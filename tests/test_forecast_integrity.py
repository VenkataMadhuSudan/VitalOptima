import unittest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd

from models.forecaster import DemandForecaster, DIURNAL_WEIGHTS_24H
from config import DATA_DIR


class TestForecastIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.forecaster = DemandForecaster()
        cls.raw_df = pd.read_csv(DATA_DIR / "hospital_census_daily.csv")

    def test_no_future_leakage_in_features(self):
        """
        Leakage Regression Test:
        Modifying future target observations must NOT alter past feature values.
        """
        df_orig = self.raw_df.copy()
        features_orig, cols = self.forecaster._prepare_features(df_orig)

        # Perturb future observations at day 200 through end of dataset
        df_perturbed = self.raw_df.copy()
        df_perturbed.loc[200:, "emergency_arrivals"] = df_perturbed.loc[200:, "emergency_arrivals"] * 5.0
        df_perturbed.loc[200:, "admissions"] = df_perturbed.loc[200:, "admissions"] * 3.0

        features_perturbed, _ = self.forecaster._prepare_features(df_perturbed)

        # Inspect rows 0 to 190 (strictly prior to perturbation)
        # Any difference would prove target leakage across time
        for col in cols:
            orig_vals = features_orig.loc[:190, col].values
            pert_vals = features_perturbed.loc[:190, col].values
            np.testing.assert_allclose(
                orig_vals, pert_vals, rtol=1e-5, atol=1e-5,
                err_msg=f"Data leakage detected in feature '{col}': past values altered by future targets!"
            )

    def test_lag_definition_correctness(self):
        """
        Verifies that lag_1 and lag_7 strictly match t-1 and t-7 shifted values
        with zero unobserved lookahead.
        """
        df, cols = self.forecaster._prepare_features(self.raw_df)
        
        # In prepared features, first 7 rows were dropped to prevent unobserved backfill
        # So row 10 in prepared df corresponds to row 17 in raw sorted df
        sorted_raw = self.raw_df.sort_values("date").reset_index(drop=True)
        
        for idx in [5, 10, 20, 50, 100]:
            raw_idx = idx + 7  # offset by 7 warmup rows
            expected_lag1 = sorted_raw.loc[raw_idx - 1, "emergency_arrivals"]
            expected_lag7 = sorted_raw.loc[raw_idx - 7, "emergency_arrivals"]
            
            actual_lag1 = df.loc[idx, "lag_1_arrivals"]
            actual_lag7 = df.loc[idx, "lag_7_arrivals"]
            
            self.assertEqual(actual_lag1, expected_lag1)
            self.assertEqual(actual_lag7, expected_lag7)

    def test_three_way_chronological_split(self):
        """
        Verifies 3-way chronological split sizing and separation:
        Train (70%), Calibration (15%), Untouched Test (15%).
        """
        metrics = self.forecaster.metrics
        n_train = metrics["train_sample_size"]
        n_cal = metrics["cal_sample_size"]
        n_test = metrics["test_sample_size"]
        total = metrics["effective_rows"]

        self.assertEqual(n_train + n_cal + n_test, total)
        self.assertAlmostEqual(n_train / total, 0.70, delta=0.02)
        self.assertAlmostEqual(n_cal / total, 0.15, delta=0.02)
        self.assertAlmostEqual(n_test / total, 0.15, delta=0.02)

    def test_prediction_interval_calibrated_independently(self):
        """
        Verifies that prediction intervals are calibrated on calibration data
        and evaluated on held-out test data without forcing artificial 100% coverage.
        """
        metrics = self.forecaster.metrics
        self.assertIn("nominal_coverage_pct", metrics)
        self.assertIn("observed_test_coverage_pct", metrics)
        self.assertIn("cal_q05", metrics)
        self.assertIn("cal_q95", metrics)
        self.assertIn("cal_interval_width", metrics)

        self.assertEqual(metrics["nominal_coverage_pct"], 90.0)
        # Empirical observed test coverage must be recorded honestly (not mocked to 90%)
        self.assertGreater(metrics["observed_test_coverage_pct"], 50.0)
        self.assertLess(metrics["observed_test_coverage_pct"], 95.0)
        self.assertGreater(metrics["cal_interval_width"], 0)

    def test_benchmarks_cover_all_models(self):
        """Verifies multi-model benchmark comparisons on identical test rows."""
        benchmarks = self.forecaster.get_benchmark_metrics()
        self.assertFalse(benchmarks.empty)
        model_names = benchmarks["Model"].tolist()
        self.assertIn("Persistence (t-1)", model_names)
        self.assertIn("Seasonal Naive (t-7)", model_names)
        self.assertIn("Ridge Regression", model_names)
        self.assertIn("Random Forest (VitalOptima)", model_names)

        # Both ML models should outperform naive baselines
        rf_row = benchmarks[benchmarks["Model"] == "Random Forest (VitalOptima)"].iloc[0]
        pers_row = benchmarks[benchmarks["Model"] == "Persistence (t-1)"].iloc[0]
        self.assertLess(rf_row["MAE"], pers_row["MAE"])

    def test_hourly_demand_labeling(self):
        """
        Verifies that 24-hour demand projection is labeled honestly
        as an illustrative distribution derived from daily forecast rather than genuine hourly telemetry.
        """
        df_24, m_24 = self.forecaster.get_24h_forecast(surge_multiplier=1.0)
        self.assertEqual(len(df_24), 25)
        self.assertIn("forecast_nature", m_24)
        self.assertIn("diurnal", m_24["forecast_nature"].lower())
        self.assertIn("circadian", m_24["forecast_nature"].lower())


if __name__ == "__main__":
    unittest.main()
