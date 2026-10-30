# VitalOptima — Empirical Forecast Evaluation & Benchmark Report

**Document:** `docs/FORECAST_BENCHMARK.md`  
**Dataset:** 365 Days Daily Hospital Census Telemetry (`data/hospital_census_daily.csv`)  
**Evaluation Standard:** Identical Out-of-Sample Timestamps Across Models  
**Reproducibility Directory:** `evaluation/forecasting/`  

---

## 1. Single Held-Out Chronological Test Split (55 Days)

Evaluated on the final 55 days of hospital census telemetry (untouched during training and calibration):

| Model Architecture | MAE (Arrivals) | RMSE | WAPE (%) | Bias ($\bar{\hat{y}} - \bar{y}$) | Error Reduction vs Persistence | Evaluation Category |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Persistence ($t-1$)** | 21.38 | 26.64 | 11.50% | -2.29 | Baseline (0.0%) | Naive Baseline |
| **Seasonal Naive ($t-7$)** | 27.13 | 38.85 | 14.58% | -6.57 | -26.9% | Seasonal Baseline |
| **Ridge Regression ($\alpha=1.0$)** | **16.43** | **22.60** | **8.83%** | **-0.40** | **+23.1%** | Regularized Linear |
| **Random Forest (VitalOptima)** | 16.75 | 22.73 | 9.01% | -2.63 | +21.7% | Tree Ensemble |

### Key Analytical Insight: Ridge Regression vs. Random Forest
Ridge Regression achieved a slightly lower MAE (16.43 vs 16.75) and nearly zero forecast bias (-0.40 vs -2.63) compared to Random Forest on the held-out test split. 

**Root Cause:** Emergency department daily arrivals follow a strong autoregressive inertia ($t-1$ and $t-7$) and calendar cycle that exhibits linear relationships in aggregate volume. Because tree ensembles recursively partition orthogonal feature space, they cannot extrapolate outside the minimum and maximum target bounds seen in training. During sudden seasonal shifts, Ridge's $L_2$ regularization produces well-calibrated, smooth continuous projections.

---

## 2. Multi-Fold Rolling-Origin Backtesting Results

To verify that model performance is consistent across time and not an artifact of a single test split, 5-fold expanding-window cross-validation was conducted over the final 120 days of telemetry (horizon $h=7$ days per fold):

| Model | MAE Mean $\pm$ Std | RMSE Mean $\pm$ Std | WAPE Mean $\pm$ Std (%) | Mean Bias |
| :--- | :---: | :---: | :---: | :---: |
| **Persistence ($t-1$)** | $19.48 \pm 4.36$ | $22.52 \pm 4.79$ | $11.46\% \pm 2.79\%$ | -2.29 |
| **Seasonal Naive ($t-7$)** | $17.14 \pm 6.37$ | $21.50 \pm 7.35$ | $9.92\% \pm 3.25\%$ | -6.57 |
| **Random Forest** | $13.40 \pm 3.95$ | $16.06 \pm 4.81$ | $7.84\% \pm 2.32\%$ | +1.78 |
| **Ridge Regression** | **$13.35 \pm 3.27$** | **$15.56 \pm 3.45$** | **$7.84\% \pm 1.99\%$** | **+0.66** |

### Rolling Backtest Highlights
- Across 5 sequential evaluation folds, Ridge Regression achieves the lowest average MAE ($13.35$), lowest RMSE ($15.56$), lowest variance ($\text{std} = 3.27$), and lowest bias ($+0.66$).
- Both machine learning models achieve a **31.5% error reduction over Naive Persistence** and a **22.1% error reduction over Seasonal Naive**.

---

## 3. Residual Distribution & Error Diagnostics

From `evaluation/forecasting/residual_analysis.json`:

```json
{
  "random_forest": {
    "mean_residual": 2.63,
    "std_residual": 22.79,
    "skewness": 0.38,
    "kurtosis": 0.12,
    "median": 1.45,
    "max_underprediction": 65.2,
    "max_overprediction": -45.8
  },
  "ridge_regression": {
    "mean_residual": 0.40,
    "std_residual": 22.81,
    "skewness": 0.41,
    "kurtosis": 0.28,
    "median": -0.85,
    "max_underprediction": 67.4,
    "max_overprediction": -44.1
  }
}
```

Residual analysis shows symmetric, approximately normal errors with slight positive skewness representing acute, unseasonal arrival spikes.

---

## 4. Reproducibility Artifacts Verification

All benchmarks are fully reproducible by running:
```powershell
python evaluation/generate_evaluation_reports.py
```
This generates and verifies:
1. `evaluation/forecasting/dataset_manifest.json` (SHA-256 data fingerprint)
2. `evaluation/forecasting/run_config.json` (Hyperparameters and random seeds)
3. `evaluation/forecasting/split_summary.json` (Sample sizes and ratios)
4. `evaluation/forecasting/predictions.csv` (Point predictions and intervals)
5. `evaluation/forecasting/fold_metrics.csv` (Fold-by-fold validation results)
6. `evaluation/forecasting/aggregate_metrics.json` (Cross-validation statistics)
7. `evaluation/forecasting/residual_analysis.json` (Error moments and quantiles)
8. `evaluation/forecasting/interval_coverage.json` (Split conformal coverage)
9. `evaluation/forecasting/figures/forecast_vs_actual.png` (Visualization)

