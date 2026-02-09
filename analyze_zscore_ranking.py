#!/usr/bin/env python3
"""
Z-Score Based Parameter Ranking for Dixon Glacier
==================================================

Following Geck et al. (2021) methodology for Eklutna Glacier, this script
implements multi-criteria parameter optimization using z-scores.

Methodology (from Geck et al. 2021):
1. Calculate RMSE for each variable independently
2. Compute z-scores: Z_i = (RMSE_i - RMSE_mean) / std_dev
3. Normalize z-scores to [0,1] range (higher = better fit)
4. Select parameter sets exceeding threshold for ALL criteria

For Dixon Glacier, we use:
- Zone-specific RMSE (ABL, ELA, ACC)
- Overall RMSE
- Seasonal bias metrics (optional)

Usage:
    python3 analyze_zscore_ranking.py --threshold 0.5 --top_n 250
"""

import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime

# Add analysis functions
sys.path.insert(0, str(Path(__file__).parent))
from analyze_sweep_results import (
    load_observations, load_seasonal_observations,
    compute_rmse_zone_weighted, SWEEP_DIR, GRAPHS_BASE_DIR,
    OBS_ELEVATIONS, WATER_YEAR_INDICES, ZONE_YEARS
)

# Configuration
ANALYSIS_NAME = "zscore_ranking"
OUTPUT_BASE = GRAPHS_BASE_DIR / f"zscore_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def load_sweep_results():
    """Load results from most recent targeted sweep."""
    # Load parameters
    params_file = SWEEP_DIR / "parameters.csv"
    if not params_file.exists():
        raise FileNotFoundError(f"Parameters file not found: {params_file}")

    params_df = pd.read_csv(params_file)
    print(f"Loaded {len(params_df):,} parameter combinations")

    return params_df


def calculate_zone_rmse(params_df, obs_dict, runs_dir):
    """
    Calculate RMSE for each zone (ABL, ELA, ACC) separately.

    Following Geck et al. (2021) multi-criteria approach.
    """
    print("\nCalculating zone-specific RMSE for all parameter sets...")

    zones = ['ABL', 'ELA', 'ACC']
    rmse_results = {
        'run_id': [],
        'rmse_ABL': [],
        'rmse_ELA': [],
        'rmse_ACC': [],
        'rmse_overall': []
    }

    # Calculate RMSE for each parameter set
    from tqdm import tqdm
    import xarray as xr

    for idx, row in tqdm(params_df.iterrows(), total=len(params_df), desc="Computing RMSE"):
        run_id = int(row['run_id'])
        run_dir = runs_dir / f"run_{run_id:06d}"

        # Load binned output
        binned_file = list(run_dir.glob("*binned.nc"))
        if not binned_file:
            continue

        try:
            ds = xr.open_dataset(binned_file[0])

            # Extract monthly mass balance: shape (1, nbins, 48 months)
            monthly_mb = ds['bin_massbalclim'].values[0]  # Remove glacier dimension

            # Extract modeled MB for each zone using same approach as analyze_sweep_results.py
            modeled_dict = {}
            for zone, info in OBS_ELEVATIONS.items():
                bin_idx = info['bin_idx']
                zone_monthly = monthly_mb[bin_idx, :]  # 48 months for this bin

                # Extract years relevant for this zone
                years_for_zone = ZONE_YEARS.get(zone, [2023, 2024])
                for year in years_for_zone:
                    if year in WATER_YEAR_INDICES:
                        start_idx, end_idx = WATER_YEAR_INDICES[year]
                        # Sum monthly values for water year (Oct-Sep)
                        annual_mb = zone_monthly[start_idx:end_idx].sum()
                        modeled_dict[(zone, year)] = annual_mb

            # Calculate RMSE for each zone
            zone_rmse = {}
            all_errors = []

            for zone in zones:
                zone_errors = []
                for key, obs_info in obs_dict.items():
                    if key[0] == zone and key in modeled_dict:
                        obs_val = obs_info['mb_obs']
                        mod_val = modeled_dict[key]
                        error_sq = (obs_val - mod_val) ** 2
                        zone_errors.append(error_sq)
                        all_errors.append(error_sq)

                if zone_errors:
                    zone_rmse[zone] = np.sqrt(np.mean(zone_errors))
                else:
                    zone_rmse[zone] = np.nan

            # Overall RMSE (all observations)
            if all_errors:
                overall_rmse = np.sqrt(np.mean(all_errors))
            else:
                overall_rmse = np.nan

            # Store results
            rmse_results['run_id'].append(run_id)
            rmse_results['rmse_ABL'].append(zone_rmse.get('ABL', np.nan))
            rmse_results['rmse_ELA'].append(zone_rmse.get('ELA', np.nan))
            rmse_results['rmse_ACC'].append(zone_rmse.get('ACC', np.nan))
            rmse_results['rmse_overall'].append(overall_rmse)

            ds.close()

        except Exception as e:
            continue

    # Convert to DataFrame
    rmse_df = pd.DataFrame(rmse_results)

    # Merge with parameters
    results_df = params_df.merge(rmse_df, on='run_id', how='inner')

    # Remove runs with missing RMSE
    results_df = results_df.dropna(subset=['rmse_overall'])

    print(f"\nSuccessfully computed RMSE for {len(results_df):,} runs")
    print(f"  Valid ABL: {results_df['rmse_ABL'].notna().sum():,}")
    print(f"  Valid ELA: {results_df['rmse_ELA'].notna().sum():,}")
    print(f"  Valid ACC: {results_df['rmse_ACC'].notna().sum():,}")

    return results_df


def calculate_zscores(results_df):
    """
    Calculate z-scores following Geck et al. (2021) methodology.

    Z_i = (RMSE_i - RMSE_mean) / std_dev

    Then normalize to [0,1] where higher values = better fit.
    """
    print("\nCalculating z-scores...")

    variables = ['rmse_ABL', 'rmse_ELA', 'rmse_ACC', 'rmse_overall']

    for var in variables:
        if var in results_df.columns:
            # Calculate z-scores
            rmse_values = results_df[var].dropna()
            mean_rmse = rmse_values.mean()
            std_rmse = rmse_values.std()

            # Z-score: negative means better than average
            z_scores = (results_df[var] - mean_rmse) / std_rmse

            # Normalize to [0,1] where 1 = best
            # Better fits (lower RMSE) have negative z-scores
            # So we invert and normalize
            z_scores_normalized = -z_scores  # Invert so higher = better
            z_min = z_scores_normalized.min()
            z_max = z_scores_normalized.max()
            z_scores_normalized = (z_scores_normalized - z_min) / (z_max - z_min)

            # Store results
            results_df[f'zscore_{var}'] = z_scores
            results_df[f'zscore_norm_{var}'] = z_scores_normalized

            print(f"  {var}:")
            print(f"    Mean RMSE: {mean_rmse:.3f}")
            print(f"    Std RMSE:  {std_rmse:.3f}")
            print(f"    Z-score range: {z_scores.min():.2f} to {z_scores.max():.2f}")

    return results_df


def select_best_parameters(results_df, threshold=0.5, top_n=250, min_threshold=0.0):
    """
    Select best-performing parameter sets using z-score threshold.

    Following Geck et al. (2021):
    - Select sets where ALL normalized z-scores exceed threshold
    - If fewer than top_n, lower threshold iteratively
    """
    print(f"\nSelecting best parameter sets (threshold={threshold}, target={top_n})...")

    # Variables to use for selection
    zscore_vars = [col for col in results_df.columns if col.startswith('zscore_norm_rmse_')]

    print(f"  Using variables: {zscore_vars}")

    # Apply threshold to all variables
    mask = results_df[zscore_vars].ge(threshold).all(axis=1)
    selected = results_df[mask].copy()

    print(f"  Parameter sets meeting threshold: {len(selected):,}")

    # If we have more than top_n, select the best based on overall score
    if len(selected) > top_n:
        # Calculate combined score (mean of normalized z-scores)
        selected['combined_zscore'] = selected[zscore_vars].mean(axis=1)
        selected = selected.nlargest(top_n, 'combined_zscore')
        print(f"  Reduced to top {top_n} based on combined z-score")

    # If we have fewer than top_n, iteratively lower threshold
    elif len(selected) < top_n and len(selected) > 0:
        print(f"  WARNING: Only {len(selected)} sets meet threshold")
        print(f"  Keeping threshold at {threshold}")

    elif len(selected) == 0:
        if threshold > min_threshold + 0.05:
            new_threshold = max(min_threshold, threshold - 0.1)
            print(f"  No parameter sets meet threshold {threshold}")
            print(f"  Lowering threshold to {new_threshold}...")
            return select_best_parameters(results_df, threshold=new_threshold, top_n=top_n, min_threshold=min_threshold)
        else:
            # Last resort: just take top N by combined z-score
            print(f"  WARNING: Threshold {threshold} too low, no sets found")
            print(f"  Selecting top {top_n} by combined z-score instead...")
            results_df['combined_zscore'] = results_df[zscore_vars].mean(axis=1)
            selected = results_df.nlargest(top_n, 'combined_zscore').copy()
            print(f"  Selected {len(selected)} parameter sets")

    # Calculate statistics for selected sets
    print(f"\nSelected parameter set statistics:")
    for var in ['rmse_ABL', 'rmse_ELA', 'rmse_ACC', 'rmse_overall']:
        if var in selected.columns:
            values = selected[var].dropna()
            print(f"  {var}: {values.mean():.3f} ± {values.std():.3f} (range: {values.min():.3f}-{values.max():.3f})")

    return selected


def plot_zscore_distribution(results_df, selected_df, output_dir):
    """Plot z-score distributions similar to Geck et al. (2021) Figure 5."""
    print("\nGenerating z-score distribution plots...")

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    axes = axes.flatten()

    # Plot each zone
    zones = ['ABL', 'ELA', 'ACC', 'overall']

    for idx, zone in enumerate(zones):
        ax = axes[idx]

        var_x = f'zscore_norm_rmse_{zone}'

        # Plot all parameter sets
        if zone != 'overall':
            # For individual zones, plot vs overall
            var_y = 'zscore_norm_rmse_overall'
            ax.scatter(results_df[var_x], results_df[var_y],
                      alpha=0.3, s=2, c='gray', label='All parameter sets')

            # Plot selected sets
            ax.scatter(selected_df[var_x], selected_df[var_y],
                      alpha=0.8, s=10, c='red', label=f'Selected (n={len(selected_df)})')

            ax.set_xlabel(f'Normalized z-score for {zone}')
            ax.set_ylabel('Normalized z-score for Overall RMSE')
        else:
            # For overall, show histogram
            ax.hist(results_df[var_x], bins=50, alpha=0.5, color='gray', label='All')
            ax.hist(selected_df[var_x], bins=50, alpha=0.7, color='red', label='Selected')
            ax.set_xlabel('Normalized z-score for Overall RMSE')
            ax.set_ylabel('Frequency')

        ax.axhline(0.5, color='k', linestyle='--', alpha=0.5, linewidth=0.5)
        ax.axvline(0.5, color='k', linestyle='--', alpha=0.5, linewidth=0.5)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)
        ax.set_title(f'{zone} Zone')

    plt.tight_layout()

    output_file = output_dir / 'zscore_distributions.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"  Saved: {output_file}")


def plot_parameter_frequency(selected_df, output_dir):
    """Plot parameter value frequencies similar to Geck et al. (2021) Figure 4."""
    print("\nGenerating parameter frequency plots...")

    params = ['tbias', 'kp', 'ddfsnow', 'ddfsnow_iceratio']

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()

    for idx, param in enumerate(params):
        ax = axes[idx]

        # Create histogram
        values = selected_df[param]
        n_bins = min(30, len(values.unique()))

        counts, bins, patches = ax.hist(values, bins=n_bins, edgecolor='black', alpha=0.7)

        ax.set_xlabel(param)
        ax.set_ylabel('Frequency in top parameter sets')
        ax.set_title(f'Distribution of {param}')
        ax.grid(True, alpha=0.3, axis='y')

        # Add statistics
        mean_val = values.mean()
        median_val = values.median()
        mode_val = values.mode()[0] if len(values.mode()) > 0 else mean_val

        stats_text = f'Mean: {mean_val:.4f}\nMedian: {median_val:.4f}\nMode: {mode_val:.4f}'
        ax.text(0.98, 0.98, stats_text, transform=ax.transAxes,
               verticalalignment='top', horizontalalignment='right',
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5),
               fontsize=8)

    plt.tight_layout()

    output_file = output_dir / 'parameter_frequencies.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"  Saved: {output_file}")


def compare_ranking_methods(results_df, selected_zscore, output_dir):
    """Compare z-score ranking vs simple RMSE ranking."""
    print("\nComparing ranking methods...")

    # Get top N by simple RMSE
    n_selected = len(selected_zscore)
    top_rmse = results_df.nsmallest(n_selected, 'rmse_overall')

    # Compare overlap
    overlap = set(selected_zscore['run_id']) & set(top_rmse['run_id'])

    print(f"\n  Top {n_selected} by z-score method")
    print(f"  Top {n_selected} by RMSE method")
    print(f"  Overlap: {len(overlap)} runs ({len(overlap)/n_selected*100:.1f}%)")

    # Compare RMSE distributions
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))

    zones = ['ABL', 'ELA', 'ACC', 'overall']

    for idx, zone in enumerate(zones):
        ax = axes.flatten()[idx]
        var = f'rmse_{zone}'

        # Box plots
        data = [
            selected_zscore[var].dropna(),
            top_rmse[var].dropna()
        ]

        bp = ax.boxplot(data, labels=['Z-score\nmethod', 'RMSE\nmethod'],
                       patch_artist=True, showmeans=True)

        # Color boxes
        bp['boxes'][0].set_facecolor('lightblue')
        bp['boxes'][1].set_facecolor('lightcoral')

        ax.set_ylabel('RMSE (m w.e.)')
        ax.set_title(f'{zone} Zone')
        ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()

    output_file = output_dir / 'method_comparison.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"  Saved: {output_file}")

    # Save comparison statistics
    comparison_file = output_dir / 'ranking_comparison.txt'
    with open(comparison_file, 'w') as f:
        f.write("=" * 70 + "\n")
        f.write("Comparison of Z-Score vs RMSE Ranking Methods\n")
        f.write("=" * 70 + "\n\n")

        f.write(f"Number of parameter sets: {n_selected}\n")
        f.write(f"Overlap between methods: {len(overlap)} ({len(overlap)/n_selected*100:.1f}%)\n\n")

        f.write("RMSE Statistics (m w.e.):\n")
        f.write("-" * 70 + "\n")
        f.write(f"{'Zone':<12} {'Z-score Method':<30} {'RMSE Method':<30}\n")
        f.write(f"{'':12} {'Mean ± Std (Min-Max)':<30} {'Mean ± Std (Min-Max)':<30}\n")
        f.write("-" * 70 + "\n")

        for zone in zones:
            var = f'rmse_{zone}'
            z_vals = selected_zscore[var].dropna()
            r_vals = top_rmse[var].dropna()

            z_str = f"{z_vals.mean():.3f} ± {z_vals.std():.3f} ({z_vals.min():.3f}-{z_vals.max():.3f})"
            r_str = f"{r_vals.mean():.3f} ± {r_vals.std():.3f} ({r_vals.min():.3f}-{r_vals.max():.3f})"

            f.write(f"{zone:<12} {z_str:<30} {r_str:<30}\n")

    print(f"  Saved: {comparison_file}")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Z-score based parameter ranking following Geck et al. (2021)'
    )
    parser.add_argument('--threshold', type=float, default=0.5,
                       help='Z-score threshold (default: 0.5)')
    parser.add_argument('--top_n', type=int, default=250,
                       help='Number of top parameter sets to select (default: 250)')
    parser.add_argument('--sweep_dir', type=str, default=None,
                       help='Override sweep directory path')
    args = parser.parse_args()

    print("=" * 70)
    print("Z-Score Parameter Ranking for Dixon Glacier")
    print("Following Geck et al. (2021) methodology")
    print("=" * 70)

    # Override sweep dir if provided
    global SWEEP_DIR
    if args.sweep_dir:
        SWEEP_DIR = Path(args.sweep_dir)

    print(f"\nSweep directory: {SWEEP_DIR}")
    print(f"Z-score threshold: {args.threshold}")
    print(f"Target ensemble size: {args.top_n}")

    # Create output directory
    OUTPUT_BASE.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {OUTPUT_BASE}")

    # Load data
    print("\n" + "=" * 70)
    print("STEP 1: Loading Data")
    print("=" * 70)

    params_df = load_sweep_results()
    obs_dict, _ = load_observations()

    # Calculate zone-specific RMSE
    print("\n" + "=" * 70)
    print("STEP 2: Calculate Zone-Specific RMSE")
    print("=" * 70)

    runs_dir = SWEEP_DIR / "runs"
    results_df = calculate_zone_rmse(params_df, obs_dict, runs_dir)

    # Calculate z-scores
    print("\n" + "=" * 70)
    print("STEP 3: Calculate Z-Scores")
    print("=" * 70)

    results_df = calculate_zscores(results_df)

    # Select best parameters
    print("\n" + "=" * 70)
    print("STEP 4: Select Best Parameter Sets")
    print("=" * 70)

    selected_df = select_best_parameters(results_df, threshold=args.threshold, top_n=args.top_n)

    # Generate plots
    print("\n" + "=" * 70)
    print("STEP 5: Generate Analysis Plots")
    print("=" * 70)

    plot_zscore_distribution(results_df, selected_df, OUTPUT_BASE)
    plot_parameter_frequency(selected_df, OUTPUT_BASE)
    compare_ranking_methods(results_df, selected_df, OUTPUT_BASE)

    # Save results
    print("\n" + "=" * 70)
    print("STEP 6: Save Results")
    print("=" * 70)

    # Save full results with z-scores
    results_file = OUTPUT_BASE / 'all_results_with_zscores.csv'
    results_df.to_csv(results_file, index=False)
    print(f"  All results: {results_file}")

    # Save selected parameter sets
    selected_file = OUTPUT_BASE / f'top_{args.top_n}_zscore_parameters.csv'
    selected_df.to_csv(selected_file, index=False)
    print(f"  Selected sets: {selected_file}")

    # Summary statistics
    summary_file = OUTPUT_BASE / 'selection_summary.txt'
    with open(summary_file, 'w') as f:
        f.write("=" * 70 + "\n")
        f.write("Z-Score Parameter Selection Summary\n")
        f.write("=" * 70 + "\n\n")

        f.write(f"Total parameter sets analyzed: {len(results_df):,}\n")
        f.write(f"Parameter sets selected: {len(selected_df):,}\n")
        f.write(f"Z-score threshold used: {args.threshold}\n\n")

        f.write("RMSE Statistics for Selected Sets (m w.e.):\n")
        f.write("-" * 70 + "\n")
        for var in ['rmse_ABL', 'rmse_ELA', 'rmse_ACC', 'rmse_overall']:
            if var in selected_df.columns:
                values = selected_df[var].dropna()
                f.write(f"  {var:20s}: {values.mean():.3f} ± {values.std():.3f}\n")
                f.write(f"  {'':20s}  Range: {values.min():.3f} - {values.max():.3f}\n\n")

        f.write("\nParameter Value Ranges:\n")
        f.write("-" * 70 + "\n")
        for param in ['tbias', 'kp', 'ddfsnow', 'ddfsnow_iceratio']:
            values = selected_df[param]
            f.write(f"  {param:20s}: {values.min():.5f} to {values.max():.5f}\n")
            f.write(f"  {'':20s}  Mean: {values.mean():.5f}, Median: {values.median():.5f}\n\n")

    print(f"  Summary: {summary_file}")

    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)
    print(f"\nResults saved to: {OUTPUT_BASE}")
    print(f"\nKey findings:")
    print(f"  - Selected {len(selected_df):,} parameter sets using z-score method")
    print(f"  - Best overall RMSE: {selected_df['rmse_overall'].min():.3f} m w.e.")
    print(f"  - Mean overall RMSE: {selected_df['rmse_overall'].mean():.3f} ± {selected_df['rmse_overall'].std():.3f} m w.e.")


if __name__ == "__main__":
    main()
