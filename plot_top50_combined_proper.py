#!/usr/bin/env python3
"""
Plot Top 50 Runs Timeseries - Combined 3-Sweep Analysis
========================================================

Uses the same format as analyze_sweep_results.py:
- Two subplots: monthly and cumulative mass balance
- Starts from Fall 2022 (Oct 2022)
- Observed values as horizontal lines on monthly plot
- Observed cumulative values as stars on cumulative plot
- Seasonal observations as squares (winter) and diamonds (summer)
"""

import numpy as np
import pandas as pd
import xarray as xr
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt
from tqdm import tqdm

# Paths
TOP_250_CSV = Path("/home/kai/Documents/PYGEM/graphs/zscore_combined_all3_20260208_183456/top_250_zscore_parameters.csv")
OBS_FILE = Path("/home/kai/Documents/PYGEM/inputs/stake_observations_dixon.csv")
OUTPUT_DIR = Path("/home/kai/Documents/PYGEM/graphs/top50_timeseries_combined_proper")

# Zone elevation bins
OBS_ELEVATIONS = {
    'ABL': {'elevation': 804, 'bin_idx': 87},
    'ELA': {'elevation': 1078, 'bin_idx': 46},
    'ACC': {'elevation': 1293, 'bin_idx': 15},
}

# Water year indices (from full 48-month array starting Jan 2022)
WATER_YEAR_INDICES = {
    2023: (9, 21),   # Oct 2022 to Sep 2023
    2024: (21, 33),  # Oct 2023 to Sep 2024
    2025: (33, 45),  # Oct 2024 to Sep 2025
}

# Seasonal indices
SEASONAL_INDICES = {
    2023: {'winter': (9, 16), 'summer': (16, 21)},   # WY2023
    2024: {'winter': (21, 28), 'summer': (28, 33)},  # WY2024
    2025: {'winter': (33, 40), 'summer': (40, 45)},  # WY2025
}

ZONE_YEARS = {
    'ABL': [2023, 2024],
    'ELA': [2023, 2024, 2025],
    'ACC': [2023, 2024, 2025],
}

FALL_2022_IDX = 9  # Index in full 48-month array


def load_observations():
    """Load annual observed mass balance data."""
    obs_df = pd.read_csv(OBS_FILE)
    annual_obs = obs_df[
        (obs_df['period_type'] == 'annual') &
        (obs_df['zone'].isin(['ABL', 'ELA', 'ACC']))
    ].copy()

    obs_dict = {}
    for _, row in annual_obs.iterrows():
        key = (row['zone'], row['year'])
        obs_dict[key] = {
            'mb_obs': row['mb_obs_mwe'],
            'uncertainty': row['mb_obs_uncertainty_mwe'],
        }
    return obs_dict


def load_seasonal_observations():
    """Load winter and summer seasonal mass balance observations."""
    obs_df = pd.read_csv(OBS_FILE)
    seasonal_obs = obs_df[
        (obs_df['period_type'].isin(['winter', 'summer'])) &
        (obs_df['zone'].isin(['ABL', 'ELA', 'ACC']))
    ].copy()

    seasonal_dict = {}
    for _, row in seasonal_obs.iterrows():
        key = (row['zone'], row['year'], row['period_type'])
        seasonal_dict[key] = {
            'mb_obs': row['mb_obs_mwe'],
            'uncertainty': row['mb_obs_uncertainty_mwe'],
            'date_end': pd.Timestamp(row['date_end']),
        }
    return seasonal_dict


def find_binned_file(run_dir):
    """Find the binned NetCDF file in a run directory."""
    binned_files = list(run_dir.glob("*binned.nc"))
    return binned_files[0] if binned_files else None


def plot_zone_timeseries(top_n_params, obs_dict, seasonal_dict, zone, output_dir, n_best=50):
    """Create timeseries plot for a specific zone using the original format."""

    bin_idx = OBS_ELEVATIONS[zone]['bin_idx']
    elev = OBS_ELEVATIONS[zone]['elevation']
    years_for_zone = ZONE_YEARS.get(zone, [2023, 2024])

    # Create time axis (48 months: Jan 2022 - Dec 2025)
    full_time_labels = pd.date_range('2022-01', periods=48, freq='ME')
    time_labels = full_time_labels[FALL_2022_IDX:]  # Start from Fall 2022
    n_months = len(time_labels)

    # Water year and spring boundaries
    wy_boundaries = [pd.Timestamp('2023-10-01'), pd.Timestamp('2024-10-01')]
    spring_boundaries = [pd.Timestamp('2023-05-01'), pd.Timestamp('2024-05-01'), pd.Timestamp('2025-05-01')]

    # Colors
    run_colors = plt.cm.tab10(np.linspace(0, 1, n_best))
    zone_colors = {'ABL': 'red', 'ELA': 'orange', 'ACC': 'blue'}
    obs_colors = {2023: 'green', 2024: 'purple', 2025: 'brown'}
    seasonal_colors_map = {'winter': 'cyan', 'summer': 'magenta'}
    seasonal_marker_styles = {'winter': 's', 'summer': 'D'}

    # Create figure
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)
    all_monthly = []

    print(f"\nPlotting {zone} timeseries...")

    # Load and plot each run
    for i, (idx, row) in enumerate(tqdm(top_n_params.iterrows(), total=len(top_n_params),
                                        desc=f"  Loading {zone} runs")):
        # Determine run directory
        run_id = int(row['run_id'])
        sweep_source = row['sweep_source']

        if sweep_source == 'expanded':
            actual_run_id = run_id
            run_dir = Path(row['runs_dir']) / f"run_{actual_run_id:06d}"
        elif sweep_source == 'targeted':
            actual_run_id = run_id - 200000
            run_dir = Path(row['runs_dir']) / f"run_{actual_run_id:06d}"
        else:  # conservative
            actual_run_id = run_id - 400000
            run_dir = Path(row['runs_dir']) / f"run_{actual_run_id:06d}"

        # Load binned output
        binned_file = find_binned_file(run_dir)
        if binned_file is None:
            continue

        ds = xr.open_dataset(binned_file)
        full_monthly_mb = ds['bin_massbalclim'].values[0, bin_idx, :]
        ds.close()

        # Extract from Fall 2022 onwards
        monthly_mb = full_monthly_mb[FALL_2022_IDX:]
        all_monthly.append(monthly_mb)

        # Plot monthly
        ax1.plot(time_labels, monthly_mb, color=run_colors[i], alpha=0.5,
                linewidth=1)

        # Plot cumulative
        cumulative = np.cumsum(monthly_mb)
        ax2.plot(time_labels, cumulative, color=run_colors[i], alpha=0.5,
                linewidth=1)

    # Compute and plot ensemble mean
    if all_monthly:
        mean_monthly = np.mean(all_monthly, axis=0)
        ax1.plot(time_labels, mean_monthly, color=zone_colors[zone],
                linewidth=3, label='Ensemble Mean', zorder=10)
        mean_cumulative = np.cumsum(mean_monthly)
        ax2.plot(time_labels, mean_cumulative, color=zone_colors[zone],
                linewidth=3, label='Ensemble Mean', zorder=10)

    # Add water year boundaries
    for wy in wy_boundaries:
        ax1.axvline(wy, color='gray', linestyle='--', alpha=0.5, linewidth=1)
        ax2.axvline(wy, color='gray', linestyle='--', alpha=0.5, linewidth=1)

    # Overlay observed annual values
    for year in years_for_zone:
        key = (zone, year)
        if key in obs_dict:
            obs_mb = obs_dict[key]['mb_obs']
            obs_unc = obs_dict[key]['uncertainty']
            start_idx, end_idx = WATER_YEAR_INDICES[year]
            rel_start_idx = start_idx - FALL_2022_IDX
            rel_end_idx = end_idx - FALL_2022_IDX
            wy_start = time_labels[rel_start_idx]
            wy_end = time_labels[rel_end_idx - 1]
            monthly_avg = obs_mb / 12

            # Monthly plot: horizontal line with shaded uncertainty
            ax1.axhspan(monthly_avg - obs_unc/12, monthly_avg + obs_unc/12,
                       xmin=(rel_start_idx)/n_months, xmax=(rel_end_idx)/n_months,
                       alpha=0.2, color=obs_colors[year])
            ax1.hlines(monthly_avg, wy_start, wy_end, colors=obs_colors[year],
                      linewidth=2, linestyles='-',
                      label=f'Obs {year}: {obs_mb:+.2f} mwe (monthly avg)')

            # Cumulative plot: star at end of water year
            if year == 2023:
                expected_cumulative = obs_mb
            elif year == 2024:
                prev_obs = obs_dict.get((zone, 2023), {}).get('mb_obs', 0)
                expected_cumulative = prev_obs + obs_mb
            else:
                prev_2023 = obs_dict.get((zone, 2023), {}).get('mb_obs', 0)
                prev_2024 = obs_dict.get((zone, 2024), {}).get('mb_obs', 0)
                expected_cumulative = prev_2023 + prev_2024 + obs_mb

            ax2.scatter(wy_end, expected_cumulative, s=150, marker='*',
                       c=obs_colors[year], edgecolors='black', linewidths=1,
                       zorder=15, label=f'Obs cumulative end WY{year}: {expected_cumulative:+.2f}')

    # Seasonal observations on cumulative plot
    for year in [2023, 2024, 2025]:
        if year == 2023:
            cumulative_baseline = 0
        elif year == 2024:
            cumulative_baseline = obs_dict.get((zone, 2023), {}).get('mb_obs', 0)
        else:
            cumulative_baseline = (obs_dict.get((zone, 2023), {}).get('mb_obs', 0) +
                                  obs_dict.get((zone, 2024), {}).get('mb_obs', 0))

        # Winter
        winter_key = (zone, year, 'winter')
        if winter_key in seasonal_dict:
            winter_obs = seasonal_dict[winter_key]
            winter_end_date = winter_obs['date_end']
            winter_cumulative = cumulative_baseline + winter_obs['mb_obs']
            ax2.scatter(winter_end_date, winter_cumulative, s=120,
                       marker=seasonal_marker_styles['winter'],
                       c=seasonal_colors_map['winter'], edgecolors='black',
                       linewidths=1, zorder=14,
                       label=f'Winter {year}: {winter_obs["mb_obs"]:+.2f} mwe' if year == 2023 else None)
            ax2.errorbar(winter_end_date, winter_cumulative,
                        yerr=winter_obs['uncertainty'], fmt='none',
                        ecolor=seasonal_colors_map['winter'], capsize=3, alpha=0.7)

        # Summer
        summer_key = (zone, year, 'summer')
        if summer_key in seasonal_dict:
            summer_obs = seasonal_dict[summer_key]
            summer_end_date = summer_obs['date_end']
            winter_mb = seasonal_dict.get(winter_key, {}).get('mb_obs', 0)
            summer_cumulative = cumulative_baseline + winter_mb + summer_obs['mb_obs']
            ax2.scatter(summer_end_date, summer_cumulative, s=120,
                       marker=seasonal_marker_styles['summer'],
                       c=seasonal_colors_map['summer'], edgecolors='black',
                       linewidths=1, zorder=14,
                       label=f'Summer {year}: {summer_obs["mb_obs"]:+.2f} mwe' if year == 2023 else None)
            ax2.errorbar(summer_end_date, summer_cumulative,
                        yerr=summer_obs['uncertainty'], fmt='none',
                        ecolor=seasonal_colors_map['summer'], capsize=3, alpha=0.7)

    # Spring boundaries
    for spring in spring_boundaries:
        ax1.axvline(spring, color='lightblue', linestyle=':', alpha=0.5, linewidth=1)
        ax2.axvline(spring, color='lightblue', linestyle=':', alpha=0.5, linewidth=1)

    # Formatting
    ax1.set_ylabel('Monthly Mass Balance (m w.e.)')
    ax1.set_title(f'{zone} Zone - Monthly Mass Balance\n'
                 f'Elevation: {elev}m | Bin Index: {bin_idx} | Top {n_best} runs by RMSE')
    ax1.grid(True, alpha=0.3)
    ax1.axhline(0, color='black', linewidth=0.5)

    ax2.set_xlabel('Date')
    ax2.set_ylabel('Cumulative Mass Balance (m w.e.)\n(normalized to 0 at Fall 2022)')
    ax2.set_title(f'{zone} Zone - Cumulative Mass Balance (from Fall 2022)')
    ax2.grid(True, alpha=0.3)
    ax2.axhline(0, color='black', linewidth=0.5)

    plt.tight_layout()

    # Save
    output_file = output_dir / f"monthly_mb_{zone}_combined_all3.png"
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"  Saved: {output_file}")
    plt.close()


def main():
    """Main execution."""
    print("=" * 70)
    print("Top 50 Runs Timeseries - Combined 3-Sweep Analysis")
    print("Original Format with Monthly and Cumulative Subplots")
    print("=" * 70)

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\nOutput directory: {OUTPUT_DIR}")

    # Load top 250 parameters
    print("\nLoading top 250 parameter sets...")
    top_250 = pd.read_csv(TOP_250_CSV)
    print(f"Loaded {len(top_250)} parameter sets")

    # Select top 50
    top_50 = top_250.head(50).copy()
    print(f"Selected top 50 for plotting")

    # Show best run info
    best = top_50.iloc[0]
    print(f"\nBest run (rank #1):")
    print(f"  Run ID: {int(best['run_id'])}")
    print(f"  Sweep: {best['sweep_source']}")
    print(f"  Overall RMSE: {best['rmse_overall']:.3f} m w.e.")
    print(f"  tbias: {best['tbias']:.2f}°C")
    print(f"  kp: {best['kp']:.3f}")
    print(f"  ddfsnow: {best['ddfsnow']:.6f}")
    print(f"  ddfsnow_iceratio: {best['ddfsnow_iceratio']:.3f}")

    # Load observations
    print("\nLoading observations...")
    obs_dict = load_observations()
    seasonal_dict = load_seasonal_observations()
    print(f"Loaded {len(obs_dict)} annual observations")
    print(f"Loaded {len(seasonal_dict)} seasonal observations")

    # Create plots for each zone
    for zone in ['ABL', 'ELA', 'ACC']:
        plot_zone_timeseries(top_50, obs_dict, seasonal_dict, zone, OUTPUT_DIR, n_best=50)

    print("\n" + "=" * 70)
    print("All plots completed!")
    print(f"Plots saved to: {OUTPUT_DIR}")
    print("=" * 70)


if __name__ == '__main__':
    main()
