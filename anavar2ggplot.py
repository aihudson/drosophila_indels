#!/usr/bin/env python

import sys
import argparse


def reformat_line(line, header):

    out_lines = []
    new_header = ['run', 'imp', 'exit_code', 'theta', 'gamma', 'e', 'var_type', 'site_class', 'lnL', 'rep', 'region']
    header = header.split()
    out_data = {x: '' for x in new_header}
    data_to_sort = {}
    for i in range(0, len(header)):
        current_col = header[i]
        current_val = line.split()[i]
        if 'ins' not in current_col and 'del' not in current_col:
            out_data[current_col] = current_val
        else:
            data_to_sort[current_col] = current_val

    # determine if ins class 1 or 2 is largest by ins gamma
    iga = data_to_sort['ins_gamma_1']
    igb = data_to_sort['ins_gamma_2']

    if float(iga) > float(igb):
        ic1 = '1'
        ic2 = '2'
    else:
        ic1 = '2'
        ic2 = '1'

    # determine if del class 1 or 2 is largest by del gamma
    dga = data_to_sort['del_gamma_1']
    dgb = data_to_sort['del_gamma_2']

    if float(dga) > float(dgb):
        dc1 = '1'
        dc2 = '2'
    else:
        dc1 = '2'
        dc2 = '1'

    # write multiple rows in long form
    for site_class in [('ins', ic1, '1'), ('ins', ic2, '2'), ('del', dc1, '1'), ('del', dc2, '2')]:
        var_type = site_class[0]
        out_data['theta'] = data_to_sort['{}_theta_{}'.format(var_type, site_class[1])]
        out_data['gamma'] = data_to_sort['{}_gamma_{}'.format(var_type, site_class[1])]
        out_data['e'] = data_to_sort['{}_e_{}'.format(var_type, site_class[1])]
        out_data['var_type'] = var_type
        out_data['site_class'] = site_class[2]

        out_lines.append('\t'.join([out_data[y] for y in new_header]))

    return '\t'.join(new_header), out_lines


def reformat_line_1class(line, header):

    out_lines = []
    new_header = ['run', 'imp', 'exit_code', 'theta', 'gamma', 'e', 'var_type', 'site_class', 'lnL', 'rep', 'region']
    header = header.split()
    out_data = {x: '' for x in new_header}
    data_to_sort = {}
    for i in range(0, len(header)):
        current_col = header[i]
        current_val = line.split()[i]
        if 'ins' not in current_col and 'del' not in current_col:
            out_data[current_col] = current_val
        else:
            data_to_sort[current_col] = current_val

    # write multiple rows in long form
    for site_class in [('ins', '1', '1'), ('del', '1', '1')]:
        var_type = site_class[0]
        out_data['theta'] = data_to_sort['{}_theta_{}'.format(var_type, site_class[1])]
        out_data['gamma'] = data_to_sort['{}_gamma_{}'.format(var_type, site_class[1])]
        out_data['e'] = data_to_sort['{}_e_{}'.format(var_type, site_class[1])]
        out_data['var_type'] = var_type
        out_data['site_class'] = site_class[2]

        out_lines.append('\t'.join([out_data[y] for y in new_header]))

    return '\t'.join(new_header), out_lines


def reformat_line_selindel_1class(line, header):

    out_lines = []
    new_header = ['run', 'imp', 'exit_code', 'theta', 'gamma', 'e',
                  'var_type', 'site_class', 'sel_type', 'lnL', 'rep', 'region']
    header = header.split()
    out_data = {x: '' for x in new_header}
    data_to_sort = {}
    for i in range(0, len(header)):
        current_col = header[i]
        current_val = line.split()[i]
        if 'ins' not in current_col and 'del' not in current_col:
            out_data[current_col] = current_val
        else:
            data_to_sort[current_col] = current_val

    # write multiple rows in long form
    for sel_type in ['sel', 'neu']:
        for site_class in [('ins', '1', '1'), ('del', '1', '1')]:
            var_type = site_class[0]
            out_data['theta'] = data_to_sort['{}_{}_theta_{}'.format(sel_type, var_type, site_class[1])]
            out_data['gamma'] = data_to_sort['{}_{}_gamma_{}'.format(sel_type, var_type, site_class[1])]
            out_data['e'] = data_to_sort['{}_{}_e_{}'.format(sel_type, var_type, site_class[1])]
            out_data['var_type'] = var_type
            out_data['site_class'] = site_class[2]
            out_data['sel_type'] = sel_type

            out_lines.append('\t'.join([out_data[y] for y in new_header]))

    return '\t'.join(new_header), out_lines


def reformat_line_selindel_2class(line, header):

    out_lines = []
    new_header = ['run', 'imp', 'exit_code', 'theta', 'gamma', 'e', 'var_type', 'site_class',
                  'sel_type', 'lnL', 'rep', 'region']
    header = header.split()
    out_data = {x: '' for x in new_header}
    data_to_sort = {}
    for i in range(0, len(header)):
        current_col = header[i]
        current_val = line.split()[i]
        if 'ins' not in current_col and 'del' not in current_col:
            out_data[current_col] = current_val
        else:
            data_to_sort[current_col] = current_val

    # determine if ins class 1 or 2 is largest by ins gamma
    iga = data_to_sort['sel_ins_gamma_1']
    igb = data_to_sort['sel_ins_gamma_2']

    if float(iga) > float(igb):
        ic1 = '1'
        ic2 = '2'
    else:
        ic1 = '2'
        ic2 = '1'

    # determine if del class 1 or 2 is largest by del gamma
    dga = data_to_sort['sel_del_gamma_1']
    dgb = data_to_sort['sel_del_gamma_2']

    if float(dga) > float(dgb):
        dc1 = '1'
        dc2 = '2'
    else:
        dc1 = '2'
        dc2 = '1'

    # write multiple rows in long form
    for site_class in [('ins', ic1, '1'), ('ins', ic2, '2'), ('del', dc1, '1'), ('del', dc2, '2')]:
        var_type = site_class[0]
        out_data['theta'] = data_to_sort['sel_{}_theta_{}'.format(var_type, site_class[1])]
        out_data['gamma'] = data_to_sort['sel_{}_gamma_{}'.format(var_type, site_class[1])]
        out_data['e'] = data_to_sort['sel_{}_e_{}'.format(var_type, site_class[1])]
        out_data['var_type'] = var_type
        out_data['site_class'] = site_class[2]
        out_data['sel_type'] = 'sel'

        out_lines.append('\t'.join([out_data[y] for y in new_header]))

    return '\t'.join(new_header), out_lines


def reformat_line_selindel_3class(line, header):

    out_lines = []
    new_header = ['run', 'imp', 'exit_code', 'theta', 'gamma', 'e', 'var_type', 'site_class',
                  'sel_type', 'lnL', 'rep', 'region']
    header = header.split()
    out_data = {x: '' for x in new_header}
    data_to_sort = {}
    for i in range(0, len(header)):
        current_col = header[i]
        try:
            current_val = line.split()[i]
        except IndexError:
            current_val = 'None'

        if 'ins' not in current_col and 'del' not in current_col:
            out_data[current_col] = current_val
        else:
            data_to_sort[current_col] = current_val

    # write multiple rows in long form
    for site_class in [('ins', '1'), ('ins', '2'), ('ins', '3'), ('del', '1'), ('del', '2'), ('del', '3')]:
        var_type = site_class[0]
        out_data['theta'] = data_to_sort['sel_{}_theta_{}'.format(var_type, site_class[1])]
        out_data['gamma'] = data_to_sort['sel_{}_gamma_{}'.format(var_type, site_class[1])]
        out_data['e'] = data_to_sort['sel_{}_e_{}'.format(var_type, site_class[1])]
        out_data['var_type'] = var_type
        out_data['site_class'] = site_class[1]
        out_data['sel_type'] = 'sel'

        out_lines.append('\t'.join([out_data[y] for y in new_header]))

    return '\t'.join(new_header), out_lines


def reformat_line_selindel_continuous(line, header):

    out_lines = []
    new_header = ['run', 'imp', 'exit_code', 'theta', 'scale', 'shape', 'e',
                  'var_type', 'site_class', 'sel_type', 'lnL', 'rep', 'region']
    header = header.split()
    out_data = {x: '' for x in new_header}
    data_to_sort = {}
    for i in range(0, len(header)):
        current_col = header[i]
        current_val = line.split()[i]
        if 'ins' not in current_col and 'del' not in current_col:
            out_data[current_col] = current_val
        else:
            data_to_sort[current_col] = current_val

    # write multiple rows in long form
    for sel_type in ['sel']:
        for site_class in [('ins', '1', '1'), ('del', '1', '1')]:
            var_type = site_class[0]
            out_data['theta'] = data_to_sort['{}_{}_theta'.format(sel_type, var_type)]
            out_data['scale'] = data_to_sort['{}_{}_scale'.format(sel_type, var_type)]
            out_data['shape'] = data_to_sort['{}_{}_shape'.format(sel_type, var_type)]
            out_data['e'] = data_to_sort['{}_{}_e'.format(sel_type, var_type)]
            out_data['var_type'] = var_type
            out_data['site_class'] = site_class[2]
            out_data['sel_type'] = sel_type

            out_lines.append('\t'.join([out_data[y] for y in new_header]))

    return '\t'.join(new_header), out_lines


def reformat_line_selsnp_1class(line, header):

    out_lines = []
    new_header = ['run', 'imp', 'exit_code', 'theta', 'gamma', 'e',
                  'var_type', 'site_class', 'sel_type', 'lnL', 'rep', 'region']
    header = header.split()
    out_data = {x: '' for x in new_header}
    data_to_sort = {}
    for i in range(0, len(header)):
        current_col = header[i]
        current_val = line.split()[i]
        if 'theta' not in current_col and 'gamma' not in current_col and '_e_' not in current_col:
            out_data[current_col] = current_val
        else:
            data_to_sort[current_col] = current_val

    # write multiple rows in long form
    for sel_type in ['sel', 'neu']:
        for site_class in [('1', '1')]:
            out_data['theta'] = data_to_sort['{}_theta_{}'.format(sel_type, site_class[0])]
            out_data['gamma'] = data_to_sort['{}_gamma_{}'.format(sel_type, site_class[0])]
            out_data['e'] = data_to_sort['{}_e_{}'.format(sel_type, site_class[0])]
            out_data['var_type'] = 'snp'
            out_data['site_class'] = site_class[1]
            out_data['sel_type'] = sel_type

            out_lines.append('\t'.join([out_data[y] for y in new_header]))

    return '\t'.join(new_header), out_lines


def reformat_line_selsnp_2class(line, header):

    out_lines = []
    new_header = ['run', 'imp', 'exit_code', 'theta', 'gamma', 'e', 'var_type', 'site_class',
                  'sel_type', 'lnL', 'rep', 'region']
    header = header.split()
    out_data = {x: '' for x in new_header}
    data_to_sort = {}
    for i in range(0, len(header)):
        current_col = header[i]
        current_val = line.split()[i]
        if 'theta' not in current_col and 'gamma' not in current_col and '_e_' not in current_col:
            out_data[current_col] = current_val
        else:
            data_to_sort[current_col] = current_val

    # determine if class 1 or 2 is largest by ins gamma
    ga = data_to_sort['sel_gamma_1']
    gb = data_to_sort['sel_gamma_2']

    if float(ga) > float(gb):
        c1 = '1'
        c2 = '2'
    else:
        c1 = '2'
        c2 = '1'

    # write multiple rows in long form
    for site_class in [(c1, '1'), (c2, '2')]:
        out_data['theta'] = data_to_sort['sel_theta_{}'.format(site_class[0])]
        out_data['gamma'] = data_to_sort['sel_gamma_{}'.format(site_class[0])]
        out_data['e'] = data_to_sort['sel_e_{}'.format(site_class[0])]
        out_data['var_type'] = 'snp'
        out_data['site_class'] = site_class[1]
        out_data['sel_type'] = 'sel'

        out_lines.append('\t'.join([out_data[y] for y in new_header]))

    return '\t'.join(new_header), out_lines


def reformat_line_selsnp_continuous(line, header):

    out_lines = []
    new_header = ['run', 'imp', 'exit_code', 'theta', 'scale', 'shape', 'e',
                  'var_type', 'site_class', 'sel_type', 'lnL', 'rep', 'region']
    header = header.split()
    out_data = {x: '' for x in new_header}
    data_to_sort = {}
    for i in range(0, len(header)):
        current_col = header[i]
        current_val = line.split()[i]
        if 'theta' not in current_col and 'shape' not in current_col and 'scale' not in current_col and '_e' not in \
                current_col:
            out_data[current_col] = current_val
        else:
            data_to_sort[current_col] = current_val

    # write multiple rows in long form
    for sel_type in ['sel']:
        for site_class in [('1', '1')]:
            out_data['theta'] = data_to_sort['{}_theta'.format(sel_type)]
            out_data['scale'] = data_to_sort['{}_scale'.format(sel_type)]
            out_data['shape'] = data_to_sort['{}_shape'.format(sel_type)]
            out_data['e'] = data_to_sort['{}_e'.format(sel_type)]
            out_data['var_type'] = 'snp'
            out_data['site_class'] = site_class[1]
            out_data['sel_type'] = sel_type

            out_lines.append('\t'.join([out_data[y] for y in new_header]))

    return '\t'.join(new_header), out_lines


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('-c', help='number of classes', default=2, type=int)
    parser.add_argument('-m', help='model run', choices=['INDEL_1', 'SEL_INDEL', 'SEL_SNP'], required=True)
    args = parser.parse_args()

    header_line = ''
    data_line = 0
    for line in sys.stdin:
        if line.startswith('run'):
            header_line = line
        else:
            data_line += 1
            if args.m == 'INDEL_1':
                if args.c == 2:
                    new_lines = reformat_line(line, header_line)
                else:
                    new_lines = reformat_line_1class(line, header_line)
            elif args.m == 'SEL_INDEL':
                if args.c == 0:
                    new_lines = reformat_line_selindel_continuous(line, header_line)
                elif args.c == 1:
                    new_lines = reformat_line_selindel_1class(line, header_line)
                elif args.c == 2:
                    new_lines = reformat_line_selindel_2class(line, header_line)
                else:
                    new_lines = reformat_line_selindel_3class(line, header_line)
            else:
                if args.c == 0:
                    new_lines = reformat_line_selsnp_continuous(line, header_line)
                elif args.c == 1:
                    new_lines = reformat_line_selsnp_1class(line, header_line)
                else:
                    new_lines = reformat_line_selsnp_2class(line, header_line)

            if data_line == 1:
                print(new_lines[0])

            print('\n'.join(new_lines[1]))

if __name__ == '__main__':
    main()
