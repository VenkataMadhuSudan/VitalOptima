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

    def test_target_taxonomy_integrity(self):
        """Verifies that all 5 clinical forecasting targets have documented metadata."""
        taxonomy = self.forecaster.get_target_taxonomy()
        required_targets = [
            "emergency_arrivals", "admissions", "icu_admissions", "bed_occupancy", "supply_consumption"
        ]
        for t in required_targets:
            self.assertIn(t, taxonomy)
            meta = taxonomy[t]
            self.assertIn("display_name", meta)
            self.assertIn("frequency", meta)
            self.assertIn("unit", meta)
            self.assertIn("prediction_horizon", meta)
            self.assertIn("missing_data_handling", meta)

    def test_rolling_origin_backtest(self):
        """Verifies 5-fold expanding window cross-validation and metric records."""
        bt = self.forecaster.backtest_results
        self.assertIn("folds", bt)
        self.assertIn("aggregate", bt)
        self.assertGreaterEqual(len(bt["folds"]), 20)  # 5 folds * 4 models = 20 records
        models_in_agg = list(bt["aggregate"].keys())
        self.assertIn("Ridge", models_in_agg)
        self.assertIn("Random_Forest", models_in_agg)
        self.assertIn("Persistence", models_in_agg)

        # Confirm Ridge and RF achieve lower mean MAE than Naive Persistence
        ridge_mae = bt["aggregate"]["Ridge"]["mae_mean"]
        pers_mae = bt["aggregate"]["Persistence"]["mae_mean"]
        self.assertLess(ridge_mae, pers_mae)

    def test_split_conformal_prediction_intervals(self):
        """Verifies split conformal intervals with finite-sample correction."""
        metrics = self.forecaster.metrics
        self.assertIn("conformal_test_coverage_pct", metrics)
        self.assertIn("conformal_interval_halfwidth", metrics)
        self.assertGreater(metrics["conformal_interval_halfwidth"], 0)
        self.assertGreaterEqual(metrics["conformal_test_coverage_pct"], 50.0)

    def test_reproducible_evaluation_artifacts_exist(self):
        """Verifies that machine-readable reproducibility artifacts are created."""
        eval_dir = PROJECT_ROOT / "evaluation" / "forecasting"
        self.assertTrue((eval_dir / "dataset_manifest.json").exists())
        self.assertTrue((eval_dir / "run_config.json").exists())
        self.assertTrue((eval_dir / "predictions.csv").exists())
        self.assertTrue((eval_dir / "fold_metrics.csv").exists())
        self.assertTrue((eval_dir / "aggregate_metrics.json").exists())
        self.assertTrue((eval_dir / "interval_coverage.json").exists())

    def test_independent_validation_metrics_and_durbin_watson(self):
        """Verifies independent validation metrics, Durbin-Watson bounds, and paired significance."""
        import json
        metrics_file = PROJECT_ROOT / "evaluation" / "forecasting" / "independent_validation_metrics.json"
        self.assertTrue(metrics_file.exists(), "independent_validation_metrics.json missing")
        with open(metrics_file, "r") as f:
            data = json.load(f)

        # Durbin-Watson statistic near 2.0
        dw = data["residual_and_conformal_diagnostics"]["durbin_watson_statistic"]
        self.assertTrue(1.2 <= dw <= 2.8, f"Durbin-Watson {dw} outside expected bounds")

        # Ridge vs Persistence MAE reduction
        pers_red = data["statistical_significance_tests"]["Ridge_vs_Persistence"]["mae_reduction_pct"]
        self.assertGreaterEqual(pers_red, 20.0)

        # Paired p-value
        p_val = data["statistical_significance_tests"]["Ridge_vs_Persistence"]["paired_t_test"]["p_value"]
        self.assertLess(p_val, 0.01)

    def test_regime_shift_mathematical_consistency(self):
        """Verifies mathematical explanation of Seasonal Naive degradation under winter surge."""
        import json
        metrics_file = PROJECT_ROOT / "evaluation" / "forecasting" / "independent_validation_metrics.json"
        with open(metrics_file, "r") as f:
            data = json.load(f)

        inv = data["benchmark_inconsistency_investigation"]
        # Test period variance must be higher than train variance (winter surge)
        self.assertGreater(inv["test_variance"], inv["train_variance"])
        # Lag-7 autocorrelation in test period must be lower than train period
        self.assertLess(inv["test_lag7_autocorr"], inv["train_lag7_autocorr"])
        # In single split, Seasonal Naive MAE is higher than Persistence
        self.assertGreater(inv["seasonal_naive_single_mae"], inv["persistence_single_mae"])


if __name__ == "__main__":
    unittest.main()
