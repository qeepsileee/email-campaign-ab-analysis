import json
from pathlib import Path

from src.analysis import (
    baseline_balance, compare_groups, describe_segments, diagnostics,
    load_data, reconcile_sql, summarize,
)
from src.plots import create_figures


def main():
    root = Path(__file__).resolve().parent
    result_dir = root / 'results'
    result_dir.mkdir(exist_ok=True)
    frame = load_data(root / 'data/raw/hillstrom.csv')
    summary = summarize(frame)
    effects = compare_groups(frame)
    balance = baseline_balance(frame)
    summary.to_csv(result_dir / 'group_metrics.csv')
    effects.to_csv(result_dir / 'effects.csv', index=False)
    balance.to_csv(result_dir / 'baseline_balance.csv', index=False)
    describe_segments(frame).to_csv(result_dir / 'exploratory_segments.csv', index=False)
    reconcile_sql(frame, summary, root / 'sql/01_group_metrics.sql', result_dir / 'analytics.sqlite')
    diagnostic = diagnostics(frame, summary, balance)
    (result_dir / 'diagnostics.json').write_text(json.dumps(diagnostic, indent=2) + '\n')
    workbook_data = {
        'columns': list(frame.columns), 'rows': frame.to_numpy().tolist(),
        'summary': summary.reset_index().to_dict(orient='records'),
        'effects': effects.to_dict(orient='records'),
    }
    (result_dir / 'workbook_data.json').write_text(json.dumps(workbook_data))
    create_figures(summary, effects, root / 'reports/figures')
    print(summary.to_string())
    print(effects.to_string(index=False))
    print('SQL reconciliation passed. Results saved to results/.')


if __name__ == '__main__':
    main()
