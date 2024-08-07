import os
import pandas as pd
import numpy as np

trim_dir = snakemake.params.trim
dedup_dir = snakemake.params.dedup
filtered_dir = snakemake.params.flt
positions_dir = snakemake.params.pos
samples_file = snakemake.params.samples

trim_suffix = '.trim.txt'
dedup_suffix = '.dedup.txt'
filtered_suffix = '.filter.txt'
positions_suffix = '.bed'

# account for possible dedup skip
# if dedup_dir is None:
#     dedup_done = False
# else:
#     dedup_done = True

def get_trim_stats(file):
    """Parse cutadapt stats"""
    def del_1000_sep(s):
        """Remove thousand separator from string representation of number"""
        return int(''.join(s.split(',')))

    stats = dict()
    with open(file) as f:
        for line in f:
            ll = line.split()
            if line.startswith('Total read pairs processed'):
                stats['total_reads'] = del_1000_sep(ll[-1]) * 2
            elif line.startswith('Pairs written (passing filters)'):
                stats['trimmed_reads'] = del_1000_sep(ll[-2]) * 2
            elif line.startswith('Total reads processed'):
                stats['total_reads'] = del_1000_sep(ll[-1])
            elif line.startswith('Reads written (passing filters)'):
                stats['trimmed_reads'] = del_1000_sep(ll[-2])
            elif line.startswith('Total basepairs processed'):
                stats['total_bp'] = del_1000_sep(ll[-2])
            elif line.startswith('Total written (filtered):'):
                stats['trimmed_bp'] = del_1000_sep(ll[-3])
    return stats


def get_dedup_stats(file):
    """Parse Picard MarkDuplicates stats"""
    stats = []
    read_line = False
    with open(file) as f:
        for line in f:
            if line.startswith('LIBRARY'):
                stats.append(line.strip('\n').lower().split('\t'))
                read_line = True
            elif read_line:
                stats.append(line.strip('\n').split('\t'))
                break
    return dict(zip(stats[0],stats[1]))


def get_filtered_stats(file):
    """Parse samtools stats file"""
    stats = dict()
    with open(file) as f:
        for line in f:
            if line.startswith('SN'):
                ll = line.strip('\n').split('\t')
                stats[ll[1].strip(':').replace(' ', '_')] = ll[2]
    return stats


def get_lane_stats(lane_data):
    """Collect sample statistics by parsing statistics files in analysis folders"""
    prefix = "{}-{}".format(lane_data['sample'], lane_data['unit'])
    lane_stats = dict()
    lane_stats.update(get_trim_stats(os.path.join(trim_dir, prefix + trim_suffix))) # qc->trim
    # if dedup_done:
    lane_stats.update(get_dedup_stats(os.path.join(dedup_dir, prefix + dedup_suffix)))
    lane_stats.update(get_filtered_stats(os.path.join(filtered_dir, prefix + filtered_suffix)))
    for stat in lane_stats.keys():
        try:
            lane_data[stat] = lane_stats[stat]
        except:
            lane_data[stat] = 0
    return lane_data


def fill_columns(cols, df):
    """Fill non-existing columns with zeros"""
    for c in cols:
        if c not in lanes.columns:
            lanes[c] = 0

    return df

def get_positions_stats(sample_data):
    """Calculate summary statistics for positions BED"""
    pos_file = os.path.join(positions_dir, sample_data.name + positions_suffix)
    bed = pd.read_csv(pos_file, sep='\t',
                      header=None, names=['chr', 'start', 'end', 'cov'])
    bed['size'] = bed['end'] - bed['start']
    sample_data['average_position_bp'] = bed['size'].mean()
    sample_data['total_position_bp'] = bed['size'].sum()
    sample_data['average_position_coverage'] = bed['cov'].mean()

    return sample_data


if __name__ == "__main__":
    # import lanes data
    lanes = pd.read_csv(samples_file, sep='\t', dtype='str')

    # collect per-lane statistics
    lanes = lanes.apply(get_lane_stats, axis=1)

    # clean-up and prepare for outputting
    for col in lanes.columns:
        try:
            lanes[col] = pd.to_numeric(lanes[col])
        except:
            pass
            # print(f'{col} not numeric')

    # fill missing data with zeros
    recalc_cols = ['read_pairs_examined',
                   'unpaired_reads_examined',
                   'read_pair_duplicates',
                   'read_pair_optical_duplicates',
                   'unpaired_read_duplicates',
                   'unpaired_read_optical_duplicates']
    fill_columns(recalc_cols, lanes)

    # get total number of mapped reads
    # if dedup_done:
    lanes['total_mapped_reads'] = (lanes['read_pairs_examined'] * 2 +
                                   lanes['unpaired_reads_examined'])
    # else:
    #     lanes['total_mapped_reads'] = lanes['raw total sequences']

    # recalculate duplicates
    lanes['duplicated_reads'] = (lanes['read_pair_duplicates'] * 2 +
                                 lanes['read_pair_optical_duplicates'] * 2 +
                                 lanes['unpaired_read_duplicates'] +
                                 lanes['unpaired_read_optical_duplicates'])

    # fill and rename post-filtering columns
    rename_cols = {'reads_mapped':'mapped_reads_after_filter',
                   'bases_mapped':'mapped_bp_after_filter',
                   'insert_size_average':'average_insert_size'}
    fill_columns(rename_cols.keys(), lanes)
    lanes = lanes.rename(columns=rename_cols)

    # subset and reorder columns
    out_cols = ['sample', 'unit', 'platform', 'adapters', 'fq1', 'fq2',
                'total_reads', 'trimmed_reads', 'total_bp', 'trimmed_bp',
                'total_mapped_reads', 'duplicated_reads', 'percent_duplication',
                'mapped_reads_after_filter', 'mapped_bp_after_filter', 'error_rate',
                'average_length', 'average_insert_size', 'average_quality']
    # fill_columns(out_cols, lanes)
    lanes_out = lanes[out_cols]

    # summarize stats by sample
    samples_out = pd.concat([
        lanes_out.groupby(by='sample')[[
            'total_reads',
            'trimmed_reads',
            'total_bp',
            'trimmed_bp',
            'total_mapped_reads',
            'duplicated_reads',
            'mapped_reads_after_filter',
            'mapped_bp_after_filter'
            ]].sum(),
        lanes_out.groupby(by='sample')[[
            'percent_duplication',
            'error_rate',
            'average_length',
            'average_insert_size',
            'average_quality'
            ]].mean()
        ], axis=1)

    # add per sample positions stats
    samples_out.apply(get_positions_stats, axis=1)

    # write
    writer = pd.ExcelWriter(snakemake.output[0])
    samples_out.to_excel(writer, sheet_name='Samples')
    lanes_out.to_excel(writer, sheet_name='Units', index=False)
    writer._save()
