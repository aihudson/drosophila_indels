# *Drosophila* INDEL analysis pipeline
Henry Juho Barton  
Department of Animal and Plant Sciences, The University of Sheffield  

Paper: <https://academic.oup.com/mbe/advance-article/doi/10.1093/molbev/msy054/4960016>

# Introduction

This document outlines the pipeline used to generate and analyse an INDEL dataset from 17 *Drosophila melanogaster* individuals. The document is subdivided by processing steps.

## Programs and versions required

  * Python 2.7.2
  * SAMtools version 1.2
  * GATK version 3.7
  * bcftools version 1.3
  * VCFtools version 0.1.14
  * RepeatMasker version open-4.0.6
  * bedtools version 2.26.0
  * pysam
  * gffutils
  * tabix
  * bgzip
  * qsub.py
  * anavar version 1.22
  * anavar_utils

## Scripts used in this pipeline

\* Note \* that most scripts make use of the python qsub wrapper module ```qsub.py``` described here: <https://github.com/henryjuho/python_qsub_wrapper>.


## Reference and annotation files required for analysis

*D. melanogaster* reference genome and annotation files used can be found at <ftp://ftp.flybase.net/genomes/Drosophila_melanogaster/dmel_r5.34_FB2011_02/>.

## BAM files

| Region                     | File  |
|:---------------------------|:---------------------------:|
| 2LHet                      | 2LHet.merged.realigned.bam  |
| 2L                         | 2L.merged.realigned.bam     |
| 2RHet                      | 2RHet.merged.realigned.bam  |
| 2R                         | 2R.merged.realigned.bam     |
| 3LHet                      | 3LHet.merged.realigned.bam  |
| 3L                         | 3L.merged.realigned.bam     |
| 3RHet                      | 3RHet.merged.realigned.bam  |
| 3R                         | 3R.merged.realigned.bam     |
| 4                          | 4.merged.realigned.bam      |
| XHet                       | XHet.merged.realigned.bam   |
| X                          | X.merged.realigned.bam      |


# Data preparation pipeline
## Reference and annotation preparation

Reference chromosome order files were generate for correct position sorting for GATK as follows:

```
$ grep ^'>' dmel-all-chromosome-r5.34.fa | cut -d ' ' -f 1 | cut -d '>' -f 2 > dmel_chr_order.txt
$ cat dmel_chr_order.txt | grep -v X | grep -v Y > dmel_autosomes.txt
```

GFF files were sorted, compressed with bgzip and indexed with tabix:

```
$ zcat dmel_ref/dmel-all-r5.34.gff.gz | python ~/drosophila_indels/trim_neg_coords.py | bgzip -c > dmel_ref/dmel-all-r5.34.no_neg.gff.gz
$ tabix -pgff dmel_ref/dmel-all-r5.34.no_neg.gff.gz
```

Then region coordinates were output to bed files as follows:

```
$ zgrep chromosome_arm dmel-all-r5.34.no_neg.gff.gz | gff2bed.py > dmel_chromosomes.bed
$ zcat dmel-all-r5.34.no_neg.gff.gz | cut -f 1-5 | grep intron | gff2bed.py | sort -k1,1 -k2,2n | bedtools merge > dmel_introns.bed
$ zcat dmel-all-r5.34.no_neg.gff.gz | cut -f 1-5 | grep CDS | grep -v match | gff2bed.py | sort -k1,1 -k2,2n | bedtools merge > dmel_cds.bed
$ zcat dmel-all-r5.34.no_neg.gff.gz | cut -f 1-5 | grep FlyBase | grep gene | grep -v pseudo | gff2bed.py | sort -k1,1 -k2,2n | bedtools merge > dmel_genes.bed
$ bedtools subtract -a dmel_chromosomes.bed -b dmel_genes.bed > dmel_intergenic.bed
$ cat dmel_introns.bed dmel_intergenic.bed | sort -k1,1 -k2,2n | bedtools merge > dmel_noncoding.bed
```
## Preparing BAM files

Multi-sample chromosomal BAM files were converted to single sample whole genome BAM files as follows:

```
$ split_bams.py -bam_dir /fastdata/bop15hjb/drosophila_data/dmel/ -out_dir /fastdata/bop15hjb/drosophila_data/dmel/unmerged_bams/ -evolgen
$ merge_chromosomal_bams.py -bam_dir /fastdata/bop15hjb/drosophila_data/dmel/unmerged_bams/ -out_dir /fastdata/bop15hjb/drosophila_data/dmel/individual_bams/ -evolgen
$ cd /fastdata/bop15hjb/drosophila_data/dmel/bams/individual_bams
$ ls *bam | while read i; do samtools index -b $i; done
$ ls $PWD/*bam > dmel_bam_list.txt
```

## Variant calling

Raw SNPs and INDELs were called using both GATK's Haplotype Caller and SAMtools mpileup. GATK calling proceeded as follows:

```
$ haplotype_caller.py -ref /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel-all-chromosome-r5.34.fa -bam_dir /fastdata/bop15hjb/drosophila_data/dmel/bams/individual_bams/ -out_dir /fastdata/bop15hjb/drosophila_data/dmel/gatk_calling/gvcf/
$ ls /fastdata/bop15hjb/drosophila_data/dmel/gatk_calling/gvcf/*vcf > /fastdata/bop15hjb/drosophila_data/dmel/gatk_calling/gvcf/dmel_gvcf.list
$ genotypeGVCFs.py -ref /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel-all-chromosome-r5.34.fa -vcf_list /fastdata/bop15hjb/drosophila_data/dmel/gatk_calling/gvcf/dmel_gvcf.list -out /fastdata/bop15hjb/drosophila_data/dmel/gatk_calling/allsites/dmel_17flys.gatk.allsites.vcf -evolgen
```

SAMtools calling proceeded as follows:

```
$ samtools_calling.py -bam_list /fastdata/bop15hjb/drosophila_data/dmel/bams/individual_bams/dmel_bam_list.txt -ref /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel-all-chromosome-r5.34.fa -out /fastdata/bop15hjb/drosophila_data/dmel/samtools_calling/dmel_17flys -evolgen
```

## VQSR

### Generating sets of 'known variants'

In order to run GATKs variant quality score recalibration (VQSR) a set of high confidence variants was generated through the intersection of GATK and SAMtools raw variant calls. This 'truth set' was generated as follows:

```
$ get_consensus_vcf.py -vcf_I /fastdata/bop15hjb/drosophila_data/dmel/gatk_calling/allsites/dmel_17flys.gatk.allsites.vcf -vcf_II /fastdata/bop15hjb/drosophila_data/dmel/samtools_calling/dmel_17flys.samtools.allsites.vcf -ref /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel-all-chromosome-r5.34.fa -out /fastdata/bop15hjb/drosophila_data/dmel/consensus/
```

Mean depth was calculated from the GATK allsites vcf using vcftools as follows:

```
$ get_mean_depth.py -vcf /fastdata/bop15hjb/drosophila_data/dmel/gatk_calling/allsites/dmel_17flys.gatk.allsites.vcf
$ cat /fastdata/bop15hjb/drosophila_data/dmel/gatk_calling/allsites/*idepth | grep -v ^I | cut -f 3 | awk '{sum+=$1} END {print sum/NR}'
```

| Species           | Mean depth  |
|:------------------|:-----------:|
| _D. melanogaster_ | 20x         |

Consensus INDEL and SNP vcfs were then hardfiltered to remove sites with less than half or more than twice the mean depth, multiallelic sites and INDELs greater than 50bp.

```
$ depth_filter.py -vcf /fastdata/bop15hjb/drosophila_data/dmel/consensus/dmel_17flys.consensus.raw.indels.vcf -mean_depth 20 -N 17
$ depth_filter.py -vcf /fastdata/bop15hjb/drosophila_data/dmel/consensus/dmel_17flys.consensus.raw.snps.vcf -mean_depth 20 -N 17
$ ls /fastdata/bop15hjb/drosophila_data/dmel/consensus/*dpfiltered.vcf | while read i; do filter_length_biallelic.py -vcf $i -ref /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel-all-chromosome-r5.34.fa; done
```

Bed files of repeat positions were obtained from repeat masker outputs (see Whole genome alignment) and sites falling within repeat regions were excluded as follows: 

```
$ cd /fastdata/bop15hjb/drosophila_data/wga/genomes
$ cat dmel-all-chromosome-r5.34.fa.out | rm_out2bed.py | bedtools sort -faidx ../../dmel_ref/dmel_chr_order.txt > dmel-all-chromosome-r5.34.fa.out.bed
$ cd
$ ls /fastdata/bop15hjb/drosophila_data/dmel/consensus/*bial.vcf | while read i; do repeat_filtering.py -vcf $i -ref /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel-all-chromosome-r5.34.fa -bed /fastdata/bop15hjb/drosophila_data/wga/genomes/dmel-all-chromosome-r5.34.fa.out.bed -evolgen ; done
```

Finally sites were hard filtered according to the GATK best practice (QD < 2.0, ReadPosRankSum < -20.0, FS > 200.0, SOR > 10.0 for INDELs, QD < 2.0, MQ < 40.0, FS > 60.0, SOR > 3.0, MQRankSum < -12.5, ReadPosRankSum < -8.0, for SNPs <https://software.broadinstitute.org/gatk/guide/article?id=3225>), additionally, SNPs falling within INDELs were removed.

```
$ hardfilter.py -ref /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel-all-chromosome-r5.34.fa -vcf /fastdata/bop15hjb/drosophila_data/dmel/consensus/dmel_17flys.consensus.raw.indels.dpfiltered.50bp_max.bial.rfiltered.vcf -mode INDEL -evolgen
$ hardfilter.py -ref /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel-all-chromosome-r5.34.fa -vcf /fastdata/bop15hjb/drosophila_data/dmel/consensus/dmel_17flys.consensus.raw.snps.dpfiltered.50bp_max.bial.rfiltered.vcf -mode SNP -evolgen
$ exclude_snp_in_indel.py -vcf /fastdata/bop15hjb/drosophila_data/dmel/consensus/dmel_17flys.consensus.raw.snps.dpfiltered.50bp_max.bial.rfiltered.hfiltered.vcf
```

### 'Truth set' summary

| Filtering step     | _D. mel_ INDELs  | _D. mel_ SNPs  |
|:-------------------|:----------------:|:--------------:|
| raw GATK           | 798107           | 6161265        |
| raw SAMtools       | 791236           | 3418572        |
| raw consensus      | 550354           | 3316428        |
| depth              | 437145           | 2628415        |
| length, allele no. | 331846           | 2471023        |
| repeats            | 286450           | 2319409        |
| hardfilters        | 286177           | 2036210        |
| no snps in indels  | -                | 2017080        |

### VQSR

VQSR was performed for SNP (for SNPs, variants in INDELs were first exluded from the raw data) and INDELs separately for both species as follows:

```
$ VQSR.py -vcf /fastdata/bop15hjb/drosophila_data/dmel/consensus/dmel_17flys.gatk.raw.indels.vcf -ref /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel-all-chromosome-r5.34.fa -truth_set /fastdata/bop15hjb/drosophila_data/dmel/consensus/dmel_17flys.consensus.raw.indels.dpfiltered.50bp_max.bial.rfiltered.hfiltered.vcf -mode INDEL -out /fastdata/bop15hjb/drosophila_data/dmel/vqsr/
$ exclude_snp_in_indel.py -vcf /fastdata/bop15hjb/drosophila_data/dmel/consensus/dmel_17flys.gatk.raw.snps.vcf
$ VQSR.py -vcf /fastdata/bop15hjb/drosophila_data/dmel/consensus/dmel_17flys.gatk.raw.snps.exsnpindel.vcf -ref /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel-all-chromosome-r5.34.fa -truth_set /fastdata/bop15hjb/drosophila_data/dmel/consensus/dmel_17flys.consensus.raw.snps.dpfiltered.50bp_max.bial.rfiltered.hfiltered.exsnpindel.vcf -mode SNP -out /fastdata/bop15hjb/drosophila_data/dmel/vqsr/
```

### Post VQSR filters

Variants more than twice and half the mean coverage, longer than 50bp or multiallelic were then removed from the post VQSR (95% cutoff) data, additionally variants located in repeat regions were marked.

```
$ cd /fastdata/bop15hjb/drosophila_data/dmel/vqsr/
$ ls $PWD/*t95.0.pass.vcf | while read i; do depth_filter.py -vcf $i -mean_depth 20 -N 17; done
$ ls $PWD/*dpfiltered.vcf | while read i; do filter_length_biallelic.py -vcf $i -ref /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel-all-chromosome-r5.34.fa; done 
$ ls $PWD/*bial.vcf | while read i; do repeat_filtering.py -vcf $i -ref /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel-all-chromosome-r5.34.fa -bed /fastdata/bop15hjb/drosophila_data/wga/genomes/dmel-all-chromosome-r5.34.fa.out.bed -evolgen ; done
```

### VQSR summary

| Filtering step     | _D. mel_ INDELs  | _D. mel_ SNPs  |
|:-------------------|:----------------:|:--------------:|
| raw GATK           | 798107           | 6161265        |
| SNPs in INDELs     | -                | 3357471        |
| post VQSR (95%)    | 651767           | 2416349        |
| depth              | 538762           | 2098303        |
| length, allele no. | 453181           | 2066044        |
| repeats marked     | 401692           | 1989033        |

## Whole genome alignment

Whole genome alignments were performed between _D. melanogaster_, _D. simulans_ and _D. yakuba_ using MultiZ, following the UCSC pipeline (described [here](http://genomewiki.ucsc.edu/index.php/Whole_genome_alignment_howto)).

First _D. simulans_ fasta headers were truncated to come within the required 50bp max length for RepeatMasker.

```
$ cat dsimV2-Mar2012.fa | rename_dsim_headers.py > dsimV2-Mar2012.rename.fa 
```
Genomes were softmasked using RepeatMasker in the following script:

```
$ ls /fastdata/bop15hjb/drosophila_data/wga/genomes/*fa | while read i; do repeat_masking.py -fa $i -evolgen; done
```

LINE coordinates were extracted from the _D. mel_ repeat masker output file and added to the reference files.

```
$ cd /fastdata/bop15hjb/drosophila_data/wga/genomes/
$ zgrep LINE dmel-all-chromosome-r5.34.fa.out | cut -d '.' -f 4- | cut -d ' ' -f 3- | cut -d '(' -f 1 | awk 'BEGIN{FS=" "} {print $1 "\t" $2 -1 "\t" $3}' | bgzip -c > /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel-r5.34.LINEs.bed.gz
```

The resulting soft masked fasta file headers were editted to contain species information:

```
$ fasta_add_header_prefix.py -fa dmel-all-chromosome-r5.34.fa.masked -pre 'dmel.' -truncate
$ fasta_add_header_prefix.py -fa dsimV2-Mar2012.rename.fa.masked -pre 'dsim.' -truncate
$ fasta_add_header_prefix.py -fa dyak-all-chromosome-r1.3.fa.masked -pre 'dyak.' -truncate
```

The resulting files were then used to generate pairwise alignments with lastz, which were then chained and netted using x and y respectively.

```
$ wholegenome_lastz_chain_net.py -ref_fa /fastdata/bop15hjb/drosophila_data/wga/genomes/dmel-all-chromosome-r5.34.fa.masked.rename.fa -ref_name dmel -query_fa /fastdata/bop15hjb/drosophila_data/wga/genomes/dsimV2-Mar2012.rename.fa.masked.rename.fa -query_name dsim -out /fastdata/bop15hjb/drosophila_data/wga/pairwise_alignments/
$ wholegenome_lastz_chain_net.py -ref_fa /fastdata/bop15hjb/drosophila_data/wga/genomes/dmel-all-chromosome-r5.34.fa.masked.rename.fa -ref_name dmel -query_fa /fastdata/bop15hjb/drosophila_data/wga/genomes/dyak-all-chromosome-r1.3.fa.masked.rename.fa -query_name dyak -out /fastdata/bop15hjb/drosophila_data/wga/pairwise_alignments/
```

Single coverage was then ensured for the reference genome:

```
$ single_cov.py -dir /fastdata/bop15hjb/drosophila_data/wga/pairwise_alignments/ -ref_name dmel 
```

The multiple alignment was then created using multiz using the roast wrapper (sumit) and then converted to a whole genome alignment bed file using the WGAbed package (<https://github.com/padraicc/WGAbed>).

```
$ roast.py -maf_dir /fastdata/bop15hjb/drosophila_data/wga/pairwise_alignments/single_coverage/ -ref dmel -out /fastdata/bop15hjb/drosophila_data/wga/multiple_alignment/dmel.dsim.dyak.maf -tree '"((dmel dsim) dyak)"'
$ cd /fastdata/bop15hjb/drosophila_data/wga/multiple_alignment/
$ gzip dmel.dsim.dyak.maf
 
$ grep '>' ../genomes/dmel-all-chromosome-r5.34.fa.masked.rename.fa | cut -d '.' -f 2 | while read i; do maf_to_bed.py -i dmel.dsim.dyak.maf.gz -r dmel -c $i | sort -k1,1 -k2,2n | gzip -c > dmel.dsim.dyak.$i.wga.bed.gz; done
$ zcat dmel.dsim.dyak.2LHet.wga.bed.gz dmel.dsim.dyak.2L.wga.bed.gz dmel.dsim.dyak.2RHet.wga.bed.gz dmel.dsim.dyak.2R.wga.bed.gz dmel.dsim.dyak.3LHet.wga.bed.gz dmel.dsim.dyak.3L.wga.bed.gz dmel.dsim.dyak.3RHet.wga.bed.gz dmel.dsim.dyak.3R.wga.bed.gz dmel.dsim.dyak.4.wga.bed.gz dmel.dsim.dyak.dmel_mitochondrion_genome.wga.bed.gz dmel.dsim.dyak.Uextra.wga.bed.gz dmel.dsim.dyak.U.wga.bed.gz dmel.dsim.dyak.XHet.wga.bed.gz dmel.dsim.dyak.X.wga.bed.gz dmel.dsim.dyak.YHet.wga.bed.gz | bgzip -c > dmel.dsim.dyak.wga.bed.gz
$ tabix -pbed dmel.dsim.dyak.wga.bed.gz
```

Gene alignments in phylip format were generate from the multispecies alignment for autosomal (2, 3 and 4, all arms and heterochromatin)  genesas follows:

```
$ ls /fastdata/bop15hjb/drosophila_data/dmel_ref/cds_fasta/*fasta* | grep -v all | grep -v mito | grep -v X | grep -v Y | grep -v U > /fastdata/bop15hjb/drosophila_data/dmel_ref/cds_fasta/autosome_fasta_list.txt
$ cat /fastdata/bop15hjb/drosophila_data/dmel_ref/cds_fasta/autosome_fasta_list.txt | while read i; do wgaBed2genes.py -wga_bed /fastdata/bop15hjb/drosophila_data/wga/multiple_alignment/dmel.dsim.dyak.wga.bed.gz -cds_fa $i -out_dir /fastdata/bop15hjb/drosophila_data/dmel/gene_analysis/phylip_files/ -sub -evolgen; done
$ trim_stop_trim_miss.py -phy_dir /fastdata/bop15hjb/drosophila_data/dmel/gene_analysis/phylip_files/ -out_dir /fastdata/bop15hjb/drosophila_data/dmel/gene_analysis/trimmed_phylip/
```

The script only outputs alignments for transcripts that are in frame, start with a start codon, end with a stop codon and without any premature stop codons. Additionally any codons containing N's or bases not present in the alignment are dropped.

## Polarisation

Variants were polarised using the whole genome alignment and a parsimony approach, where either the alternate or the reference allele had to be supported by all outgroups in the the alignment to be considered ancestral.

```
$ polarise_vcf.py -vcf /fastdata/bop15hjb/drosophila_data/dmel/post_vqsr/dmel_17flys.gatk.raw.indels.recalibrated.filtered_t95.0.pass.dpfiltered.50bp_max.bial.rmarked.vcf -wga_bed /fastdata/bop15hjb/drosophila_data/wga/multiple_alignment/dmel.dsim.dyak.wga.bed.gz -sub
$ polarise_vcf.py -vcf /fastdata/bop15hjb/drosophila_data/dmel/post_vqsr/dmel_17flys.gatk.raw.snps.exsnpindel.recalibrated.filtered_t95.0.pass.dpfiltered.50bp_max.bial.rmarked.vcf -wga_bed /fastdata/bop15hjb/drosophila_data/wga/multiple_alignment/dmel.dsim.dyak.wga.bed.gz -sub
```

| Category           | _D. mel_ INDELs  | _D. mel_ SNPs  |
|:-------------------|:----------------:|:--------------:|
|total               | 453181           | 2066044        |
|polarised           | **183617**       | **1058001**    |
|hotspots            | 110409           | 143392         |
|low spp coverage    | 132674           | 611511         |
|ambiguous           | 26481            | 253140         |
|total unpolarised   | 269564           | 1008043        |


## Annotating genomic regions

Variants were annotated as either 'CDS_non_frameshift' (all CDS SNPs, and CDS INDELs with lengths divisible by 3), 'CDS_frameshift', 'intron' or 'intergenic'.

```
$ annotate_regions_all_chr.py -gff /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel-all-r5.34.gff.gz -vcf /fastdata/bop15hjb/drosophila_data/dmel/post_vqsr/dmel_17flys.gatk.raw.indels.recalibrated.filtered_t95.0.pass.dpfiltered.50bp_max.bial.rmarked.polarised.vcf -evolgen
$ annotate_regions_all_chr.py -gff /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel-all-r5.34.gff.gz -vcf /fastdata/bop15hjb/drosophila_data/dmel/post_vqsr/dmel_17flys.gatk.raw.snps.exsnpindel.recalibrated.filtered_t95.0.pass.dpfiltered.50bp_max.bial.rmarked.polarised.vcf -evolgen
```

| Annotation category| _D. mel_ INDELs  | _D. mel_ SNPs  |
|:-------------------|:----------------:|:--------------:|
|All                 | 453181           | 2066044        |
|CDS_frameshift      | 1934             | -              |
|CDS_non_frameshift  | 3744             | 321224         |
|Intron              | 228009           | 870947         |
|Intergenic          | 196042           | 732757         |
|Not annotated       | 23452            | 141116         |

## Annotating ancestral repeats

Coordinates for regions that were soft masked across all genomes in the whole genome alignment were extracted and used to annotated intergenic variants.

```
$ cd /fastdata/bop15hjb/drosophila_data/wga/multiple_alignment/
$ zcat dmel.dsim.dyak.wga.bed.gz | ancestral_repeat_extract.py | bgzip -c > dmel_ancestral_repeats.wga.bed.gz
$ bedtools intersect -a dmel_ancestral_repeats.wga.bed.gz -b ../../dmel_ref/dmel-r5.34.LINEs.bed.gz | bgzip -c > ../../dmel_ref/dmel-r5.34.ancLINEs.bed.gz 
$ tabix -pbed  ../../dmel_ref/dmel-r5.34.ancLINEs.bed.gz

$ cd /fastdata/bop15hjb/drosophila_data/

$ annotate_anc_reps.py -bed wga/multiple_alignment/dmel_ancestral_repeats.wga.bed.gz -vcf dmel/post_vqsr/dmel_17flys.gatk.raw.indels.recalibrated.filtered_t95.0.pass.dpfiltered.50bp_max.bial.rmarked.polarised.annotated.vcf -trim_non_anc_reps
$ annotate_anc_reps.py -bed wga/multiple_alignment/dmel_ancestral_repeats.wga.bed.gz -vcf dmel/post_vqsr/dmel_17flys.gatk.raw.snps.exsnpindel.recalibrated.filtered_t95.0.pass.dpfiltered.50bp_max.bial.rmarked.polarised.annotated.vcf -trim_non_anc_reps
```

| Category           | _D. mel_ INDELs  | _D. mel_ SNPs  |
|:-------------------|:----------------:|:--------------:|
| before annotation  | 453181           | 2066044        |
| non-coding ARs     | 8153             | 11040          |
| non ARs removed    | 43336            | 65971          |
| after annotation   | 409845           | 2000073        |

## SNP degeneracy 

Bed files were created with coordinates for all fourfold and zerofold sites in the genome using the CDS fasta sequence downloaded from: <ftp://ftp.flybase.net/genomes/Drosophila_melanogaster/dmel_r5.34_FB2011_02/fasta/dmel-all-CDS-r5.34.fasta.gz> as follows:
 
```
$ cd /fastdata/bop15hjb/drosophila_data/dmel_ref/
$ qsuber -cmd "cd /fastdata/bop15hjb/drosophila_data/dmel_ref/" -cmd "degen_to_bed.py -cds_fa cds_fasta/dmel-all-CDS-r5.34.fasta.gz -degen 0 | sort -k1,1 -k2,2n | bedtools merge -c 4 -o distinct | bgzip -c > dmel-all-0fold.bed.gz" -rmem 15 -mem 15 -evolgen -o /fastdata/bop15hjb/drosophila_data/dmel_ref/zerofold_gene_pos -t 48 -OM q
$ tabix -pbed dmel-all-0fold.bed.gz 

# todo add merge to 4fold file
$ qsuber -cmd "cd /fastdata/bop15hjb/drosophila_data/dmel_ref/" -cmd "degen_to_bed.py -cds_fa cds_fasta/dmel-all-CDS-r5.34.fasta.gz -degen 4 | sort -k1,1 -k2,2n | bgzip -c > dmel-all-4fold.bed.gz" -rmem 15 -mem 15 -evolgen -o /fastdata/bop15hjb/drosophila_data/dmel_ref/fourfold_gene_pos -t 48 -OM q
$ tabix -pbed dmel-all-4fold.bed.gz

$ qsuber -cmd "cd /fastdata/bop15hjb/drosophila_data/dmel_ref/" -cmd "degen_to_bed.py -cds_fa cds_fasta/dmel-all-CDS-r5.34.fasta.gz -degen 0 -degen 2 -degen 3 -degen 4 | sort -k1,1 -k2,2n | bedtools merge -c 4 -o distinct | bgzip -c > dmel-all-degen.bed.gz" -rmem 15 -mem 15 -evolgen -o /fastdata/bop15hjb/drosophila_data/dmel_ref/all_degen_gene_pos -t 48 -OM q
$ tabix -pbed dmel-all-degen.bed.gz 
```

Coordinates of fourfold sites from genes with GC <= 72% were also obtained:

```
$ cd ~/drosophila_indels/
$ ./fourfold_gc.py -fourfold /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel-all-4fold.bed.gz -ref /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel-all-chromosome-r5.34.fa
$ cd /fastdata/bop15hjb/drosophila_data/dmel_ref/
$ bedtools merge -c 4 -o distinct -i dmel-all-4fold_maxgc72.bed.gz | bgzip -c > dmel-all-4fold_maxgc72.collapsed.bed.gz
$ tabix -pbed dmel-all-4fold_maxgc72.collapsed.bed.gz 
```

These were then used to annotate the degeneracy of coding SNPs as follows.

```
$ annotate_degeneracy.py -vcf /fastdata/bop15hjb/drosophila_data/dmel/post_vqsr/dmel_17flys.gatk.raw.snps.exsnpindel.recalibrated.filtered_t95.0.pass.dpfiltered.50bp_max.bial.rmarked.polarised.annotated.ar.vcf -zerofold /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel-all-0fold.bed.gz -fourfold /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel-all-4fold.bed.gz
```

|Category          | Number SNPs     |
|:-----------------|:---------------:|
|zerofold          |75549            |
|fourfold          |150441           |

## Generating callable sites fastas

Fasta files of callable sites were created and summarised using the following codes:

| Case            | code  |
|:----------------|:-----:|
| N               | 0     |
| Filtered        | 1     |
| Pass polarised  | K     |
| Pass unpolarised| k     |
| AR polarised    | R     |
| AR unpolarised  | r     |

```
$ qrsh -q evolgen.q -P evolgen -l rmem=25G -l mem=25G

$ mkdir /fastdata/bop15hjb/drosophila_data/dmel_ref/callable_sites
$ bgzip /fastdata/bop15hjb/drosophila_data/dmel/gatk_calling/allsites/dmel_17flys.gatk.allsites.vcf
$ tabix -pvcf /fastdata/bop15hjb/drosophila_data/dmel/gatk_calling/allsites/dmel_17flys.gatk.allsites.vcf.gz
$ callable_sites_from_vcf.py -vcf /fastdata/bop15hjb/drosophila_data/dmel/gatk_calling/allsites/dmel_17flys.gatk.allsites.vcf.gz -bed /fastdata/bop15hjb/drosophila_data/wga/genomes/dmel-all-chromosome-r5.34.fa.out.bed -ar_bed /fastdata/bop15hjb/drosophila_data/wga/multiple_alignment/dmel_ancestral_repeats.wga.bed.gz  -mean_depth 20 -N 17  -out /fastdata/bop15hjb/drosophila_data/dmel_ref/callable_sites/dmel.callable -pol /fastdata/bop15hjb/drosophila_data/wga/multiple_alignment/dmel.dsim.dyak.wga.bed.gz -sub -evolgen
$ callable_sites_summary.py -gff /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel-all-r5.34.gff.gz -call_fa /fastdata/bop15hjb/drosophila_data/dmel_ref/callable_sites/dmel.callable.ALL.fa -chr_list /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel_autosomes.txt -opt_bed /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel-all-0fold.bed.gz,zerofold -opt_bed /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel-all-4fold.bed.gz,fourfold > /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel.callablesites.summary_with_degen.csv
```

## Indexing

Analysis ready files were compressed with bgzip and indexed with tabix:

```
$ bgzip /fastdata/bop15hjb/drosophila_data/dmel/post_vqsr/dmel_17flys.gatk.raw.indels.recalibrated.filtered_t95.0.pass.dpfiltered.50bp_max.bial.rmarked.polarised.annotated.ar.vcf
$ tabix -pvcf /fastdata/bop15hjb/drosophila_data/dmel/post_vqsr/dmel_17flys.gatk.raw.indels.recalibrated.filtered_t95.0.pass.dpfiltered.50bp_max.bial.rmarked.polarised.annotated.ar.vcf.gz
$ bgzip dmel_17flys.gatk.raw.snps.exsnpindel.recalibrated.filtered_t95.0.pass.dpfiltered.50bp_max.bial.rmarked.polarised.annotated.ar.degen.vcf 
$ tabix -pvcf dmel_17flys.gatk.raw.snps.exsnpindel.recalibrated.filtered_t95.0.pass.dpfiltered.50bp_max.bial.rmarked.polarised.annotated.ar.degen.vcf.gz
```

# Analysis

## Summary statistics: theta, pi and Tajima's D

```
$ summary_stats.py -vcf /fastdata/bop15hjb/drosophila_data/dmel/post_vqsr/dmel_17flys.gatk.raw.indels.recalibrated.filtered_t95.0.pass.dpfiltered.50bp_max.bial.rmarked.polarised.annotated.ar.vcf.gz -call_csv /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel.callablesites.summary.csv -mode INDEL -sub -out /fastdata/bop15hjb/drosophila_data/dmel/summary_stats/dmel_17flys_indel_summary_no_bs_split_ar_nc.txt -evolgen
$ summary_stats.py -vcf /fastdata/bop15hjb/drosophila_data/dmel/post_vqsr/dmel_17flys.gatk.raw.indels.recalibrated.filtered_t95.0.pass.dpfiltered.50bp_max.bial.rmarked.polarised.annotated.ar.vcf.gz -call_csv /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel.callablesites.summary.csv -mode INDEL -sub -out /fastdata/bop15hjb/drosophila_data/dmel/summary_stats/dmel_17flys_indel_summary_1000bs_nc.txt -evolgen -bootstrap 1000
$ summary_stats.py -vcf /fastdata/bop15hjb/drosophila_data/dmel/analysis_ready_data/dmel_17flys.gatk.raw.snps.exsnpindel.recalibrated.filtered_t95.0.pass.dpfiltered.50bp_max.bial.rmarked.polarised.annotated.ar.degen.vcf.gz -call_csv /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel.callablesites.summary_with_degen.csv -mode SNP -sub -out /fastdata/bop15hjb/drosophila_data/dmel/summary_stats/dmel_17flys_snp_summary_codon_checks_no_bs_nc.txt -evolgen
$ summary_stats.py -vcf /fastdata/bop15hjb/drosophila_data/dmel/analysis_ready_data/dmel_17flys.gatk.raw.snps.exsnpindel.recalibrated.filtered_t95.0.pass.dpfiltered.50bp_max.bial.rmarked.polarised.annotated.ar.degen.vcf.gz -call_csv /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel.callablesites.summary_with_degen.csv -mode SNP -sub -out /fastdata/bop15hjb/drosophila_data/dmel/summary_stats/dmel_17flys_snp_summary_codon_checks_bs1000_nc.txt -evolgen -bootstrap 1000
```

In response to reviewer comments we also obtained summary statistics for nonsense mutations:

```
$ ./automate_nonsense_stats.py -cds_fa_dir /fastdata/bop15hjb/drosophila_data/dmel_ref/cds_fasta/ -out_dir /fastdata/bop15hjb/drosophila_data/dmel/summary_stats/ -vcf /fastdata/bop15hjb/drosophila_data/dmel/analysis_ready_data/dmel_17flys.gatk.raw.snps.exsnpindel.recalibrated.filtered_t95.0.pass.dpfiltered.50bp_max.bial.rmarked.polarised.annotated.ar.degen.vcf.gz -call_fa /fastdata/bop15hjb/drosophila_data/dmel_ref/callable_sites/dmel.callable.ALL.fa -evolgen
```

The summary stats can be found as follows. For INDELs [here](dmel_17flys_indel_summary_no_bs_split_ar_nc.txt), for SNPs 
[here](dmel_17flys_snp_summary_codon_checks_no_bs.txt) and for nonsense mutations [here](dmel_nonsense_stats.txt).

## Site frequency spectra

Site frequency spectra were extracted and plotted as follows:

```
$ summary_sfs.py -vcf /fastdata/bop15hjb/drosophila_data/dmel/analysis_ready_data/dmel_17flys.gatk.raw.indels.recalibrated.filtered_t95.0.pass.dpfiltered.50bp_max.bial.rmarked.polarised.annotated.ar.vcf.gz -mode INDEL -out indel_sfs/ -spp dmel -evolgen
$ Rscript sfs_plots.R
```

Genome-wide plot [here](gwide_indel_sfs.pdf) and regional plot [here](regional_indel_sfs.pdf).


## Length summary

The distribution of INDEL lengths was summarised with the following scripts:

```
$ ./indel_lengths.py -vcf ~/sharc_fastdata/drosophila_data/dmel/analysis_ready_data/dmel_17flys.gatk.raw.indels.recalibrated.filtered_t95.0.pass.dpfiltered.50bp_max.bial.rmarked.polarised.annotated.ar.vcf.gz -region 'CDS' -region 'non-coding' -auto_only > dmel_indel_lengths.txt
$ Rscript length_distribution.R 
```

Plot can be seen [here](dmel_lengths.pdf)

## Gene by gene analysis

dn and ds values were calculated using codeml, with a one ratio model, on the genes extracted from the multispecies alignment as follows:

```
$ per_gene_codeml.py -phy_dir /fastdata/bop15hjb/drosophila_data/dmel/gene_analysis/trimmed_phylip/ -out_dir /fastdata/bop15hjb/drosophila_data/dmel/gene_analysis/codeml_data/
$ extract_dn_ds.py -dir /fastdata/bop15hjb/drosophila_data/dmel/gene_analysis/codeml_data/ > /fastdata/bop15hjb/drosophila_data/dmel/gene_analysis/dmel.dn_ds_values.longest_trans.txt
```

pi, theta and Tajima's D values for zerofold SNPs, fourfold SNPs and INDELs were calculated for all transcripts of all genes in the dmel CDS fasta alignments file:

```
$ summarise_genes.py -call_fa /fastdata/bop15hjb/drosophila_data/dmel_ref/callable_sites/dmel.callable.ALL.fa -vcf /fastdata/bop15hjb/drosophila_data/dmel/analysis_ready_data/dmel_17flys.gatk.raw.snps.exsnpindel.recalibrated.filtered_t95.0.pass.dpfiltered.50bp_max.bial.rmarked.polarised.annotated.ar.degen.vcf.gz -zbed /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel-all-0fold.bed.gz -fbed /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel-all-4fold.bed.gz -out /fastdata/bop15hjb/drosophila_data/dmel/gene_analysis/dmel.pi0_pi4_theta_tajd_values.all_trans.txt -sub -evolgen
$ summarise_genic_indels.py -call_fa /fastdata/bop15hjb/drosophila_data/dmel_ref/callable_sites/dmel.callable.ALL.fa -vcf /fastdata/bop15hjb/drosophila_data/dmel/analysis_ready_data/dmel_17flys.gatk.raw.indels.recalibrated.filtered_t95.0.pass.dpfiltered.50bp_max.bial.rmarked.polarised.annotated.ar.vcf.gz -cds_bed /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel-all-degen.bed.gz -out /fastdata/bop15hjb/drosophila_data/dmel/gene_analysis/dmel.pi_theta_tajd_indel_values.all_trans.txt -sub -evolgen
```

Genes with dn ds estimates then had pi0 pi4 estimates added from the above step with the following script:

```
$ cd /fastdata/bop15hjb/drosophila_data/dmel/gene_analysis/
$ cat_dnds_pi0pi4.py -d dmel.dn_ds_values.longest_trans.txt -p dmel.pi0_pi4_theta_tajd_values.all_trans.txt -pI dmel.pi_theta_tajd_indel_values.all_trans.txt > dmel.gene_summarystats.longest_trans.txt
```

Genes with dS greater than 5 were filtered out, the remaining results (8355 genes) were binned into 20 equal occupancy bins according to dN and plotted as max dN per bin against mean pi per bin (A) and mean Tajima's D per bin for zerofold, fourfold and INDEL sites.

```
$ Rscript plot_dnds_pi0pi4.R
```

The results can be seen [here](dmel.pi_tajd_dn.pdf)

## INDEL divergence

```
$ indel_divergence.py -wga /fastdata/bop15hjb/drosophila_data/wga/multiple_alignment/dmel.dsim.dyak.wga.bed.gz -bed /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel_cds.bed -out ~/drosophila_indels/divergence_data/dmel_cds_indel_divergence.txt
$ indel_divergence.py -wga /fastdata/bop15hjb/drosophila_data/wga/multiple_alignment/dmel.dsim.dyak.wga.bed.gz -bed /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel_noncoding.bed -out ~/drosophila_indels/divergence_data/dmel_noncoding_indel_divergence.txt
$ indel_divergence.py -wga /fastdata/bop15hjb/drosophila_data/wga/multiple_alignment/dmel.dsim.dyak.wga.bed.gz -bed /fastdata/bop15hjb/drosophila_data/wga/multiple_alignment/dmel_ancestral_repeats.wga.bed.gz -out ~/drosophila_indels/divergence_data/dmel_ar_indel_divergence.txt
$ indel_divergence.py -wga /fastdata/bop15hjb/drosophila_data/wga/multiple_alignment/dmel.dsim.dyak.wga.bed.gz -bed /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel-r5.34.ancLINEs.bed.gz -out ~/drosophila_indels/divergence_data/dmel_ar_LINEs_indel_divergence.txt

$ Rscript collate_indel_divergence.R 
```

Divergence was also calculated for the length categories described in the anavar analysis section.

```
$ ./indel_length_divergence.py -wga /fastdata/bop15hjb/drosophila_data/wga/multiple_alignment/dmel.dsim.dyak.wga.bed.gz -bed /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel_cds.bed -out dmel_length_divergence.txt
$ cat dmel_length_divergence.txt | python length_div_to_all_div.py >> dmel_length_divergence.txt 
$ ./indel_length_divergence.py -wga /fastdata/bop15hjb/drosophila_data/wga/multiple_alignment/dmel.dsim.dyak.wga.bed.gz -bed /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel_noncoding.bed -out dmel_length_divergence_noncoding.txt
$ cat dmel_length_divergence_noncoding.txt | python length_div_to_all_div.py >> dmel_length_divergence_noncoding.txt
```

Divergence data [here](indel_divergence.csv).

Plot of results [here](indel_divergence.pdf).


## anavar analyses

Anavar was run on the coding INDEL data with intergenic and intronic variants as neutral reference. Four models were run, a continuous gamma distribution model, a discrete gamma model with 3 classes, a discrete gamma model with 2 classes and a discrete gamma model with 1 class. For each model a reduced model was also run with equal mutation rates. The commands are as follows:

```
$ cds_vs_neutral_anavar.py -mode indel -vcf /fastdata/bop15hjb/drosophila_data/dmel/analysis_ready_data/dmel_17flys.gatk.raw.indels.recalibrated.filtered_t95.0.pass.dpfiltered.50bp_max.bial.rmarked.polarised.annotated.ar.vcf.gz -n 17 -c 1 -call_csv /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel.callablesites.summary_with_degen.csv -out_pre /fastdata/bop15hjb/drosophila_data/dmel/anavar/anavar1.22_runs/indel/dmel_cds_with_neu_ref_1class -evolgen -n_search 100 -split 50
$ cds_vs_neutral_anavar.py -mode indel -vcf /fastdata/bop15hjb/drosophila_data/dmel/analysis_ready_data/dmel_17flys.gatk.raw.indels.recalibrated.filtered_t95.0.pass.dpfiltered.50bp_max.bial.rmarked.polarised.annotated.ar.vcf.gz -n 17 -c 1 -call_csv /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel.callablesites.summary_with_degen.csv -out_pre /fastdata/bop15hjb/drosophila_data/dmel/anavar/anavar1.22_runs/indel/dmel_cds_with_neu_ref_1class_equal_t -constraint equal_mutation_rate -evolgen -n_search 100 -split 50

$ cds_vs_neutral_anavar.py -mode indel -vcf /fastdata/bop15hjb/drosophila_data/dmel/analysis_ready_data/dmel_17flys.gatk.raw.indels.recalibrated.filtered_t95.0.pass.dpfiltered.50bp_max.bial.rmarked.polarised.annotated.ar.vcf.gz -n 17 -c 2 -call_csv /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel.callablesites.summary_with_degen.csv -out_pre /fastdata/bop15hjb/drosophila_data/dmel/anavar/anavar1.22_runs/indel/dmel_cds_with_neu_ref_2class -evolgen -n_search 100 -split 50
$ cds_vs_neutral_anavar.py -mode indel -vcf /fastdata/bop15hjb/drosophila_data/dmel/analysis_ready_data/dmel_17flys.gatk.raw.indels.recalibrated.filtered_t95.0.pass.dpfiltered.50bp_max.bial.rmarked.polarised.annotated.ar.vcf.gz -n 17 -c 2 -call_csv /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel.callablesites.summary_with_degen.csv -out_pre /fastdata/bop15hjb/drosophila_data/dmel/anavar/anavar1.22_runs/indel_neldermead/dmel_cds_with_neu_ref_2class_equal_t -constraint equal_mutation_rate -n_search 25 -split 200 -alg NLOPT_LN_NELDERMEAD -nnoimp 100 -maximp 1000

$ cds_vs_neutral_anavar.py -mode indel -vcf /fastdata/bop15hjb/drosophila_data/dmel/analysis_ready_data/dmel_17flys.gatk.raw.indels.recalibrated.filtered_t95.0.pass.dpfiltered.50bp_max.bial.rmarked.polarised.annotated.ar.vcf.gz -n 17 -c 3 -call_csv /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel.callablesites.summary_with_degen.csv -out_pre /fastdata/bop15hjb/drosophila_data/dmel/anavar/anavar1.22_runs/indel/dmel_cds_with_neu_ref_3class -evolgen -n_search 100 -split 50
$ cds_vs_neutral_anavar.py -mode indel -vcf /fastdata/bop15hjb/drosophila_data/dmel/analysis_ready_data/dmel_17flys.gatk.raw.indels.recalibrated.filtered_t95.0.pass.dpfiltered.50bp_max.bial.rmarked.polarised.annotated.ar.vcf.gz -n 17 -c 3 -call_csv /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel.callablesites.summary_with_degen.csv -out_pre /fastdata/bop15hjb/drosophila_data/dmel/anavar/anavar1.22_runs/indel/dmel_cds_with_neu_ref_3class_equal_t -constraint equal_mutation_rate -n_search 25 -split 200 -alg NLOPT_LN_NELDERMEAD -nnoimp 100 -maximp 1000

$ cds_vs_neutral_anavar.py -mode indel -vcf /fastdata/bop15hjb/drosophila_data/dmel/analysis_ready_data/dmel_17flys.gatk.raw.indels.recalibrated.filtered_t95.0.pass.dpfiltered.50bp_max.bial.rmarked.polarised.annotated.ar.vcf.gz -n 17 -c 1 -call_csv /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel.callablesites.summary_with_degen.csv -out_pre /fastdata/bop15hjb/drosophila_data/dmel/anavar/anavar1.22_runs/indel/dmel_cds_with_neu_ref_continuous -dfe continuous -degree 500 -n_search 25 -split 200
$ cds_vs_neutral_anavar.py -mode indel -vcf /fastdata/bop15hjb/drosophila_data/dmel/analysis_ready_data/dmel_17flys.gatk.raw.indels.recalibrated.filtered_t95.0.pass.dpfiltered.50bp_max.bial.rmarked.polarised.annotated.ar.vcf.gz -n 17 -c 1 -call_csv /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel.callablesites.summary_with_degen.csv -out_pre /fastdata/bop15hjb/drosophila_data/dmel/anavar/anavar1.22_runs/indel/dmel_cds_with_neu_ref_continuous_equal_t -constraint equal_mutation_rate -dfe continuous -degree 500 -n_search 25 -split 200
```

These analyses were repeated for the SNP data with fourfold reference:

```
$ cds_vs_neutral_anavar.py -mode snp -vcf /fastdata/bop15hjb/drosophila_data/dmel/analysis_ready_data/dmel_17flys.gatk.raw.snps.exsnpindel.recalibrated.filtered_t95.0.pass.dpfiltered.50bp_max.bial.rmarked.polarised.annotated.ar.degen.vcf.gz -n 17 -c 1 -call_csv /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel.callablesites.summary_with_degen.csv -out_pre /fastdata/bop15hjb/drosophila_data/dmel/anavar/anavar1.22_runs/snp/dmel_snps_cds_with_4fold_ref_1class -n_search 100 -split 50
$ cds_vs_neutral_anavar.py -mode snp -vcf /fastdata/bop15hjb/drosophila_data/dmel/analysis_ready_data/dmel_17flys.gatk.raw.snps.exsnpindel.recalibrated.filtered_t95.0.pass.dpfiltered.50bp_max.bial.rmarked.polarised.annotated.ar.degen.vcf.gz -n 17 -c 1 -call_csv /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel.callablesites.summary_with_degen.csv -out_pre /fastdata/bop15hjb/drosophila_data/dmel/anavar/anavar1.22_runs/snp/dmel_snps_cds_with_4fold_ref_1class_equal_t -constraint equal_mutation_rate -n_search 100 -split 50

$ cds_vs_neutral_anavar.py -mode snp -vcf /fastdata/bop15hjb/drosophila_data/dmel/analysis_ready_data/dmel_17flys.gatk.raw.snps.exsnpindel.recalibrated.filtered_t95.0.pass.dpfiltered.50bp_max.bial.rmarked.polarised.annotated.ar.degen.vcf.gz -n 17 -c 2 -call_csv /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel.callablesites.summary_with_degen.csv -out_pre /fastdata/bop15hjb/drosophila_data/dmel/anavar/anavar1.22_runs/snp/dmel_snps_cds_with_4fold_ref_2class -n_search 100 -split 50
$ cds_vs_neutral_anavar.py -mode snp -vcf /fastdata/bop15hjb/drosophila_data/dmel/analysis_ready_data/dmel_17flys.gatk.raw.snps.exsnpindel.recalibrated.filtered_t95.0.pass.dpfiltered.50bp_max.bial.rmarked.polarised.annotated.ar.degen.vcf.gz -n 17 -c 2 -call_csv /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel.callablesites.summary_with_degen.csv -out_pre /fastdata/bop15hjb/drosophila_data/dmel/anavar/anavar1.22_runs/snp/dmel_snps_cds_with_4fold_ref_2class_equal_t -constraint equal_mutation_rate -n_search 100 -split 50

$ cds_vs_neutral_anavar.py -mode snp -vcf /fastdata/bop15hjb/drosophila_data/dmel/analysis_ready_data/dmel_17flys.gatk.raw.snps.exsnpindel.recalibrated.filtered_t95.0.pass.dpfiltered.50bp_max.bial.rmarked.polarised.annotated.ar.degen.vcf.gz -n 17 -c 3 -call_csv /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel.callablesites.summary_with_degen.csv -out_pre /fastdata/bop15hjb/drosophila_data/dmel/anavar/anavar1.22_runs/snp/dmel_snps_cds_with_4fold_ref_3class -n_search 100 -split 50
$ cds_vs_neutral_anavar.py -mode snp -vcf /fastdata/bop15hjb/drosophila_data/dmel/analysis_ready_data/dmel_17flys.gatk.raw.snps.exsnpindel.recalibrated.filtered_t95.0.pass.dpfiltered.50bp_max.bial.rmarked.polarised.annotated.ar.degen.vcf.gz -n 17 -c 3 -call_csv /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel.callablesites.summary_with_degen.csv -out_pre /fastdata/bop15hjb/drosophila_data/dmel/anavar/anavar1.22_runs/snp/dmel_snps_cds_with_4fold_ref_3class_equal_t -constraint equal_mutation_rate -n_search 100 -split 50

$ cds_vs_neutral_anavar.py -mode snp -vcf /fastdata/bop15hjb/drosophila_data/dmel/analysis_ready_data/dmel_17flys.gatk.raw.snps.exsnpindel.recalibrated.filtered_t95.0.pass.dpfiltered.50bp_max.bial.rmarked.polarised.annotated.ar.degen.vcf.gz -n 17 -c 1 -call_csv /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel.callablesites.summary_with_degen.csv -out_pre /fastdata/bop15hjb/drosophila_data/dmel/anavar/anavar1.22_runs/snp/dmel_snps_cds_with_4fold_ref_continuous -dfe continuous -degree 500 -n_search 50 -split 100
$ cds_vs_neutral_anavar.py -mode snp -vcf /fastdata/bop15hjb/drosophila_data/dmel/analysis_ready_data/dmel_17flys.gatk.raw.snps.exsnpindel.recalibrated.filtered_t95.0.pass.dpfiltered.50bp_max.bial.rmarked.polarised.annotated.ar.degen.vcf.gz -n 17 -c 1 -call_csv /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel.callablesites.summary_with_degen.csv -out_pre /fastdata/bop15hjb/drosophila_data/dmel/anavar/anavar1.22_runs/snp/dmel_snps_cds_with_4fold_ref_continuous_equal_t -constraint equal_mutation_rate -dfe continuous -degree 500 -n_search 50 -split 100
```

Finally the analysis was run for nonsense mutations with fourfold reference:

```
$ mkdir /fastdata/bop15hjb/drosophila_data/dmel/anavar/anavar1.22_runs/nonsense_snp
$ ./prep_nonsense_anavar.py -cds_fa_dir /fastdata/bop15hjb/drosophila_data/dmel_ref/cds_fasta/ -out_dir /fastdata/bop15hjb/drosophila_data/dmel/anavar/anavar1.22_runs/nonsense_snp/ -vcf /fastdata/bop15hjb/drosophila_data/dmel/analysis_ready_data/dmel_17flys.gatk.raw.snps.exsnpindel.recalibrated.filtered_t95.0.pass.dpfiltered.50bp_max.bial.rmarked.polarised.annotated.ar.degen.vcf.gz -call_fa /fastdata/bop15hjb/drosophila_data/dmel_ref/callable_sites/dmel.callable.ALL.fa -evolgen
$ ./nonsense_anavar.py -nonsense_list /fastdata/bop15hjb/drosophila_data/dmel/anavar/anavar1.22_runs/nonsense_snp/chromo_nonsense_list.txt -call_csv /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel.callablesites.summary_with_degen.csv -vcf /fastdata/bop15hjb/drosophila_data/dmel/analysis_ready_data/dmel_17flys.gatk.raw.snps.exsnpindel.recalibrated.filtered_t95.0.pass.dpfiltered.50bp_max.bial.rmarked.polarised.annotated.ar.degen.vcf.gz -n 17 -c 1 -dfe discrete -constraint equal_mutation_rate -n_search 25 -split 200 -alg NLOPT_LN_NELDERMEAD -nnoimp 100 -maximp 1000 -out_pre /fastdata/bop15hjb/drosophila_data/dmel/anavar/anavar1.22_runs/nonsense_snp/dmel_snps__nonsense_with_4fold_ref_1class_equal_t -evolgen
$ ./nonsense_anavar.py -nonsense_list /fastdata/bop15hjb/drosophila_data/dmel/anavar/anavar1.22_runs/nonsense_snp/chromo_nonsense_list.txt -call_csv /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel.callablesites.summary_with_degen.csv -vcf /fastdata/bop15hjb/drosophila_data/dmel/analysis_ready_data/dmel_17flys.gatk.raw.snps.exsnpindel.recalibrated.filtered_t95.0.pass.dpfiltered.50bp_max.bial.rmarked.polarised.annotated.ar.degen.vcf.gz -n 17 -c 2 -dfe discrete -constraint equal_mutation_rate -n_search 25 -split 200 -alg NLOPT_LN_NELDERMEAD -nnoimp 100 -maximp 1000 -out_pre /fastdata/bop15hjb/drosophila_data/dmel/anavar/anavar1.22_runs/nonsense_snp/dmel_snps_nonsense_with_4fold_ref_2class_equal_t -evolgen
```

Furthermore fourfold data was also obtained for genes with less than 72% GC.

```
$ ./fourfold_model_data_gc72.py -vcf /fastdata/bop15hjb/drosophila_data/dmel/analysis_ready_data/dmel_17flys.gatk.raw.snps.exsnpindel.recalibrated.filtered_t95.0.pass.dpfiltered.50bp_max.bial.rmarked.polarised.annotated.ar.degen.vcf.gz -fourfold /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel-all-4fold_maxgc72.collapsed.bed.gz -call_fa /fastdata/bop15hjb/drosophila_data/dmel_ref/callable_sites/dmel.callable.ALL.fa
callable: 1303594
sfs: [16710, 6909, 4403, 3273, 2663, 2138, 1995, 1731, 1473, 1406, 1363, 1265, 1216, 1117, 1314, 1641]
pi: 0.0109532141621
theta_w: 0.0114853356203
TajD: -0.201019627549
```

Additionally results from an INDEL model with fourfold refence were obtained:

```
$ cd /fastdata/bop15hjb/drosophila_data/dmel/anavar/kai_runs_revisions/Henry
$ ls 4f_indel_7.1_result/*txt | python ~/drosophila_indels/merge_results.py 4f_indel_7.1_result.merged.txt
$ ls 4f_indel_c\=1/*result/*txt | python ~/drosophila_indels/merge_results.py 4f_indel_c1_result.merged.txt
$ ls 4f_indel_c\=2/*result/*txt | python ~/drosophila_indels/merge_results.py 4f_indel_c2_result.merged.txt
$ ls 4f_indel_c\=3/*result/*txt | python ~/drosophila_indels/merge_results.py 4f_indel_c3_result.merged.txt
ls /fastdata/bop15hjb/drosophila_data/dmel/anavar/kai_runs_revisions/Henry/*merged.txt | ./process_anavar_results.py > dmel_sel_v_neu_anavar_allmodels_results.snp_indel.aic.csv
```

Results [here](dmel_sel_v_neu_anavar_allmodels_results.snp_indel.aic.csv).

The Akaike information criterion (AIC) was calculated for each model as follows:

```
$ cd ~/drosophila_indels/
$ ls /fastdata/bop15hjb/drosophila_data/dmel/anavar/anavar1.22_runs/indel/*merged* | ./process_anavar_results.py > dmel_sel_v_neu_anavar_1run_results_indels.aic.csv
$ ls /fastdata/bop15hjb/drosophila_data/dmel/anavar/anavar1.22_runs/snp/dmel_snps_cds_with_4fold_ref_*merged.results.txt | process_anavar_results.py > dmel_sel_v_4fold_anavar_1run_results_snps.aic.csv 
$ ls /fastdata/bop15hjb/drosophila_data/dmel/anavar/anavar1.22_runs/nonsense_snp/*merged.results.txt | process_anavar_results.py > dmel_nonsense_v_4fold_anavar_1run_results_snps.aic.csv 
```

Results for INDELs: [dmel_sel_v_neu_anavar_1run_results_indels.aic.csv](dmel_sel_v_neu_anavar_1run_results_indels.aic.csv) 
, SNPs: [dmel_sel_v_4fold_anavar_1run_results_snps.aic.csv](dmel_sel_v_4fold_anavar_1run_results_snps.aic.csv) 
and nonsense mutations: [dmel_nonsense_v_4fold_anavar_1run_results_snps.aic.csv](dmel_nonsense_v_4fold_anavar_1run_results_snps.aic.csv).

Additionally the control files used can be found [here](anavar_control_files/).

## anavar analysis by length

To investigate if there differences in the DFE for different lengths of INDEL, we ran the 1 class model on the following 
length categories of INDELS: 1bp, 2bp, 3bp, >= 4bp frame-shifting and >= 6bp in-frame.

```
$ ./length_anavar.py -call_csv /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel.callablesites.summary_with_degen.csv -vcf /fastdata/bop15hjb/drosophila_data/dmel/analysis_ready_data/dmel_17flys.gatk.raw.indels.recalibrated.filtered_t95.0.pass.dpfiltered.50bp_max.bial.rmarked.polarised.annotated.ar.vcf.gz -dfe discrete -constraint equal_mutation_rate -c 1 -n 17 -n_search 25 -split 200 -alg NLOPT_LN_NELDERMEAD -nnoimp 100 -maximp 1000 -out_pre /fastdata/bop15hjb/drosophila_data/dmel/anavar/anavar1.22_runs/indel_lengths/dmel_cds_with_neu_ref_1class_equal_t -evolgen
$ ls /fastdata/bop15hjb/drosophila_data/dmel/anavar/anavar1.22_runs/indel_lengths/*merged* | ./process_anavar_results.py -file_pattern length,_len\(\\dbp\) | cut -f 1-18 -d ',' > dmel_sel_v_neu_anavar_1class_equal_t_lengths.csv
$ grep sel /fastdata/bop15hjb/drosophila_data/dmel/anavar/anavar1.22_runs/indel_lengths/*control* | grep sfs | python n_from_control.py > length_analysis_segsite_numbers.txt 
```

Length results table can be seen [here](dmel_sel_v_neu_anavar_1class_equal_t_lengths.csv) or a plot [here](length_anavar.png).

This was repeated with two and three class models.

```
$ ./length_anavar.py -call_csv /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel.callablesites.summary_with_degen.csv -vcf /fastdata/bop15hjb/drosophila_data/dmel/analysis_ready_data/dmel_17flys.gatk.raw.indels.recalibrated.filtered_t95.0.pass.dpfiltered.50bp_max.bial.rmarked.polarised.annotated.ar.vcf.gz -dfe discrete -constraint equal_mutation_rate -c 2 -n 17 -n_search 25 -split 200 -alg NLOPT_LN_NELDERMEAD -nnoimp 100 -maximp 1000 -out_pre /fastdata/bop15hjb/drosophila_data/dmel/anavar/anavar1.22_runs/indel_lengths/dmel_cds_with_neu_ref_2class_equal_t -evolgen
$ ls /fastdata/bop15hjb/drosophila_data/dmel/anavar/anavar1.22_runs/indel_lengths/*merged* | grep 2class | ./process_anavar_results.py -file_pattern length,_len\(\\dbp\) | cut -f 1-18 -d ',' | > dmel_sel_v_neu_anavar_2class_equal_t_lengths.csv
$ ./length_anavar.py -call_csv /fastdata/bop15hjb/drosophila_data/dmel_ref/dmel.callablesites.summary_with_degen.csv -vcf /fastdata/bop15hjb/drosophila_data/dmel/analysis_ready_data/dmel_17flys.gatk.raw.indels.recalibrated.filtered_t95.0.pass.dpfiltered.50bp_max.bial.rmarked.polarised.annotated.ar.vcf.gz -dfe discrete -constraint equal_mutation_rate -c 3 -n 17 -n_search 25 -split 200 -alg NLOPT_LN_NELDERMEAD -nnoimp 100 -maximp 1000 -out_pre /fastdata/bop15hjb/drosophila_data/dmel/anavar/anavar1.22_runs/indel_lengths/dmel_cds_with_neu_ref_3class_equal_t -evolgen
```

The results table can be seen [here](dmel_sel_v_neu_anavar_2class_equal_t_lengths.csv) or a plot [here](length_anavar_2class.png).

The two models were compared for each length subset as follows:

```
$ printf '1bp\n2bp\n3bp\n4bp+shift\n6bp+inframe\n' | while read i; do ls /fastdata/bop15hjb/drosophila_data/dmel/anavar/anavar1.22_runs/indel_lengths/dmel_cds_with_neu_ref_*$i.merged* | ./process_anavar_results.py -file_pattern length,_len\(\\dbp\); done | grep  ^run | head -n 1  > dmel_sel_v_neu_anavar_allmodels_equal_t_lengths.csv 
$ printf '1bp\n2bp\n3bp\n4bp+shift\n6bp+inframe\n' | while read i; do ls /fastdata/bop15hjb/drosophila_data/dmel/anavar/anavar1.22_runs/indel_lengths/dmel_cds_with_neu_ref_*$i.merged* | ./process_anavar_results.py -file_pattern length,_len\(\\dbp\); done | grep -v ^run >> dmel_sel_v_neu_anavar_allmodels_equal_t_lengths.csv 
```

AIC for each length subset can be found [here](dmel_sel_v_neu_anavar_allmodels_equal_t_lengths.csv).