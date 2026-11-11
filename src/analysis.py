import hashlib
import math
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

GROUPS = ['No E-Mail', 'Mens E-Mail', 'Womens E-Mail']
SEED = 20261111
REPLICATES = 30000
SOURCE_SHA256 = '0e5893329d8b93cefecc571777672028290ab69865718020c78c7284f291aece'


def load_data(path):
    path = Path(path)
    frame = pd.read_csv(path)
    expected = ['recency', 'history_segment', 'history', 'mens', 'womens',
                'zip_code', 'newbie', 'channel', 'segment', 'visit', 'conversion', 'spend']
    if frame.shape != (64000, 12) or list(frame.columns) != expected:
        raise ValueError('Unexpected source schema or row count')
    if hashlib.sha256(path.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError('Source checksum does not match the original dataset')
    if frame.isna().any().any():
        raise ValueError('Missing values found')
    for column in ['visit', 'conversion', 'mens', 'womens', 'newbie']:
        if not frame[column].isin([0, 1]).all():
            raise ValueError(f'Invalid binary values: {column}')
    if set(frame.segment) != set(GROUPS):
        raise ValueError('Unexpected experiment groups')
    if (frame.spend < 0).any():
        raise ValueError('Negative spend found')
    if (frame.conversion > frame.visit).any():
        raise ValueError('Purchase without visit found')
    if not ((frame.spend > 0) == (frame.conversion == 1)).all():
        raise ValueError('Spend and conversion do not agree')
    return frame


def summarize(frame):
    summary = frame.groupby('segment').agg(
        customers=('conversion', 'size'), visitors=('visit', 'sum'),
        buyers=('conversion', 'sum'), revenue=('spend', 'sum'),
        visit_rate=('visit', 'mean'), conversion_rate=('conversion', 'mean'),
        revenue_per_customer=('spend', 'mean')).loc[GROUPS]
    summary['revenue_per_buyer'] = summary.revenue / summary.buyers
    return summary


def holm_adjust(p_values):
    p_values = np.asarray(p_values, dtype=float)
    order = np.argsort(p_values)
    adjusted = np.empty(len(p_values))
    running = 0.0
    for rank, index in enumerate(order):
        running = max(running, (len(p_values) - rank) * p_values[index])
        adjusted[index] = min(1.0, running)
    return adjusted


def compare_binary(treatment, control):
    treatment = np.asarray(treatment)
    control = np.asarray(control)
    pt, pc = treatment.mean(), control.mean()
    nt, nc = len(treatment), len(control)
    pooled = (treatment.sum() + control.sum()) / (nt + nc)
    delta = pt - pc
    se_null = math.sqrt(pooled * (1 - pooled) * (1 / nt + 1 / nc))
    se_interval = math.sqrt(pt * (1 - pt) / nt + pc * (1 - pc) / nc)
    return {
        'effect': float(delta), 'relative_lift': float(pt / pc - 1),
        'ci95_low': float(delta - stats.norm.ppf(.975) * se_interval),
        'ci95_high': float(delta + stats.norm.ppf(.975) * se_interval),
        'p_two_sided': float(2 * stats.norm.sf(abs(delta / se_null))),
    }


def bootstrap_means(values, rng, replicates=REPLICATES):
    values = np.asarray(values)
    unique, counts = np.unique(values, return_counts=True)
    means = np.empty(replicates)
    for start in range(0, replicates, 500):
        size = min(500, replicates - start)
        weights = rng.multinomial(len(values), counts / len(values), size=size)
        means[start:start + size] = weights @ unique / len(values)
    return means


def compare_groups(frame, replicates=REPLICATES, seed=SEED):
    rng = np.random.default_rng(seed)
    bootstrap = {group: bootstrap_means(
        frame.loc[frame.segment == group, 'spend'].to_numpy(), rng, replicates
    ) for group in GROUPS}
    control = frame[frame.segment == GROUPS[0]]
    rows = []
    for metric in ['conversion', 'visit', 'spend']:
        family = []
        for group in GROUPS[1:]:
            treatment = frame[frame.segment == group]
            if metric != 'spend':
                result = compare_binary(treatment[metric], control[metric])
            else:
                delta = bootstrap[group] - bootstrap[GROUPS[0]]
                effect = treatment.spend.mean() - control.spend.mean()
                se = math.sqrt(treatment.spend.var(ddof=1) / len(treatment)
                               + control.spend.var(ddof=1) / len(control))
                result = {
                    'effect': float(effect),
                    'relative_lift': float(treatment.spend.mean() / control.spend.mean() - 1),
                    'ci95_low': float(np.quantile(delta, .025)),
                    'ci95_high': float(np.quantile(delta, .975)),
                    'p_two_sided': float(2 * stats.norm.sf(abs(effect / se))),
                }
            result.update(metric=metric, treatment=group, control=GROUPS[0])
            family.append(result)
        for result, adjusted in zip(family, holm_adjust([r['p_two_sided'] for r in family])):
            result['p_holm_within_metric'] = float(adjusted)
        rows.extend(family)
    return pd.DataFrame(rows)


def baseline_balance(frame):
    prepared = pd.concat([
        frame[['recency', 'history', 'mens', 'womens', 'newbie']],
        pd.get_dummies(frame[['channel', 'zip_code', 'history_segment']], dtype=float)
    ], axis=1)
    control = prepared.loc[frame.segment == GROUPS[0]]
    rows = []
    for group in GROUPS[1:]:
        treatment = prepared.loc[frame.segment == group]
        for column in prepared.columns:
            denominator = math.sqrt((treatment[column].var(ddof=1)
                                     + control[column].var(ddof=1)) / 2)
            smd = (treatment[column].mean() - control[column].mean()) / denominator
            rows.append({'treatment': group, 'variable': column, 'smd': float(smd)})
    return pd.DataFrame(rows)


def describe_segments(frame):
    rows = []
    for column in ['newbie', 'channel', 'zip_code', 'history_segment']:
        for level, subset in frame.groupby(column):
            for group, part in subset.groupby('segment'):
                rows.append({
                    'dimension': column, 'level': str(level), 'group': group,
                    'n': len(part), 'conversion': float(part.conversion.mean()),
                    'revenue_per_customer': float(part.spend.mean()),
                })
    return pd.DataFrame(rows)


def reconcile_sql(frame, summary, sql_path, database_path):
    with sqlite3.connect(database_path) as connection:
        frame.to_sql('customers', connection, index=False, if_exists='replace')
        query = Path(sql_path).read_text(encoding='utf-8')
        sql_summary = pd.read_sql_query(query, connection).set_index('segment').loc[GROUPS]
        if not np.allclose(sql_summary.to_numpy(), summary[sql_summary.columns].to_numpy(),
                           rtol=1e-12, atol=1e-10):
            raise ValueError('SQL and pandas metrics do not agree')
    return sql_summary


def diagnostics(frame, summary, balance):
    size_test = stats.chisquare(summary.customers.to_numpy())
    return {
        'rows': len(frame), 'columns': list(frame.columns),
        'missing': int(frame.isna().sum().sum()),
        'identical_rows': int(frame.duplicated().sum()), 'duplicates_removed': 0,
        'negative_spend': int((frame.spend < 0).sum()),
        'source_sha256': SOURCE_SHA256, 'bootstrap_replicates': REPLICATES,
        'random_seed': SEED, 'sql_reconciles': True,
        'group_size_chi2_df2': float(size_test.statistic),
        'group_size_p': float(size_test.pvalue),
        'max_abs_smd_checked_baselines': float(balance.smd.abs().max()),
    }
