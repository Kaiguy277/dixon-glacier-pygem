#!/usr/bin/env python3
"""
Combined Z-Score Analysis for Dixon Glacier
============================================

Analyzes ALL THREE sweeps using z-score methodology following Geck et al. (2021):
- Expanded sweep: 110k runs
- Targeted sweep: 36k runs
- Conservative sweep: 50k runs

Total: ~197k parameter combinations
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

# Add analysis functions
sys.path.insert(0, str(Path(__file__).parent))
from analyze_zscore_ranking import (
    calculate_zone_rmse, calculate_zscores, select_best_parameters,
    plot_zscore_distribution, plot_parameter_frequency, compare_ranking_methods
)
from analyze_sweep_results import (
    load_observations, GRAPHS_BASE_DIR
)

# Sweep directories
EXPANDED_SWEEP = Path("/media/kai/Extreme SSD/Linux_Pygem/expanded_sweep/calibration_expanded_20260122_220448")
TARGETED_SWEEP = Path("/media/kai/Extreme SSD/Linux_Pygem/targeted_sweep/targeted_extended_20260128_154200")
CONSERVATIVE_SWEEP = Path("/media/kai/Extreme SSD/Linux_Pygem/conservative_sweep/conservative_20260203_132620")

# Output
OUTPUT_BASE = GRAPHS_BASE_DIR / f"zscore_combined_all3_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def load_combined_sweeps():
    """Load and combine parameters from all three sweeps."""
    print("Loading parameters from all three sweeps...")

    # Load expanded sweep
    expanded_params = pd.read_csv(EXPANDED_SWEEP / "parameters.csv")
    expanded_params['sweep_source'] = 'expanded'
    expanded_params['runs_dir'] = str(EXPANDED_SWEEP / "runs")
    print(f"  Expanded sweep: {len(expanded_params):,} parameter sets")

    # Load targeted sweep
    targeted_params = pd.read_csv(TARGETED_SWEEP / "parameters.csv")
    targeted_params['sweep_source'] = 'targeted'
    targeted_params['runs_dir'] = str(TARGETED_SWEEP / "runs")
    print(f"  Targeted sweep: {len(targeted_params):,} parameter sets")

    # Load conservative sweep
    conservative_params = pd.read_csv(CONSERVATIVE_SWEEP / "parameters.csv")
    conservative_params['sweep_source'] = 'conservative'
    conservative_params['runs_dir'] = str(CONSERVATIVE_SWEEP / "runs")
    print(f"  Conservative sweep: {len(conservative_params):,} parameter sets")

    # Combine - need to renumber run_ids to avoid conflicts
    targeted_params['run_id'] = targeted_params['run_id'] + 200000  # Offset
    conservative_params['run_id'] = conservative_params['run_id'] + 400000  # Offset

    combined = pd.concat([expanded_params, targeted_params, conservative_params], ignore_index=True)
    print(f"  Combined total: {len(combined):,} parameter sets")

    return combined


def calculate_combined_rmse(params_df, obs_dict):
    """Calculate RMSE for combined dataset from both sweep directories."""
    print("\nCalculating zone-specific RMSE for all parameter sets...")

    zones = ['ABL', 'ELA', 'ACC']
    rmse_results = {
        'run_id': [],
        'rmse_ABL': [],
        'rmse_ELA': [],
        'rmse_ACC': [],
        'rmse_overall': [],
        'sweep_source': []
    }

    from tqdm import tqdm
    import xarray as xr
    from analyze_sweep_results import OBS_ELEVATIONS, WATER_YEAR_INDICES, ZONE_YEARS

    for idx, row in tqdm(params_df.iterrows(), total=len(params_df), desc="Computing RMSE"):
        run_id = int(row['run_id'])
        sweep_source = row['sweep_source']

        # Construct run directory based on source
        if sweep_source == 'expanded':
            actual_run_id = run_id
            run_dir = EXPANDED_SWEEP / "runs" / f"run_{actual_run_id:06d}"
        elif sweep_source == 'targeted':
            actual_run_id = run_id - 200000  # Remove offset
            run_dir = TARGETED_SWEEP / "runs" / f"run_{actual_run_id:06d}"
        else:  # conservative
            actual_run_id = run_id - 400000  # Remove offset
            run_dir = CONSERVATIVE_SWEEP / "runs" / f"run_{actual_run_id:06d}"

        # Load binned output
        binned_file = list(run_dir.glob("*binned.nc"))
        if not binned_file:
            continue

        try:
            ds = xr.open_dataset(binned_file[0])

            # Extract monthly mass balance: shape (1, nbins, 48 months)
            monthly_mb = ds['bin_massbalclim'].values[0]  # Remove glacier dimension

            # Extract modeled MB for each zone
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
            rmse_results['sweep_source'].append(sweep_source)

            ds.close()

        except Exception as e:
            continue

    # Convert to DataFrame
    rmse_df = pd.DataFrame(rmse_results)

    # Merge with parameters
    results_df = params_df.merge(rmse_df, on=['run_id', 'sweep_source'], how='inner')

    # Remove runs with missing RMSE
    results_df = results_df.dropna(subset=['rmse_overall'])

    print(f"\nSuccessfully computed RMSE for {len(results_df):,} runs")
    print(f"  Valid ABL: {results_df['rmse_ABL'].notna().sum():,}")
    print(f"  Valid ELA: {results_df['rmse_ELA'].notna().sum():,}")
    print(f"  Valid ACC: {results_df['rmse_ACC'].notna().sum():,}")
    print(f"  From expanded sweep: {(results_df['sweep_source'] == 'expanded').sum():,}")
    print(f"  From targeted sweep: {(results_df['sweep_source'] == 'targeted').sum():,}")

    return results_df


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Combined z-score analysis for both sweeps'
    )
    parser.add_argument('--threshold', type=float, default=0.5,
                       help='Z-score threshold (default: 0.5)')
    parser.add_argument('--top_n', type=int, default=250,
                       help='Number of top parameter sets to select (default: 250)')
    args = parser.parse_args()

    print("=" * 70)
    print("Combined Z-Score Parameter Ranking for Dixon Glacier")
    print("Following Geck et al. (2021) methodology")
    print("=" * 70)
    print(f"\nExpanded sweep: {EXPANDED_SWEEP}")
    print(f"Targeted sweep: {TARGETED_SWEEP}")
    print(f"Z-score threshold: {args.threshold}")
    print(f"Target ensemble size: {args.top_n}")

    # Create output directory
    OUTPUT_BASE.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {OUTPUT_BASE}")

    # Load data
    print("\n" + "=" * 70)
    print("STEP 1: Loading Data")
    print("=" * 70)

    params_df = load_combined_sweeps()
    obs_dict, _ = load_observations()

    # Calculate zone-specific RMSE
    print("\n" + "=" * 70)
    print("STEP 2: Calculate Zone-Specific RMSE")
    print("=" * 70)

    results_df = calculate_combined_rmse(params_df, obs_dict)

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

    # Additional analysis: breakdown by sweep source
    print("\n" + "=" * 70)
    print("SWEEP SOURCE BREAKDOWN")
    print("=" * 70)

    print(f"\nSelected parameter sets by source:")
    for source in ['expanded', 'targeted']:
        count = (selected_df['sweep_source'] == source).sum()
        pct = count / len(selected_df) * 100
        print(f"  {source.capitalize()}: {count} ({pct:.1f}%)")

    # Best run
    best_run = selected_df.iloc[0]
    print(f"\nBest run (lowest overall RMSE):")
    print(f"  Source: {best_run['sweep_source']}")
    print(f"  Run ID: {int(best_run['run_id'])}")
    print(f"  tbias: {best_run['tbias']:.2f}°C")
    print(f"  kp: {best_run['kp']:.3f}")
    print(f"  ddfsnow: {best_run['ddfsnow']:.6f}")
    print(f"  ddfsnow_iceratio: {best_run['ddfsnow_iceratio']:.3f}")
    print(f"  Overall RMSE: {best_run['rmse_overall']:.3f} m w.e.")

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

    all_results_file = OUTPUT_BASE / "all_results_with_zscores.csv"
    results_df.to_csv(all_results_file, index=False)
    print(f"  All results: {all_results_file}")

    selected_file = OUTPUT_BASE / "top_250_zscore_parameters.csv"
    selected_df.to_csv(selected_file, index=False)
    print(f"  Selected sets: {selected_file}")

    # Save summary
    summary_file = OUTPUT_BASE / "selection_summary.txt"
    with open(summary_file, 'w') as f:
        f.write("=" * 70 + "\n")
        f.write("Combined Z-Score Parameter Selection Summary\n")
        f.write("=" * 70 + "\n\n")

        f.write(f"Total parameter sets analyzed: {len(results_df):,}\n")
        f.write(f"  From expanded sweep: {(results_df['sweep_source'] == 'expanded').sum():,}\n")
        f.write(f"  From targeted sweep: {(results_df['sweep_source'] == 'targeted').sum():,}\n\n")

        f.write(f"Parameter sets selected: {len(selected_df)}\n")
        f.write(f"  From expanded sweep: {(selected_df['sweep_source'] == 'expanded').sum()}\n")
        f.write(f"  From targeted sweep: {(selected_df['sweep_source'] == 'targeted').sum()}\n")
        f.write(f"Z-score threshold used: {args.threshold}\n\n")

        f.write("RMSE Statistics for Selected Sets (m w.e.):\n")
        f.write("-" * 70 + "\n")
        for var in ['rmse_ABL', 'rmse_ELA', 'rmse_ACC', 'rmse_overall']:
            vals = selected_df[var].dropna()
            f.write(f"  {var:<20}: {vals.mean():.3f} ± {vals.std():.3f}\n")
            f.write(f"  {'':<20}  Range: {vals.min():.3f} - {vals.max():.3f}\n\n")

        f.write("\nParameter Value Ranges:\n")
        f.write("-" * 70 + "\n")
        for param in ['tbias', 'kp', 'ddfsnow', 'ddfsnow_iceratio']:
            vals = selected_df[param]
            f.write(f"  {param:<20}: {vals.min():.5f} to {vals.max():.5f}\n")
            f.write(f"  {'':<20}  Mean: {vals.mean():.5f}, Median: {vals.median():.5f}\n\n")

    print(f"  Summary: {summary_file}")

    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)
    print(f"\nResults saved to: {OUTPUT_BASE}")
    print(f"\nKey findings:")
    print(f"  - Selected {len(selected_df)} parameter sets from {len(results_df):,} total")
    print(f"  - Best overall RMSE: {selected_df['rmse_overall'].min():.3f} m w.e.")
    print(f"  - Mean overall RMSE: {selected_df['rmse_overall'].mean():.3f} ± {selected_df['rmse_overall'].std():.3f} m w.e.")


if __name__ == '__main__':
    main()
