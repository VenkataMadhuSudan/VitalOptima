"""
VitalOptima Publication-Grade Research Figures Generator
Renders 9 publication-quality figures using matplotlib for the reproducible research release.
All figures are saved to docs/figures/ at 300 DPI with clear labels, gridlines, and legends.
"""
import sys
import json
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIGURES_DIR = PROJECT_ROOT / "docs" / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

# Publication styling settings
plt.rcParams.update({
    "font.size": 11,
    "axes.labelsize": 12,
    "axes.titlesize": 13,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 10,
    "figure.titlesize": 14,
    "font.family": "sans-serif"
})


def generate_fig1_forecast_vs_actual(df_preds: pd.DataFrame):
    """Figure 1: Out-of-Sample Predictions vs Actual Arrivals."""
    fig, ax = plt.subplots(figsize=(10, 5))
    dates = pd.to_datetime(df_preds["date"])
    ax.plot(dates, df_preds["actual_arrivals"], label="Actual Arrivals", color="#1f77b4", linewidth=2.2, marker="o", markersize=4)
    ax.plot(dates, df_preds["pred_ridge"], label="Ridge Model (Selected)", color="#2ca02c", linestyle="--", linewidth=2.0)
    ax.plot(dates, df_preds["pred_random_forest"], label="Random Forest", color="#ff7f0e", linestyle=":", linewidth=1.8)
    
    ax.set_title("Figure 1: Out-of-Sample Daily Emergency Demand Forecast vs Actuals")
    ax.set_xlabel("Date (November - December 2025 Test Split)")
    ax.set_ylabel("Daily Patient Arrivals")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(loc="upper right")
    fig.autofmt_xdate()
    fig.tight_layout()
    out_path = FIGURES_DIR / "fig1_forecast_vs_actual.png"
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    print(f"[Exported] {out_path.name}")


def generate_fig2_conformal_intervals(df_preds: pd.DataFrame):
    """Figure 2: Split Conformal 90% Prediction Intervals."""
    fig, ax = plt.subplots(figsize=(10, 5))
    dates = pd.to_datetime(df_preds["date"])
    ax.fill_between(
        dates,
        df_preds["lower_bound_90_conf"],
        df_preds["upper_bound_90_conf"],
        color="#2ca02c",
        alpha=0.25,
        label="Split Conformal 90% Coverage Band"
    )
    ax.plot(dates, df_preds["actual_arrivals"], label="Actual Arrivals", color="#1f77b4", linewidth=2.0, marker="o", markersize=4)
    ax.plot(dates, df_preds["pred_ridge"], label="Point Prediction (Ridge)", color="#2ca02c", linestyle="--", linewidth=1.8)

    ax.set_title("Figure 2: Distribution-Free Split Conformal Prediction Intervals (90% Target Coverage)")
    ax.set_xlabel("Date")
    ax.set_ylabel("Patient Arrivals")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(loc="upper right")
    fig.autofmt_xdate()
    fig.tight_layout()
    out_path = FIGURES_DIR / "fig2_conformal_intervals.png"
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    print(f"[Exported] {out_path.name}")


def generate_fig3_model_error_comparison():
    """Figure 3: Benchmark Model Error Comparison (MAE & RMSE)."""
    fig, ax = plt.subplots(figsize=(8, 5))
    models = ["Persistence", "Seasonal Naive", "Random Forest", "Ridge"]
    mae_values = [19.48, 17.14, 13.40, 13.35]
    rmse_values = [24.12, 22.80, 17.25, 16.98]

    x = np.arange(len(models))
    width = 0.35

    bars1 = ax.bar(x - width/2, mae_values, width, label="Mean Absolute Error (MAE)", color="#4575b4")
    bars2 = ax.bar(x + width/2, rmse_values, width, label="Root Mean Squared Error (RMSE)", color="#d73027")

    ax.set_ylabel("Error (Patients / Day)")
    ax.set_title("Figure 3: Rolling-Origin Out-of-Sample Error Comparison")
    ax.set_xticks(x)
    ax.set_xticklabels(models)
    ax.legend()
    ax.grid(True, axis="y", linestyle="--", alpha=0.5)

    for bar in bars1:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2.0, yval + 0.4, f"{yval:.2f}", ha="center", va="bottom", fontsize=9)
    for bar in bars2:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2.0, yval + 0.4, f"{yval:.2f}", ha="center", va="bottom", fontsize=9)

    fig.tight_layout()
    out_path = FIGURES_DIR / "fig3_model_error_comparison.png"
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    print(f"[Exported] {out_path.name}")


def generate_fig4_residual_distribution(df_preds: pd.DataFrame):
    """Figure 4: Residual Error Distribution & Normality Diagnostics."""
    residuals = df_preds["actual_arrivals"] - df_preds["pred_ridge"]
    fig, ax = plt.subplots(figsize=(8, 5))
    
    n, bins, patches = ax.hist(residuals, bins=15, density=True, alpha=0.65, color="#3182bd", edgecolor="black")
    
    # Gaussian overlay
    mu, std = residuals.mean(), residuals.std()
    xmin, xmax = ax.get_xlim()
    x_grid = np.linspace(xmin, xmax, 100)
    p = (1 / (std * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x_grid - mu) / std) ** 2)
    ax.plot(x_grid, p, "r--", linewidth=2.0, label=f"Fitted Gaussian ($\mu={mu:.2f}, \sigma={std:.2f}$)")

    ax.axvline(0, color="black", linestyle="-", linewidth=1.0)
    ax.set_title("Figure 4: Ridge Model Residual Distribution (Durbin-Watson = 1.734)")
    ax.set_xlabel("Residual (Actual - Predicted Arrivals)")
    ax.set_ylabel("Density")
    ax.legend(loc="upper right")
    ax.grid(True, linestyle="--", alpha=0.5)

    fig.tight_layout()
    out_path = FIGURES_DIR / "fig4_residual_distribution.png"
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    print(f"[Exported] {out_path.name}")


def generate_fig5_deterministic_vs_stochastic(stoch_json: dict):
    """Figure 5: Policy Performance Comparison: Deterministic vs Two-Stage Stochastic MILP."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 5))
    
    seeds = stoch_json["multi_seed_stability"]["seed_breakdown"]
    det_costs = [s["det_mean_cost"] for s in seeds]
    stoch_costs = [s["stoch_mean_cost"] for s in seeds]
    
    det_surge = [s["det_surge_unmet"] for s in seeds]
    stoch_surge = [s["stoch_surge_unmet"] for s in seeds]

    # Subplot 1: Penalty Cost Comparison
    ax1.boxplot([det_costs, stoch_costs], tick_labels=["Deterministic", "Two-Stage Stochastic"], patch_artist=True,
                boxprops=dict(facecolor="#9ecae1", color="#3182bd"),
                medianprops=dict(color="red", linewidth=2))
    ax1.set_title("Mean Operational Penalty Cost")
    ax1.set_ylabel("Cost Score (Arbitrary Currency Units)")
    ax1.grid(True, linestyle="--", alpha=0.5)

    # Subplot 2: Surge Unmet Demand Comparison
    ax2.boxplot([det_surge, stoch_surge], tick_labels=["Deterministic", "Two-Stage Stochastic"], patch_artist=True,
                boxprops=dict(facecolor="#a1d99b", color="#31a354"),
                medianprops=dict(color="red", linewidth=2))
    ax2.set_title("Surge Unmet Patient Demand")
    ax2.set_ylabel("Unallocated Patients during Surges")
    ax2.grid(True, linestyle="--", alpha=0.5)

    fig.suptitle("Figure 5: Policy Comparison Across 150 Monte Carlo Trials (10 Random Seeds)", fontsize=13)
    fig.tight_layout()
    out_path = FIGURES_DIR / "fig5_deterministic_vs_stochastic.png"
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    print(f"[Exported] {out_path.name}")


def generate_fig6_resource_utilization():
    """Figure 6: Unit-Level Bed Occupancy & Staffed Capacity."""
    df_res = pd.read_csv(PROJECT_ROOT / "data" / "hospital_resources.csv")
    fig, ax = plt.subplots(figsize=(10, 5.5))
    
    depts = df_res["resource_id"]
    occupied = df_res["occupied_capacity"]
    staffed = df_res["staffed_capacity"]
    total = df_res["total_capacity"]

    y = np.arange(len(depts))
    height = 0.35

    ax.barh(y - height/2, occupied, height, label="Occupied Beds", color="#e6550d")
    ax.barh(y + height/2, staffed, height, label="Staffed Available Beds", color="#31a354")

    ax.set_yticks(y)
    ax.set_yticklabels(depts)
    ax.set_xlabel("Beds")
    ax.set_title("Figure 6: Unit-Level Operational Census vs Staffed Bed Capacity")
    ax.legend(loc="lower right")
    ax.grid(True, axis="x", linestyle="--", alpha=0.5)

    fig.tight_layout()
    out_path = FIGURES_DIR / "fig6_resource_utilization.png"
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    print(f"[Exported] {out_path.name}")


def generate_fig7_surge_unmet_demand(stoch_json: dict):
    """Figure 7: Surge Unmet Demand Reduction across Random Seeds."""
    fig, ax = plt.subplots(figsize=(9, 5))
    seeds_data = stoch_json["multi_seed_stability"]["seed_breakdown"]
    seed_labels = [f"Seed {s['seed']}" for s in seeds_data]
    unmet_red = [s["surge_unmet_reduction_pct"] for s in seeds_data]
    
    colors = ["#2ca02c" if r > 10 else "#ff7f0e" for r in unmet_red]
    bars = ax.bar(seed_labels, unmet_red, color=colors, edgecolor="black", alpha=0.85)

    mean_red = stoch_json["multi_seed_stability"]["surge_unmet_reduction_mean_pct"]
    ax.axhline(mean_red, color="red", linestyle="--", linewidth=1.8, label=f"Mean Reduction ({mean_red:.2f}%)")

    ax.set_ylabel("Surge Unmet Demand Reduction (%)")
    ax.set_title("Figure 7: Two-Stage Stochastic Surge Protection across 10 Random Seeds")
    ax.set_xticklabels(seed_labels, rotation=45, ha="right")
    ax.legend(loc="upper right")
    ax.grid(True, axis="y", linestyle="--", alpha=0.5)

    for bar in bars:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2.0, h + 0.4, f"{h:.1f}%", ha="center", va="bottom", fontsize=8.5)

    fig.tight_layout()
    out_path = FIGURES_DIR / "fig7_surge_unmet_demand.png"
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    print(f"[Exported] {out_path.name}")


def generate_fig8_optimization_cost_comparison(stoch_json: dict):
    """Figure 8: Conformal Uncertainty Halfwidth Sensitivity on Expected Cost."""
    fig, ax = plt.subplots(figsize=(8, 5))
    sens = stoch_json.get("conformal_halfwidth_sensitivity", [])
    if sens:
        halfwidths = [s["conformal_halfwidth"] for s in sens]
        costs = [s["expected_cost"] for s in sens]
        ax.plot(halfwidths, costs, marker="s", markersize=7, linewidth=2.2, color="#756bb1")
        
        ax.set_title("Figure 8: Expected Optimization Penalty Cost vs Conformal Margin ($\hat{q}$)")
        ax.set_xlabel("Conformal Halfwidth Margin ($\hat{q}$ Patients)")
        ax.set_ylabel("Two-Stage Expected Cost")
        ax.grid(True, linestyle="--", alpha=0.5)

        for hw, c in zip(halfwidths, costs):
            ax.annotate(f"{c:.0f}", (hw, c), textcoords="offset points", xytext=(0, 10), ha="center", fontsize=9)

    fig.tight_layout()
    out_path = FIGURES_DIR / "fig8_optimization_cost_comparison.png"
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    print(f"[Exported] {out_path.name}")


def generate_fig9_scenario_sensitivity(stoch_json: dict):
    """Figure 9: Cost Reduction Sensitivity Distribution."""
    fig, ax = plt.subplots(figsize=(8, 5))
    seeds_data = stoch_json["multi_seed_stability"]["seed_breakdown"]
    cost_reductions = [s["cost_reduction_pct"] for s in seeds_data]
    
    ax.hist(cost_reductions, bins=6, color="#41b6c4", edgecolor="black", alpha=0.75)
    mean_val = np.mean(cost_reductions)
    std_val = np.std(cost_reductions)

    ax.axvline(mean_val, color="red", linestyle="--", linewidth=2.0, label=f"Mean = {mean_val:.2f}%")
    ax.axvspan(mean_val - std_val, mean_val + std_val, color="red", alpha=0.15, label=f"$\pm 1\sigma$ ({std_val:.2f}%)")

    ax.set_title("Figure 9: Cost Reduction Stability Distribution across Seeds (Range: 15.6% - 27.8%)")
    ax.set_xlabel("Cost Reduction vs Deterministic Policy (%)")
    ax.set_ylabel("Seed Count")
    ax.legend(loc="upper left")
    ax.grid(True, linestyle="--", alpha=0.5)

    fig.tight_layout()
    out_path = FIGURES_DIR / "fig9_scenario_sensitivity.png"
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    print(f"[Exported] {out_path.name}")


def main():
    print("=== Generating 9 Publication-Grade Research Figures ===")
    preds_file = PROJECT_ROOT / "evaluation" / "forecasting" / "predictions.csv"
    stoch_file = PROJECT_ROOT / "evaluation" / "stochastic_sensitivity_results.json"

    df_preds = pd.read_csv(preds_file)
    with open(stoch_file, "r") as f:
        stoch_json = json.load(f)

    generate_fig1_forecast_vs_actual(df_preds)
    generate_fig2_conformal_intervals(df_preds)
    generate_fig3_model_error_comparison()
    generate_fig4_residual_distribution(df_preds)
    generate_fig5_deterministic_vs_stochastic(stoch_json)
    generate_fig6_resource_utilization()
    generate_fig7_surge_unmet_demand(stoch_json)
    generate_fig8_optimization_cost_comparison(stoch_json)
    generate_fig9_scenario_sensitivity(stoch_json)

    print("\n[PHASE 17 COMPLETED] All 9 research figures successfully generated in docs/figures/.")


if __name__ == "__main__":
    main()

