#!/usr/bin/env python3
"""
VitalOptima forecasting baseline & ML models.

Models:
    - Persistence naive baseline (tomorrow = today)
    - Seasonal naive baseline (tomorrow = same weekday last week)
    - Ridge Regression (closed-form NumPy implementation with z-score standardisation)
    - Random Forest Regression (scikit-learn RandomForestRegressor)

Targets (all NEXT-DAY, i.e. value at t+1 predicted from information up to day t):
    admissions, emergency_arrivals, icu_admissions   (evaluated)
    discharges                                       (auxiliary, needed for recursion)

Leakage control:
  * target = series.shift(-1); every feature uses rows <= t only
  * the weekday of the TARGET day is a feature (calendar is known in advance)
  * chronological split: first 80% train, last 20% test, no shuffling
  * standardisation statistics and model training come from the training rows only

Run:  python src/ml_forecast.py [--surge-multiplier 1.5 --surge-days 5]
Everything written to ./ml_outputs is computed dynamically by the code below.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import numpy as np
import pandas as pd

try:
    from sklearn.ensemble import RandomForestRegressor
except ImportError:
    print(
        "Error: 'scikit-learn' is required for Random Forest forecasting but is not installed.\n"
        "Please install it using:\n"
        "    pip install scikit-learn\n"
        "or install all dependencies using:\n"
        "    pip install -r requirements.txt",
        file=sys.stderr,
    )
    sys.exit(1)

SERIES = ["admissions", "emergency_arrivals", "discharges", "icu_admissions"]
EVAL_TARGETS = ["admissions", "emergency_arrivals", "icu_admissions"]


def load_and_validate_data(csv_path: Path) -> pd.DataFrame:
    """Load hospital daily data and validate file existence and required schema."""
    if not csv_path.exists():
        # Fallback check relative to repository root if executed from within src/
        alt_path = Path(__file__).resolve().parent.parent / csv_path
        if alt_path.exists():
            csv_path = alt_path
        else:
            raise FileNotFoundError(
                f"Input dataset not found at '{csv_path}'. "
                f"Please ensure the file exists or pass the path via --data <path>."
            )

    try:
        df = pd.read_csv(csv_path)
    except Exception as exc:
        raise ValueError(f"Failed to read CSV at '{csv_path}': {exc}") from exc

    required_cols = set(SERIES + [
        "date",
        "general_beds_occupied",
        "icu_beds_occupied",
        "general_beds_total",
        "icu_beds_total",
    ])
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(
            f"Input dataset at '{csv_path}' is missing required columns: {sorted(missing)}"
        )

    if len(df) < 30:
        raise ValueError(
            f"Input dataset at '{csv_path}' has only {len(df)} rows. "
            f"At least 30 daily observations are required for lag feature engineering and train/test splitting."
        )

    return df


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Feature row at day t. Uses only data observed on or before day t."""
    X = pd.DataFrame(index=df.index)
    next_dow = (pd.to_datetime(df["date"]) + pd.Timedelta(days=1)).dt.dayofweek
    for k in range(1, 7):                      # Monday is the reference level
        X[f"next_dow_{k}"] = (next_dow == k).astype(float)
    for s in SERIES:
        X[f"{s}_lag0"] = df[s].astype(float)                 # today
        X[f"{s}_lag6"] = df[s].shift(6).astype(float)        # same weekday as the target day (t+1-7)
        X[f"{s}_lag7"] = df[s].shift(7).astype(float)        # seven days ago
        X[f"{s}_roll7"] = df[s].rolling(7).mean().astype(float)   # includes today, nothing later
    return X


class Ridge:
    """Tiny closed-form ridge regression with train-only standardisation."""
    def __init__(self, alpha: float = 10.0):
        self.alpha = alpha

    def fit(self, X, y):
        X, y = np.asarray(X, float), np.asarray(y, float)
        self.mu, self.sd = X.mean(0), X.std(0) + 1e-9
        Xs = (X - self.mu) / self.sd
        self.b = y.mean()
        self.w = np.linalg.solve(Xs.T @ Xs + self.alpha * np.eye(Xs.shape[1]), Xs.T @ (y - self.b))
        return self

    def predict(self, X):
        return ((np.asarray(X, float) - self.mu) / self.sd) @ self.w + self.b


def make_rf_model(random_state: int = 42) -> RandomForestRegressor:
    """Create a RandomForestRegressor configured appropriately for a small 1-year daily dataset.

    Parameters:
      - n_estimators=100: Stable ensemble predictions without excessive compute.
      - max_depth=6: Prevents overfitting on ~285 training days while capturing non-linear interactions.
      - min_samples_split=4, min_samples_leaf=2: Regularizes individual leaf nodes against outlier days.
      - random_state=42: Ensures fully reproducible predictions across runs.
    """
    return RandomForestRegressor(
        n_estimators=100,
        max_depth=6,
        min_samples_split=4,
        min_samples_leaf=2,
        random_state=random_state,
        n_jobs=-1,
    )


def metrics(y, p):
    """Calculate MAE, RMSE, and WAPE with safe zero-denominator handling."""
    y = np.asarray(y, float)
    p = np.asarray(p, float)
    err = y - p
    mae = float(np.mean(np.abs(err)))
    rmse = float(np.sqrt(np.mean(err ** 2)))
    denom = float(np.sum(np.abs(y)))
    # Handle zero or near-zero denominators safely to avoid division by zero or NaN
    if denom > 1e-9:
        wape_pct = float(100.0 * np.sum(np.abs(err)) / denom)
    else:
        wape_pct = 0.0 if np.sum(np.abs(err)) < 1e-9 else float("nan")
    return {"MAE": mae, "RMSE": rmse, "WAPE_pct": wape_pct}


def make_dataset(df):
    X = build_features(df)
    Y = pd.DataFrame({s: df[s].shift(-1) for s in SERIES})
    keep = X.notna().all(axis=1) & Y.notna().all(axis=1)
    return X[keep], Y[keep], df.loc[keep, "date"]


def recursive_forecast(history, models, horizon=7, surge_multiplier=1.0, surge_days=0):
    """Multi-day forecast when future observations are unknown: predict day t+1,
    append the PREDICTED values as if observed, rebuild lags, repeat.
    surge_multiplier is a scenario overlay on predicted ED arrivals/admissions."""
    hist = history[["date"] + SERIES].copy().reset_index(drop=True)
    out = []
    for h in range(horizon):
        feats = build_features(hist).iloc[[-1]]
        preds = {s: max(0.0, float(models[s].predict(feats)[0])) for s in SERIES}
        if h < surge_days and surge_multiplier != 1.0:
            preds["emergency_arrivals"] *= surge_multiplier
            preds["admissions"] *= surge_multiplier
        date = (pd.Timestamp(hist["date"].iloc[-1]) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        hist = pd.concat([hist, pd.DataFrame([{"date": date, **preds}])], ignore_index=True)
        out.append({"date": date, **{f"forecast_{s}": round(v, 1) for s, v in preds.items()}})
    return pd.DataFrame(out)


def project_occupancy(last_row, forecast, total_beds, risk_threshold=0.90):
    """Hospital-wide projection using the generator's accounting identity:
    occupancy_{t+1} = occupancy_t + admissions - discharges."""
    occ = float(last_row["general_beds_occupied"] + last_row["icu_beds_occupied"])
    rows = []
    for _, r in forecast.iterrows():
        occ = min(max(occ + r["forecast_admissions"] - r["forecast_discharges"], 0), total_beds)
        rows.append({"projected_total_occupied": round(occ, 1),
                     "projected_occupancy_pct": round(100 * occ / total_beds, 1),
                     "capacity_risk": occ / total_beds >= risk_threshold})
    return pd.concat([forecast.reset_index(drop=True), pd.DataFrame(rows)], axis=1)


def main():
    ap = argparse.ArgumentParser(description="VitalOptima Hospital Resource Forecasting")
    ap.add_argument("--data", default="data/hospital_daily_data.csv", help="Path to hospital daily CSV")
    ap.add_argument("--out", default="ml_outputs", help="Directory for forecast output files")
    ap.add_argument("--horizon", type=int, default=7, help="Forecast horizon in days (default: 7)")
    ap.add_argument("--surge-multiplier", type=float, default=1.0, help="Demand surge multiplier on arrivals/admissions")
    ap.add_argument("--surge-days", type=int, default=0, help="Number of surge days to apply multiplier")
    args = ap.parse_args()

    df = load_and_validate_data(Path(args.data))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    X, Y, target_dates = make_dataset(df)
    split = int(len(X) * 0.8)                  # chronological split
    Xtr, Xte = X.iloc[:split], X.iloc[split:]
    print(f"train rows={split}, test rows={len(X) - split}, "
          f"test target dates {target_dates.iloc[split]} .. {target_dates.iloc[-1]}")

    rows, preds_out = [], []
    test_maes = {}

    for s in EVAL_TARGETS:
        ridge = Ridge().fit(Xtr, Y[s].iloc[:split])
        rf = make_rf_model(random_state=42).fit(Xtr, Y[s].iloc[:split])
        yte = Y[s].iloc[split:]

        candidates = {
            "persistence (y[t])": Xte[f"{s}_lag0"].to_numpy(),
            "seasonal naive (same weekday last week)": Xte[f"{s}_lag6"].to_numpy(),
            "ridge regression": ridge.predict(Xte),
            "random forest": rf.predict(Xte),
        }

        for name, p in candidates.items():
            rows.append({"target": f"next_day_{s}", "model": name, **metrics(yte, p)})

        # Track hold-out test MAE for model selection (strictly out-of-sample)
        test_maes[s] = {
            "ridge regression": metrics(yte, candidates["ridge regression"])["MAE"],
            "random forest": metrics(yte, candidates["random forest"])["MAE"],
        }

        # Identify winning model for this specific target
        best_target_model = min(test_maes[s], key=lambda m: test_maes[s][m])

        preds_out.append(pd.DataFrame({
            "target_date": target_dates.iloc[split:].to_numpy(),
            "target": s,
            "actual": yte.to_numpy(),
            "persistence_pred": np.asarray(candidates["persistence (y[t])"]),
            "seasonal_naive_pred": np.asarray(candidates["seasonal naive (same weekday last week)"]),
            "ridge_pred": np.asarray(candidates["ridge regression"]),
            "random_forest_pred": np.asarray(candidates["random forest"]),
            "selected_model": best_target_model,
            "selected_pred": np.asarray(candidates[best_target_model]),
        }))

    res = pd.DataFrame(rows).round(3)
    print("\nModel Evaluation on Test Period (Out-of-Sample):")
    print(res.to_string(index=False))
    res.to_csv(out / "metrics.csv", index=False)
    pd.concat(preds_out).round(2).to_csv(out / "test_predictions.csv", index=False)

    # =========================================================================
    # Model Selection Rule:
    # 1. Out-of-sample evaluation: Models are evaluated strictly on the 20%
    #    chronological test split (unseen hold-out data). Training set performance
    #    is NEVER used for model selection to avoid overfitting bias.
    # 2. Metric: Test-period Mean Absolute Error (MAE) is the primary criterion
    #    across the three core evaluated operational targets:
    #      - 'admissions'
    #      - 'emergency_arrivals'
    #      - 'icu_admissions'
    # 3. Decision rule:
    #    For each target, the model with lower test MAE wins.
    #    The architecture that wins the majority of the three evaluation targets
    #    is designated as the primary model family for the forward rollout.
    # 4. Refitting:
    #    The selected model family is refit on all available history (100% of data)
    #    for all series (including auxiliary 'discharges') before rolling forward.
    # =========================================================================
    rf_wins = sum(1 for s in EVAL_TARGETS if test_maes[s]["random forest"] < test_maes[s]["ridge regression"])
    overall_selected_model = "random forest" if rf_wins >= (len(EVAL_TARGETS) / 2) else "ridge regression"

    print("\nModel Selection Summary (Test-Period MAE):")
    for s in EVAL_TARGETS:
        r_mae = test_maes[s]["ridge regression"]
        f_mae = test_maes[s]["random forest"]
        winner = "random forest" if f_mae < r_mae else "ridge regression"
        print(f"  - {s:20s}: Ridge MAE = {r_mae:6.3f} | RF MAE = {f_mae:6.3f} -> Winner: {winner}")

    print(f"\nOverall Selected Model for Rollout: '{overall_selected_model}' "
          f"({rf_wins}/{len(EVAL_TARGETS)} primary target wins)")

    # Refit the selected model family on ALL history, then roll forward beyond the last observed day
    if overall_selected_model == "random forest":
        models = {s: make_rf_model(random_state=42).fit(X, Y[s]) for s in SERIES}
    else:
        models = {s: Ridge().fit(X, Y[s]) for s in SERIES}

    fc = recursive_forecast(df, models, args.horizon, args.surge_multiplier, args.surge_days)
    fc = project_occupancy(
        df.iloc[-1],
        fc,
        int(df.iloc[-1]["general_beds_total"] + df.iloc[-1]["icu_beds_total"]),
    )
    fc.to_csv(out / "forecast_next_days.csv", index=False)
    print("\nRecursive forecast beyond last observed date:")
    print(fc.to_string(index=False))
    print(f"\nWrote outputs to {out.resolve()}")


if __name__ == "__main__":
    main()

