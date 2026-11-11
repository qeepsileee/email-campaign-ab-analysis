import sqlite3
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from src.analysis import (
    GROUPS, baseline_balance, bootstrap_means, compare_binary,
    holm_adjust, load_data, summarize,
)

ROOT = Path(__file__).resolve().parents[1]


class AnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frame = load_data(ROOT / 'data/raw/hillstrom.csv')
        cls.summary = summarize(cls.frame)

    def test_source_population_is_retained(self):
        self.assertEqual(len(self.frame), 64000)
        self.assertEqual(int(self.frame.duplicated().sum()), 6562)
        self.assertEqual(int(self.summary.customers.sum()), 64000)

    def test_holm_adjustment_preserves_order_and_caps_at_one(self):
        np.testing.assert_allclose(holm_adjust([.04, .001, .03]), [.06, .003, .06])
        np.testing.assert_allclose(holm_adjust([.8, .9]), [1, 1])

    def test_binary_effect_reverses_with_group_order(self):
        a = np.array([1] * 60 + [0] * 940)
        b = np.array([1] * 30 + [0] * 970)
        forward, reverse = compare_binary(a, b), compare_binary(b, a)
        self.assertAlmostEqual(forward['effect'], .03)
        self.assertAlmostEqual(forward['effect'], -reverse['effect'])
        self.assertAlmostEqual(forward['p_two_sided'], reverse['p_two_sided'])

    def test_bootstrap_includes_zero_spend_clients(self):
        values = np.array([0., 0., 0., 20.])
        means = bootstrap_means(values, np.random.default_rng(42), 20000)
        self.assertLess(abs(means.mean() - 5), .12)
        self.assertLess(abs(means.var() - values.var() / len(values)), .3)

    def test_sql_group_metrics_and_effects_match_pandas(self):
        with sqlite3.connect(':memory:') as connection:
            self.frame.to_sql('customers', connection, index=False)
            sql = (ROOT / 'sql/01_group_metrics.sql').read_text()
            result = pd.read_sql_query(sql, connection).set_index('segment').loc[GROUPS]
            np.testing.assert_allclose(result, self.summary[result.columns], rtol=1e-12)
            effects = pd.read_sql_query((ROOT / 'sql/02_effects_vs_control.sql').read_text(), connection)
            control = self.summary.loc['No E-Mail']
            for row in effects.itertuples():
                treatment = self.summary.loc[row.segment]
                self.assertAlmostEqual(row.conversion_effect,
                                       treatment.conversion_rate - control.conversion_rate)
                self.assertAlmostEqual(row.revenue_effect,
                                       treatment.revenue_per_customer - control.revenue_per_customer)
            segments = pd.read_sql_query((ROOT / 'sql/03_customer_segments.sql').read_text(), connection)
            self.assertEqual(int(segments.customers.sum()), 64000)
            self.assertEqual(int(segments.buyers.sum()), int(self.frame.conversion.sum()))

    def test_baseline_balance_does_not_include_outcomes(self):
        result = baseline_balance(self.frame)
        self.assertFalse(set(result.variable) & {'visit', 'conversion', 'spend'})


if __name__ == '__main__':
    unittest.main()
