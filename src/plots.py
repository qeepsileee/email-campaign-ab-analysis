from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import numpy as np

from src.analysis import GROUPS


def create_figures(summary, effects, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11,
                         'axes.spines.top': False, 'axes.spines.right': False,
                         'axes.titleweight': 'bold', 'figure.facecolor': '#f5f7fb',
                         'axes.facecolor': '#f5f7fb', 'text.color': '#172338',
                         'axes.labelcolor': '#172338', 'xtick.color': '#526178',
                         'ytick.color': '#526178'})
    colors = ['#9aa6b6', '#275dad', '#44a89a']
    labels = ['No email', 'Mens email', 'Womens email']
    figure, axes = plt.subplots(2, 2, figsize=(13, 8.8))
    figure.subplots_adjust(top=.85, bottom=.12, hspace=.48, wspace=.3)
    figure.suptitle('Do email campaigns lead to more purchases?', x=.07, ha='left',
                   fontsize=21, fontweight='bold', y=.97)
    figure.text(.07, .90, 'Hillstrom experiment  |  64,000 customers  |  Two-week outcomes',
                color='#526178', fontsize=12)
    for ax, column, title, formatter in [
        (axes[0, 0], 'conversion_rate', 'Purchase conversion', lambda v: f'{v:.3%}'),
        (axes[0, 1], 'revenue_per_customer', 'Revenue per assigned customer', lambda v: f'${v:.3f}'),
    ]:
        values = summary.loc[GROUPS, column].to_numpy()
        bars = ax.bar(labels, values, color=colors, width=.55)
        ax.set_title(title, loc='left', pad=18)
        ax.set_ylim(0, max(values)*1.28)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, p: formatter(v)))
        ax.bar_label(bars, labels=[formatter(v) for v in values], padding=7, fontsize=11)
        ax.grid(axis='y', alpha=.12)
        ax.set_axisbelow(True)
    for ax, metric, scale, title, unit in [
        (axes[1, 0], 'conversion', 100, 'Extra purchase conversion vs control', 'Percentage points'),
        (axes[1, 1], 'spend', 1, 'Extra revenue per customer vs control', 'USD'),
    ]:
        subset = effects[effects.metric == metric].set_index('treatment').loc[GROUPS[1:]]
        values = subset.effect.to_numpy()*scale
        errors = np.vstack([values-subset.ci95_low.to_numpy()*scale,
                            subset.ci95_high.to_numpy()*scale-values])
        ax.errorbar(values, [1, 0], xerr=errors, fmt='o', color=colors[1],
                    ecolor='#71839c', capsize=6, markersize=8, linewidth=2)
        ax.set_yticks([1, 0], labels[1:])
        ax.axvline(0, color='#9aa6b6', linestyle='--', linewidth=1)
        ax.set_ylim(-.65, 1.65)
        ax.set_xlim(left=-.06)
        ax.set_title(title, loc='left', pad=18)
        ax.set_xlabel(unit)
        ax.grid(axis='x', alpha=.12)
    figure.text(.07, .035, 'Intervals: ordinary 95% CI; revenue uses 30,000 bootstrap samples. '
                'Revenue is not profit.', fontsize=10, color='#526178')
    figure.savefig(output / 'overview.png', dpi=150, facecolor=figure.get_facecolor())
    plt.close(figure)
