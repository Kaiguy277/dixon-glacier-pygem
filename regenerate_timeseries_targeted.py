#!/usr/bin/env python3
"""
Regenerate time series plots for targeted sweep analysis (without legend).
"""

import sys
import pandas as pd
from pathlib import Path

# Add the analysis functions
sys.path.insert(0, str(Path(__file__).parent))
from analyze_sweep_results import (
    load_observations, load_seasonal_observations,
    plot_monthly_timeseries, SWEEP_DIR
)

# Configuration
ANALYSIS_DIR = Path("/home/kai/Documents/PYGEM/graphs/analysis_20260202_142027")
SWEEP_NAME = "targeted_extended_20260128_154200"

print("=" * 70)
print("Regenerating Time Series Plots (Top 100, No Legend)")
print("=" * 70)

# Load existing analysis results
data_dir = ANALYSIS_DIR / "data"
results_files = list(data_dir.glob("sweep_analysis_full_*.csv"))
if not results_files:
    print("ERROR: No results file found!")
    sys.exit(1)

results_file = results_files[0]
print(f"\nLoading results from: {results_file}")
results_df = pd.read_csv(results_file)
print(f"  Loaded {len(results_df):,} runs")

# Load observations
print("\nLoading observations...")
obs_dict, _ = load_observations()  # Returns (obs_dict, annual_obs)
seasonal_dict = load_seasonal_observations()

# Output directory
output_dir = ANALYSIS_DIR / "timeseries"

# Regenerate plots
print(f"\nGenerating time series plots (top 100, no legend)...")
plot_monthly_timeseries(
    SWEEP_DIR,
    results_df,
    obs_dict,
    output_dir,
    SWEEP_NAME,
    n_best=100,
    seasonal_dict=seasonal_dict
)

print("\n" + "=" * 70)
print("DONE")
print("=" * 70)
print(f"\nPlots saved to: {output_dir}")
