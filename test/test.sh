# /#!/usr/bin/env bash

# Test dopseq pipeline with using two samples of 
# fox B chromosomes aligned to dog genome. 

# This test should be run from dopseq folder as
# bash test/test.sh

# exit on first error
set -e

READDIR=test_fastq
GENOMEDIR=test_genome
RUNDIR=$PWD

# enable conda activate
eval "$(conda shell.bash hook)"

# check directory
if [[ $RUNDIR == *dopseq ]]; then
	echo "Test run from $RUNDIR. OK!"
else
	echo "Test should be executed from dopseq dir"
	exit 1
fi

# check and install dopseq env
if [[ ! -f test/env.installed ]]; then

	echo 'Installing dopseq environment'
	mamba env create -f env.yaml
	echo 'Installing dopseq environment complete'
	touch test/env.installed

else
	echo 'Skipping dopseq environment intallation'
fi


# download example reads
if [[ ! -f test/reads.downloaded ]]; then

	# TODO check and install test env
	if [[ ! -f test/test_env.installed ]]; then

		echo 'Installing dopseq_test environment'
		mamba env create -f test/test_env.yaml
		echo 'Installing dopseq_test environment complete'
		touch test/test_env.installed

	else
		echo 'Skipping test environment intallation'
	fi

	conda activate dopseq_test

	echo 'Downloading test reads'
	rm -rf $READDIR
	mkdir -pv $READDIR

	# VVUB2 - sorted DOP-PCR fox B chromosomes from Makunin et al. 2018 Genes
	# do not use -I - differing read names don't work with bwa mem
	fastq-dump --gzip --split-files --outdir $READDIR SRR7429930
	# VVUB5 - microdissected WGA fox B chromosomes from Makunin et al. 2018 Genes
	fastq-dump --gzip --split-files --outdir $READDIR SRR7429928

	touch test/reads.downloaded
	echo 'Downloading test reads complete'
else
	echo 'Skipping test reads downloading'
fi

# download dog reference genome from Ensembl
if [[ ! -f test/genome.downloaded ]]; then

	echo 'Downloading test genome'
	rm -rf $GENOMEDIR
	mkdir -pv $GENOMEDIR
	
	cd $GENOMEDIR
	wget --no-clobber ftp://ftp.ensembl.org/pub/release-94/fasta/canis_familiaris/dna/Canis_familiaris.CanFam3.1.dna_sm.toplevel.fa.gz
	gunzip -v Canis_familiaris.CanFam3.1.dna_sm.toplevel.fa.gz
	cd $RUNDIR

	touch test/genome.downloaded
	echo 'Downloading test genome complete'

else
	echo 'Skipping test genome downloading'
fi

# copy test files
# echo 'Setting up dopseq'
# cp -v test/test_samples.tsv samples.tsv
# cp -v test/test_config.yaml config.yaml
# echo 'Setting up dopseq done'

echo 'Activating dopseq env'
# this will work only if conda bin dir is in $PATH
conda activate dopseq

# run pipeline
echo 'Running dopseq'
snakemake -j 2 --configfile test/test_config.yaml
echo 'Running dopseq complete'

# validate results
echo 'Running validation'
python test/test_validate.py $RUNDIR
echo 'Validation complete'
echo 'All done!'
