#!/usr/bin/env python

from __future__ import print_function
import anavar_utils as an
import argparse
from qsub import *
import sys
import random
from collections import Counter


def read_callable_csv(csv):
    call_sites = {}
    for line in open(csv):
        if not line.startswith('contig'):
            info = line.rstrip().split(',')
            contig, reg, all_call, pol_call = info
            if contig not in call_sites.keys():
                call_sites[contig] = {reg: {'all': float(all_call), 'pol': float(pol_call)}}
            else:
                call_sites[contig][reg] = {'all': float(all_call), 'pol': float(pol_call)}
    return call_sites


def resample_replace(site_freqs):
    resamp_sfs = []
    for i in range(0, len(site_freqs)):
        random_no = random.randint(0, len(site_freqs) - 1)
        resamp_sfs.append(site_freqs[random_no])
    return resamp_sfs


def sfs2counts(freq_list, n):
    pos_biallelic_freqs = [round(i / float(n), 3) for i in range(1, int(n))]

    counted_sorted_sfs = sorted(Counter(freq_list).most_common(), key=lambda z: z[0])
    sfs_freq_dict = {x[0]: x[1] for x in counted_sorted_sfs}

    counts = []
    for frequency in pos_biallelic_freqs:
        try:
            no_var = sfs_freq_dict[str(frequency)]
        except KeyError:
            no_var = 0  # account for freqs with 0 variants

        counts.append(no_var)

    return counts


def indel_sel_v_neu_anavar(ins_sfs, ins_m, del_sfs, del_m, n_i_sfs, n_i_m, n_d_sfs, n_d_m, bootstrap, n, c, out_stem):

    anavar_path = '/shared/evolgen1/shared_data/program_files/iceberg/'

    anavar_cmd = '{path}anavar1.2 {ctl} {rslts} {log}'

    results = []

    for i in [0] + range(1, bootstrap+1):

        # sort sfs
        if i == 0:
            sfs_i = ins_sfs
            sfs_d = del_sfs
            sfs_ni = n_i_sfs
            sfs_nd = n_d_sfs
        else:
            sfs_i = resample_replace(ins_sfs)
            sfs_d = resample_replace(del_sfs)
            sfs_ni = resample_replace(n_i_sfs)
            sfs_nd = resample_replace(n_d_sfs)

        # convert to correct format for anavar
        sfs_i = sfs2counts(sfs_i, n)
        sfs_d = sfs2counts(sfs_d, n)
        sfs_ni = sfs2counts(sfs_ni, n)
        sfs_nd = sfs2counts(sfs_nd, n)

        # sort file names
        ctl_name = out_stem + '.rep{}.control.txt'.format(i)
        result_name = out_stem + '.rep{}.results.txt'.format(i)
        log_name = out_stem + '.rep{}.log.txt'.format(i)

        # construct control file
        sfs_m = {'selected_INS': (sfs_i, ins_m), 'selected_DEL': (sfs_d, del_m),
                 'neutral_INS': (sfs_ni, n_i_m), 'neutral_DEL': (sfs_nd, n_d_m)}
        ctl = an.IndelNeuSelControlFile()
        ctl.set_data(sfs_m, n, dfe='discrete', c=c)
        ctl_contents = ctl.construct()
        with open(ctl_name, 'w') as control:
            control.write(ctl_contents)

        # call anavar
        rep_cmd = anavar_cmd.format(path=anavar_path, ctl=ctl_name, rslts=result_name, log=log_name)
        subprocess.call(rep_cmd, shell=True)

        # process results
        with open(result_name) as rep_results:
            results_data = an.ResultsFile(rep_results)
            header = list(results_data.header()) + ['rep', 'region']
            ml_est = results_data.ml_estimate(as_string=True) + '\t{}\t{}'.format(i, 'CDS')
            if i == 0:
                results.append('\t'.join(header))
            results.append(ml_est)

    return results


def main():
    # arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-vcf', help='VCF file to extract site frequencies from', required=True)
    parser.add_argument('-n', help='Sample size', required=True)
    parser.add_argument('-c', help='Number of classes to run model with', required=True, type=int)
    parser.add_argument('-call_csv', help='Callable sites summary file', required=True)
    parser.add_argument('-bootstrap', help='Number of bootstrap replicates', default=0, type=int)
    parser.add_argument('-out_pre', help='File path and prefix for output', required=True)
    parser.add_argument('-sub', help='If specified will submit script to cluster', action='store_true', default=False)
    parser.add_argument('-evolgen', help='If specified will run on evolgen', default=False, action='store_true')
    args = parser.parse_args()

    # submission loop
    if args.sub is True:
        command_line = [' '.join([x for x in sys.argv if x != '-sub' and x != '-evolgen'])]
        q_sub(command_line, args.out_pre, evolgen=args.evolgen)
        sys.exit(0)

    # variables
    call_site_dict = read_callable_csv(args.call_csv)
    out_pre = args.out_pre

    # extract site frequencies
    del_sfs_cmd = ('/home/bop15hjb/sfs_utils/vcf2raw_sfs.py '
                   '-vcf {vcf} '
                   '-mode del -auto_only -skip_hetero '
                   '-region CDS_frameshift -region CDS_non_frameshift'
                   ).format(vcf=args.vcf)

    ins_sfs_cmd = ('/home/bop15hjb/sfs_utils/vcf2raw_sfs.py '
                   '-vcf {vcf} '
                   '-mode ins -auto_only -skip_hetero '
                   '-region CDS_frameshift -region CDS_non_frameshift'
                   ).format(vcf=args.vcf)

    n_i_sfs_cmd = ('/home/bop15hjb/sfs_utils/vcf2raw_sfs.py '
                   '-vcf {vcf} '
                   '-mode ins -auto_only -skip_hetero '
                   '-region intergenic -region intron'
                   ).format(vcf=args.vcf)

    n_d_sfs_cmd = ('/home/bop15hjb/sfs_utils/vcf2raw_sfs.py '
                   '-vcf {vcf} '
                   '-mode del -auto_only -skip_hetero '
                   '-region intergenic -region intron'
                   ).format(vcf=args.vcf)

    del_sfs = subprocess.Popen(del_sfs_cmd, shell=True, stdout=subprocess.PIPE).communicate()[0].split('\n')[:-1]
    ins_sfs = subprocess.Popen(ins_sfs_cmd, shell=True, stdout=subprocess.PIPE).communicate()[0].split('\n')[:-1]
    n_d_sfs = subprocess.Popen(n_d_sfs_cmd, shell=True, stdout=subprocess.PIPE).communicate()[0].split('\n')[:-1]
    n_i_sfs = subprocess.Popen(n_i_sfs_cmd, shell=True, stdout=subprocess.PIPE).communicate()[0].split('\n')[:-1]

    # get callable sites
    del_m = call_site_dict['ALL']['CDS']['pol']
    ins_m = call_site_dict['ALL']['CDS']['pol']
    neu_m = call_site_dict['ALL']['intergenic']['pol'] + call_site_dict['ALL']['intron']['pol']

    # construct process
    region_results = indel_sel_v_neu_anavar(ins_sfs=ins_sfs, ins_m=ins_m,
                                            del_sfs=del_sfs, del_m=del_m,
                                            n_i_sfs=n_i_sfs, n_i_m=neu_m,
                                            n_d_sfs=n_d_sfs, n_d_m=neu_m,
                                            bootstrap=args.bootstrap,
                                            n=args.n, c=args.c, out_stem=out_pre)

    # main out
    with open(out_pre + '.allreps.results.txt', 'w') as main_out:

        # print header
        print(region_results[0], file=main_out)

        # trims off header
        reg_data = region_results[1:]

        for line in reg_data:
            print(line, file=main_out)

if __name__ == '__main__':
    main()