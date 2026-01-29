#!/usr/bin/env python3
"""
Regenerate time series plots with top 50 runs instead of top 5.
Uses existing analysis results to avoid re-processing all runs.
"""

import pandas as pd
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
from pathlib import Path

# Configuration - use the most recent analysis
ANALYSIS_DIR = Path("/home/kai/Documents/PYGEM/graphs/analysis_20260128_112331")
SWEEP_DIR = Path("/media/kai/Extreme SSD/Linux_Pygem/expanded_sweep/calibration_expanded_20260122_220448")
OBS_FILE = Path("/home/kai/Documents/PYGEM/inputs/stake_observations_dixon.csv")

# Observation elevations and bin indices
OBS_ELEVATIONS = {
    'ABL': {'elevation': 804, 'bin_idx': 87},
    'ELA': {'elevation': 1078, 'bin_idx': 46},
    'ACC': {'elevation': 1293, 'bin_idx': 15},
}

ZONE_YEARS = {
    'ABL': [2023, 2024],
    'ELA': [2023, 2024, 2025],
    'ACC': [2023, 2024, 2025],
}

WATER_YEAR_INDICES = {
    2023: (9, 21),
    2024: (21, 33),
    2025: (33, 45),
}


def load_observations():
    """Load annual observations."""
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
    """Load seasonal observations."""
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
            'date_start': pd.to_datetime(row['date_start']),
            'date_end': pd.to_datetime(row['date_end']),
        }
    return seasonal_dict


def find_binned_file(run_dir):
    """Find the binned NetCDF file in a run directory."""
    binned_files = list(run_dir.glob("*binned.nc"))
    if binned_files:
        return binned_files[0]
    return None


def plot_monthly_timeseries_top50(sweep_dir, results_df, obs_dict, output_dir, sweep_name, n_best=50, seasonal_dict=None):
    """
    Plot monthly mass balance time series for each zone with top 50 runs.
    """
    runs_dir = sweep_dir / "runs"

    if seasonal_dict is None:
        seasonal_dict = load_seasonal_observations()

    # Get top N best runs
    sorted_df = results_df.sort_values('combined_rmse').head(n_best)
    best_run_ids = sorted_df['run_id'].tolist()

    print(f"Plotting top {n_best} runs...")
    print(f"RMSE range: {sorted_df['combined_rmse'].iloc[0]:.3f} - {sorted_df['combined_rmse'].iloc[-1]:.3f}")

    # Create time axis (48 months: Jan 2022 - Dec 2025)
    full_time_labels = pd.date_range('2022-01', periods=48, freq='ME')
    FALL_2022_IDX = 9
    time_labels = full_time_labels[FALL_2022_IDX:]
    n_months = len(time_labels)

    # Water year boundaries
    wy_boundaries = [pd.Timestamp('2023-10-01'), pd.Timestamp('2024-10-01')]
    spring_boundaries = [pd.Timestamp('2023-05-01'), pd.Timestamp('2024-05-01'), pd.Timestamp('2025-05-01')]

    # Use a colormap that works well with 50 runs
    run_colors = plt.cm.viridis(np.linspace(0, 0.9, n_best))
    zones = ['ABL', 'ELA', 'ACC']
    zone_colors = {'ABL': 'red', 'ELA': 'orange', 'ACC': 'blue'}

    for zone in zones:
        bin_idx = OBS_ELEVATIONS[zone]['bin_idx']
        elev = OBS_ELEVATIONS[zone]['elevation']
        years_for_zone = ZONE_YEARS.get(zone, [2023, 2024])

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12), sharex=True)
        all_monthly = []

        # Load and plot each best run
        for i, run_id in enumerate(best_run_ids):
            run_dir = runs_dir / f"run_{int(run_id):06d}"
            binned_file = find_binned_file(run_dir)
            if binned_file is None:
                continue

            ds = xr.open_dataset(binned_file)
            full_monthly_mb = ds['bin_massbalclim'].values[0, bin_idx, :]
            ds.close()

            monthly_mb = full_monthly_mb[FALL_2022_IDX:]
            all_monthly.append(monthly_mb)

            # Use lighter alpha for individual runs since there are 50
            ax1.plot(time_labels, monthly_mb, color=run_colors[i], alpha=0.3,
                    linewidth=0.8)
            cumulative = np.cumsum(monthly_mb)
            ax2.plot(time_labels, cumulative, color=run_colors[i], alpha=0.3,
                    linewidth=0.8)

        # Compute and plot ensemble mean
        if all_monthly:
            all_monthly = np.array(all_monthly)
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
        obs_colors = {2023: 'green', 2024: 'purple', 2025: 'brown'}
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

                ax1.axhspan(monthly_avg - obs_unc/12, monthly_avg + obs_unc/12,
                           xmin=(rel_start_idx)/n_months, xmax=(rel_end_idx)/n_months,
                           alpha=0.2, color=obs_colors[year])
                ax1.hlines(monthly_avg, wy_start, wy_end, colors=obs_colors[year],
                          linewidth=2, linestyles='-',
                          label=f'Obs {year}: {obs_mb:+.2f} mwe (monthly avg)')

                # Cumulative plot
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

        # Seasonal observations
        seasonal_marker_styles = {'winter': 's', 'summer': 'D'}
        seasonal_colors_map = {'winter': 'cyan', 'summer': 'magenta'}

        for year in [2023, 2024, 2025]:
            if year == 2023:
                cumulative_baseline = 0
            elif year == 2024:
                cumulative_baseline = obs_dict.get((zone, 2023), {}).get('mb_obs', 0)
            else:
                cumulative_baseline = (obs_dict.get((zone, 2023), {}).get('mb_obs', 0) +
                                      obs_dict.get((zone, 2024), {}).get('mb_obs', 0))

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
        ax1.legend(loc='upper left', fontsize=8, ncol=2)
        ax1.grid(True, alpha=0.3)
        ax1.axhline(0, color='black', linewidth=0.5)

        ax2.set_xlabel('Date')
        ax2.set_ylabel('Cumulative Mass Balance (m w.e.)\n(normalized to 0 at Fall 2022)')
        ax2.set_title(f'{zone} Zone - Cumulative Mass Balance (from Fall 2022)')
        ax2.legend(loc='upper left', fontsize=8, ncol=2)
        ax2.grid(True, alpha=0.3)
        ax2.axhline(0, color='black', linewidth=0.5)

        plt.tight_layout()
        outfile = output_dir / f'monthly_mb_{zone}_top{n_best}_{sweep_name}.png'
        plt.savefig(outfile, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"  Saved: {outfile}")


def main():
    print("=" * 70)
    print("Regenerating Time Series Plots with Top 50 Runs")
    print("=" * 70)

    # Load existing analysis results (find the actual file)
    data_dir = ANALYSIS_DIR / "data"
    results_files = list(data_dir.glob("sweep_analysis_full_*.csv"))
    if not results_files:
        print("ERROR: No results file found!")
        return
    results_file = results_files[0]
    print(f"\nLoading results from: {results_file}")
    results_df = pd.read_csv(results_file)
    print(f"  Loaded {len(results_df):,} runs")

    # Load observations
    print("\nLoading observations...")
    obs_dict = load_observations()
    seasonal_dict = load_seasonal_observations()

    # Get sweep name
    sweep_name = SWEEP_DIR.name

    # Output to timeseries directory
    output_dir = ANALYSIS_DIR / "timeseries"

    # Generate plots
    print("\nGenerating time series plots...")
    plot_monthly_timeseries_top50(SWEEP_DIR, results_df, obs_dict, output_dir,
                                   sweep_name, n_best=50, seasonal_dict=seasonal_dict)

    print("\n" + "=" * 70)
    print("DONE")
    print("=" * 70)
    print(f"\nPlots saved to: {output_dir}")


if __name__ == "__main__":
    main()
