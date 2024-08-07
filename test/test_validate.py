import pandas as pd
import glob
import sys
import os

'''
Sanity checks of dopseq output
Usage: python test_validate.py {dopseq_dir}
'''

assert pd.__version__.startswith('2')

WD = sys.argv[1]
STAT = os.path.join(WD, 'results/stats.xlsx')
LOGS = glob.iglob(os.path.join(WD, 'results/logs/**/*.log'), recursive=True)
REGS = glob.iglob('results/8_regions/*.tsv')

def run_test(df, test, msg):
    '''If test passes, print message formatted with list of indices'''
    if test.any():
        print(msg.format(', '.join([str(x) for x in df[test].index.tolist()])))

# check stats
print('Checking stats')
sd = pd.read_excel(STAT)
trim_test = (sd.total_reads < sd.trimmed_reads)
run_test(sd, trim_test,
         msg='ERROR: less total reads than trimmed reads for {}')
trim_bp_test = (sd.total_bp < sd.trimmed_bp)
run_test(sd, trim_bp_test,
         msg='ERROR: total bp < trimmed bp for {}')
mapped_test = (sd.trimmed_reads < sd.total_mapped_reads)
run_test(sd, mapped_test,
         'ERROR: less trimmed reads than mapped reads for {}')
duplicated_test = (sd.total_mapped_reads < sd.duplicated_reads)
run_test(sd, duplicated_test,
         msg='ERROR: less mapped reads than duplicated reads for {}')
filter_test = ((sd.total_mapped_reads - sd.duplicated_reads) < sd.mapped_reads_after_filter)
run_test(sd, filter_test,
         msg='ERROR: too many reads remaining after duplicate removal and filtering for {}')
filter_bp_test = (sd.trimmed_bp < sd.mapped_bp_after_filter)
run_test(sd, filter_bp_test,
         msg='ERROR: less trimmed bp than filtered bp for {}')
divergence_test = (sd.error_rate > 10)
run_test(sd, divergence_test,
         msg='ERROR: sequence divergence over 10% for {}')
qual_test = ((sd.average_quality > 40) | (sd.average_quality < 20))
run_test(sd, qual_test,
         msg='ERROR: average mapq not within (20,40) for {}')

# check logs
print('Checking logs')
for fn in LOGS:
    with open(fn) as f:
        for l in f:
            lowl = l.lower()
            for s in ('error', 'warning'):
                if s in lowl:
                    print(fn + ':')
                    sys.stdout.write(l)

# check regs
print('Checking region predictions')
for fn in REGS:
    rd = pd.read_table(fn).fillna(0)
    if (rd['sample'].nunique() != 1):
        print ('ERROR: more than one sample in ' + fn)
    reg_test = (rd.reg_start > rd.reg_end) | (rd.first_pos_start > rd.last_pos_end)
    run_test(rd, reg_test,
             msg='ERROR: region coordinates are wrong for {}')
    regpos_test = (rd.reg_start > rd.first_pos_start) | (rd.reg_end < rd.last_pos_end)
    run_test(rd, regpos_test,
             msg='ERROR: correspondence between region and first/last pos is wrong for {}')
    pos_read_test = (rd.reg_reads < rd.reg_pos)
    run_test(rd, pos_read_test,
             msg='ERROR: more reads than positions for {}')
