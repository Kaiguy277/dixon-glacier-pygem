#!/usr/bin/env python3
"""
Analyze Parameter Sweep Results for Dixon Glacier
==================================================

Compares PyGEM modeled mass balance against observed stake measurements
at three elevation zones (ABL, ELA, ACC) for calibration.

Features:
- Equal zone weighting for RMSE (ABL, ELA, ACC each contribute 1/3)
- Seasonal metrics extraction for later filtering
- Checkpointing every 10,000 runs for large sweeps
- Organized output directory structure

Usage:
    python3 analyze_sweep_results.py
    python3 analyze_sweep_results.py --max_runs 100  # Test on subset
    python3 analyze_sweep_results.py --resume        # Resume from checkpoint
"""

import os
import json
import numpy as np
import pandas as pd
import xarray as xr
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt
from tqdm import tqdm

# Configuration
SWEEP_DIR = Path("/media/kai/Extreme SSD/Linux_Pygem/expanded_sweep/calibration_expanded_20260122_220448")
OBS_FILE = Path("/home/kai/Documents/PYGEM/inputs/stake_observations_dixon.csv")
GRAPHS_BASE_DIR = Path("/home/kai/Documents/PYGEM/graphs")

# Analysis settings
CHECKPOINT_INTERVAL = 10000  # Save progress every N runs
TOP_N_EXPORT = 1000  # Number of top parameter sets to export

# Observation elevations and their corresponding bin indices
# These were determined from inspecting the binned.nc files
OBS_ELEVATIONS = {
    'ABL': {'elevation': 804, 'bin_idx': 87},
    'ELA': {'elevation': 1078, 'bin_idx': 46},
    'ACC': {'elevation': 1293, 'bin_idx': 15},
}

# Monthly indices for water year calculations
# Model output: Jan 2022 = index 0, so Oct 2022 = index 9
WATER_YEAR_INDICES = {
    2023: (9, 21),   # Oct 2022 (idx 9) to Sep 2023 (idx 20), sum indices 9-20
    2024: (21, 33),  # Oct 2023 (idx 21) to Sep 2024 (idx 32), sum indices 21-32
    2025: (33, 45),  # Oct 2024 (idx 33) to Sep 2025 (idx 44), sum indices 33-44
}

# Seasonal indices within each water year
# Winter: Oct-Apr (7 months), Summer: May-Sep (5 months)
SEASONAL_INDICES = {
    2023: {'winter': (9, 16), 'summer': (16, 21)},   # WY2023
    2024: {'winter': (21, 28), 'summer': (28, 33)},  # WY2024
    2025: {'winter': (33, 40), 'summer': (40, 45)},  # WY2025
}

# Zone-specific years to use for calibration
# ABL: no 2025 annual observation available
# ELA, ACC: have 2025 annual observations
ZONE_YEARS = {
    'ABL': [2023, 2024],
    'ELA': [2023, 2024, 2025],
    'ACC': [2023, 2024, 2025],
}


def load_observations():
    """Load and filter observed mass balance data."""
    obs_df = pd.read_csv(OBS_FILE)

    # Filter to annual observations only for zones we care about
    annual_obs = obs_df[
        (obs_df['period_type'] == 'annual') &
        (obs_df['zone'].isin(['ABL', 'ELA', 'ACC']))
    ].copy()

    # Create observation lookup: (zone, year) -> mb_obs_mwe
    obs_dict = {}
    for _, row in annual_obs.iterrows():
        key = (row['zone'], row['year'])
        obs_dict[key] = {
            'mb_obs': row['mb_obs_mwe'],
            'uncertainty': row['mb_obs_uncertainty_mwe'],
        }

    return obs_dict, annual_obs


def load_seasonal_observations():
    """Load winter and summer seasonal mass balance observations."""
    obs_df = pd.read_csv(OBS_FILE)

    seasonal_obs = obs_df[
        (obs_df['period_type'].isin(['winter', 'summer'])) &
        (obs_df['zone'].isin(['ABL', 'ELA', 'ACC']))
    ].copy()

    # Create lookup: (zone, year, period_type) -> {mb_obs, uncertainty, date_start, date_end}
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


def load_geodetic_observation():
    """Load glacier-wide geodetic observation."""
    obs_df = pd.read_csv(OBS_FILE)
    geodetic = obs_df[obs_df['site_id'] == 'DIXON_GEODETIC'].iloc[0]
    return geodetic['mb_obs_mwe'], geodetic['mb_obs_uncertainty_mwe']


def find_binned_file(run_dir):
    """Find the binned NetCDF file in a run directory."""
    binned_files = list(run_dir.glob("*binned.nc"))
    if binned_files:
        return binned_files[0]
    return None


def extract_modeled_mb_monthly(binned_file, bin_indices):
    """
    Extract modeled mass balance from monthly data, summed to water years.

    Parameters
    ----------
    binned_file : Path
        Path to the binned NetCDF file
    bin_indices : dict
        Zone name -> bin index mapping

    Returns
    -------
    dict : {(zone, year): modeled_mb_mwe}
    """
    ds = xr.open_dataset(binned_file)

    # Get monthly mass balance: shape (1, nbins, 48 months)
    monthly_mb = ds['bin_massbalclim'].values[0]  # Remove glacier dimension

    modeled = {}
    for zone, info in OBS_ELEVATIONS.items():
        bin_idx = info['bin_idx']
        zone_monthly = monthly_mb[bin_idx, :]  # 48 months for this bin

        # Only extract years relevant for this zone
        years_for_zone = ZONE_YEARS.get(zone, [2023, 2024])
        for year in years_for_zone:
            if year in WATER_YEAR_INDICES:
                start_idx, end_idx = WATER_YEAR_INDICES[year]
                # Sum monthly values for water year (Oct-Sep)
                annual_mb = zone_monthly[start_idx:end_idx].sum()
                modeled[(zone, year)] = annual_mb

    ds.close()
    return modeled


def extract_seasonal_mb(binned_file, seasonal_obs_dict):
    """
    Extract modeled seasonal (winter/summer) mass balance.

    Parameters
    ----------
    binned_file : Path
        Path to the binned NetCDF file
    seasonal_obs_dict : dict
        Seasonal observations for comparison

    Returns
    -------
    dict : Contains modeled seasonal values and biases
    """
    ds = xr.open_dataset(binned_file)
    monthly_mb = ds['bin_massbalclim'].values[0]  # Remove glacier dimension

    result = {}
    winter_biases = []
    summer_biases = []

    for zone, info in OBS_ELEVATIONS.items():
        bin_idx = info['bin_idx']
        zone_monthly = monthly_mb[bin_idx, :]

        for year in [2023, 2024, 2025]:
            if year not in SEASONAL_INDICES:
                continue

            # Winter
            winter_start, winter_end = SEASONAL_INDICES[year]['winter']
            mod_winter = zone_monthly[winter_start:winter_end].sum()
            result[f'mod_winter_{zone}_{year}'] = mod_winter

            winter_key = (zone, year, 'winter')
            if winter_key in seasonal_obs_dict:
                obs_winter = seasonal_obs_dict[winter_key]['mb_obs']
                bias = mod_winter - obs_winter
                result[f'bias_winter_{zone}_{year}'] = bias
                winter_biases.append(bias)

            # Summer
            summer_start, summer_end = SEASONAL_INDICES[year]['summer']
            mod_summer = zone_monthly[summer_start:summer_end].sum()
            result[f'mod_summer_{zone}_{year}'] = mod_summer

            summer_key = (zone, year, 'summer')
            if summer_key in seasonal_obs_dict:
                obs_summer = seasonal_obs_dict[summer_key]['mb_obs']
                bias = mod_summer - obs_summer
                result[f'bias_summer_{zone}_{year}'] = bias
                summer_biases.append(bias)

    # Aggregate seasonal biases
    if winter_biases:
        result['bias_winter_mean'] = np.mean(winter_biases)
    if summer_biases:
        result['bias_summer_mean'] = np.mean(summer_biases)

    ds.close()
    return result


def extract_glacier_wide_mb(run_dir):
    """Extract glacier-wide mass balance for comparison with geodetic."""
    all_files = list(run_dir.glob("*all.nc"))
    if not all_files:
        return None

    ds = xr.open_dataset(all_files[0])

    # Get annual mass values
    if 'glac_mass_annual' in ds:
        mass_annual = ds['glac_mass_annual'].values[0]  # kg
        area_annual = ds['glac_area_annual'].values[0]  # m²

        # Mass change from 2022 to 2023 (indices 0 to 1)
        # Convert to m w.e.: (kg / m²) / 1000 kg/m³
        if len(mass_annual) >= 2 and len(area_annual) >= 2:
            mass_change = mass_annual[1] - mass_annual[0]  # kg
            avg_area = (area_annual[0] + area_annual[1]) / 2  # m²
            mb_mwe = mass_change / avg_area / 1000  # m w.e.
            ds.close()
            return mb_mwe

    ds.close()
    return None


def compute_rmse_zone_weighted(obs_dict, modeled_dict):
    """
    Compute RMSE with equal weighting per zone (1/3 each for ABL, ELA, ACC).

    This ensures each zone contributes equally regardless of how many
    observation years are available for that zone.
    """
    zone_rmses = {}

    for zone in ['ABL', 'ELA', 'ACC']:
        errors = []
        for key, obs_info in obs_dict.items():
            if key[0] == zone and key in modeled_dict:
                obs_val = obs_info['mb_obs']
                mod_val = modeled_dict[key]
                errors.append((obs_val - mod_val) ** 2)

        if errors:
            zone_rmses[zone] = np.sqrt(np.mean(errors))

    # Equal weight: average of zone RMSEs
    if zone_rmses:
        return np.mean(list(zone_rmses.values()))
    return np.inf


def compute_per_zone_metrics(obs_dict, modeled_dict):
    """Compute RMSE and bias for each zone."""
    zones = ['ABL', 'ELA', 'ACC']
    metrics = {}

    for zone in zones:
        zone_errors = []
        zone_biases = []
        for key, obs_info in obs_dict.items():
            if key[0] == zone and key in modeled_dict:
                obs_val = obs_info['mb_obs']
                mod_val = modeled_dict[key]
                zone_errors.append((obs_val - mod_val) ** 2)
                zone_biases.append(mod_val - obs_val)

        if zone_errors:
            metrics[zone] = {
                'rmse': np.sqrt(np.mean(zone_errors)),
                'bias': np.mean(zone_biases),
                'n_obs': len(zone_errors),
            }

    return metrics


def analyze_all_runs(sweep_dir, obs_dict, seasonal_dict, output_dir, max_runs=None, resume=False):
    """
    Analyze all runs in the sweep directory.

    Returns DataFrame with parameters and error metrics for each run.
    Includes checkpointing for large sweeps.
    """
    # Load parameters
    params_df = pd.read_csv(sweep_dir / "parameters.csv")

    if max_runs:
        params_df = params_df.head(max_runs)

    total_runs = len(params_df)
    runs_dir = sweep_dir / "runs"

    # Check for existing checkpoint
    checkpoint_file = output_dir / "checkpoint_results.csv"
    start_idx = 0
    results = []

    if resume and checkpoint_file.exists():
        print(f"  Resuming from checkpoint: {checkpoint_file}")
        checkpoint_df = pd.read_csv(checkpoint_file)
        results = checkpoint_df.to_dict('records')
        start_idx = len(results)
        print(f"  Loaded {start_idx:,} previously analyzed runs")

    # Analyze runs
    for idx in tqdm(range(start_idx, total_runs), initial=start_idx, total=total_runs, desc="Analyzing runs"):
        row = params_df.iloc[idx]
        run_id = int(row['run_id'])
        run_dir = runs_dir / f"run_{run_id:06d}"  # 6-digit padding for expanded sweep

        binned_file = find_binned_file(run_dir)
        if binned_file is None:
            continue

        try:
            # Extract modeled MB at observation locations
            modeled = extract_modeled_mb_monthly(binned_file, OBS_ELEVATIONS)

            # Compute metrics with zone weighting
            combined_rmse = compute_rmse_zone_weighted(obs_dict, modeled)
            zone_metrics = compute_per_zone_metrics(obs_dict, modeled)

            # Extract seasonal metrics
            seasonal_metrics = extract_seasonal_mb(binned_file, seasonal_dict)

            # Extract glacier-wide for geodetic comparison
            glacier_wide_mb = extract_glacier_wide_mb(run_dir)

            result = {
                'run_id': run_id,
                'tbias': row['tbias'],
                'kp': row['kp'],
                'ddfsnow': row['ddfsnow'],
                'ddfsnow_iceratio': row['ddfsnow_iceratio'],
                'ddfice': row['ddfice'],
                'combined_rmse': combined_rmse,
                'glacier_wide_mb': glacier_wide_mb,
            }

            # Add modeled values for each zone-year
            for key, val in modeled.items():
                zone, year = key
                result[f'mod_{zone}_{year}'] = val

            # Add per-zone metrics
            for zone, metrics in zone_metrics.items():
                result[f'rmse_{zone}'] = metrics['rmse']
                result[f'bias_{zone}'] = metrics['bias']

            # Add seasonal metrics
            result.update(seasonal_metrics)

            results.append(result)

            # Checkpoint
            if (idx + 1) % CHECKPOINT_INTERVAL == 0:
                checkpoint_df = pd.DataFrame(results)
                checkpoint_df.to_csv(checkpoint_file, index=False)
                print(f"\n  [Checkpoint: {idx + 1:,} runs analyzed, saved to {checkpoint_file}]")

        except Exception as e:
            print(f"\nError processing run {run_id}: {e}")
            continue

    return pd.DataFrame(results)


def print_best_results(results_df, obs_dict, n_best=20):
    """Print summary of best-fitting parameter combinations."""
    # Sort by combined RMSE
    sorted_df = results_df.sort_values('combined_rmse').head(n_best)

    print("\n" + "=" * 80)
    print(f"TOP {n_best} BEST-FITTING PARAMETER COMBINATIONS")
    print("=" * 80)

    # Load geodetic for comparison
    geodetic_mb, geodetic_unc = load_geodetic_observation()
    print(f"\nGeodetic observation (2022-2023): {geodetic_mb:.3f} +/- {geodetic_unc:.2f} m w.e.")

    print("\nObserved annual mass balance (m w.e.):")
    for key, info in obs_dict.items():
        zone, year = key
        print(f"  {zone} {year}: {info['mb_obs']:+.2f} +/- {info['uncertainty']:.2f}")

    print("\n" + "-" * 120)
    print(f"{'Rank':<5} {'RMSE':<7} {'tbias':<8} {'kp':<6} {'ddfsnow':<9} {'ratio':<6} | "
          f"{'ABL_23':<8} {'ABL_24':<8} {'ELA_23':<8} {'ELA_24':<8} {'ELA_25':<8} {'ACC_23':<8} {'ACC_24':<8} {'ACC_25':<8}")
    print("-" * 120)

    for rank, (_, row) in enumerate(sorted_df.iterrows(), 1):
        print(f"{rank:<5} {row['combined_rmse']:<7.3f} {row['tbias']:+6.1f}  {row['kp']:<6.2f} "
              f"{row['ddfsnow']:<9.5f} {row['ddfsnow_iceratio']:<6.2f} | "
              f"{row.get('mod_ABL_2023', np.nan):+7.2f}  {row.get('mod_ABL_2024', np.nan):+7.2f}  "
              f"{row.get('mod_ELA_2023', np.nan):+7.2f}  {row.get('mod_ELA_2024', np.nan):+7.2f}  "
              f"{row.get('mod_ELA_2025', np.nan):+7.2f}  "
              f"{row.get('mod_ACC_2023', np.nan):+7.2f}  {row.get('mod_ACC_2024', np.nan):+7.2f}  "
              f"{row.get('mod_ACC_2025', np.nan):+7.2f}")

    print("\n" + "-" * 80)
    print("\nBest fit parameters:")
    best = sorted_df.iloc[0]
    print(f"  Temperature bias (tbias):    {best['tbias']:+.2f} C")
    print(f"  Precipitation factor (kp):   {best['kp']:.3f}")
    print(f"  DDF snow:                    {best['ddfsnow']:.6f} m/C/d")
    print(f"  DDF snow/ice ratio:          {best['ddfsnow_iceratio']:.3f}")
    print(f"  DDF ice (computed):          {best['ddfice']:.6f} m/C/d")
    print(f"\n  Combined RMSE (zone-weighted): {best['combined_rmse']:.3f} m w.e.")
    if best['glacier_wide_mb'] is not None and not np.isnan(best['glacier_wide_mb']):
        print(f"  Glacier-wide MB (2022-23):   {best['glacier_wide_mb']:.3f} m w.e. (obs: {geodetic_mb:.3f})")


def setup_output_directories(sweep_dir):
    """Create organized output directory structure."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    sweep_name = sweep_dir.name

    output_dir = GRAPHS_BASE_DIR / f"analysis_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    subdirs = {
        'data': output_dir / "data",
        'timeseries': output_dir / "timeseries",
        'heatmaps': output_dir / "heatmaps",
        'distributions': output_dir / "distributions",
        'scatter': output_dir / "scatter",
    }

    for subdir in subdirs.values():
        subdir.mkdir(parents=True, exist_ok=True)

    return output_dir, subdirs, sweep_name


def plot_monthly_timeseries(sweep_dir, results_df, obs_dict, output_dir, sweep_name, n_best=50, seasonal_dict=None):
    """
    Plot monthly mass balance time series for each zone with observations overlaid.

    Creates one plot per zone (ABL, ELA, ACC) showing:
    - Monthly MB from top N best-fitting runs (thin lines)
    - Ensemble mean (bold line)
    - Cumulative MB over time (normalized to zero at Fall 2022)
    - Observed annual values as reference points
    - Observed seasonal (winter/summer) values as intermediate points
    """
    runs_dir = sweep_dir / "runs"

    # Load seasonal observations if not provided
    if seasonal_dict is None:
        seasonal_dict = load_seasonal_observations()

    # Get top N best runs
    sorted_df = results_df.sort_values('combined_rmse').head(n_best)
    best_run_ids = sorted_df['run_id'].tolist()

    # Create time axis (48 months: Jan 2022 - Dec 2025)
    full_time_labels = pd.date_range('2022-01', periods=48, freq='ME')
    FALL_2022_IDX = 9
    time_labels = full_time_labels[FALL_2022_IDX:]
    n_months = len(time_labels)

    # Water year boundaries
    wy_boundaries = [pd.Timestamp('2023-10-01'), pd.Timestamp('2024-10-01')]
    spring_boundaries = [pd.Timestamp('2023-05-01'), pd.Timestamp('2024-05-01'), pd.Timestamp('2025-05-01')]

    run_colors = plt.cm.tab10(np.linspace(0, 1, n_best))
    zones = ['ABL', 'ELA', 'ACC']
    zone_colors = {'ABL': 'red', 'ELA': 'orange', 'ACC': 'blue'}

    for zone in zones:
        bin_idx = OBS_ELEVATIONS[zone]['bin_idx']
        elev = OBS_ELEVATIONS[zone]['elevation']
        years_for_zone = ZONE_YEARS.get(zone, [2023, 2024])

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)
        all_monthly = []

        # Load and plot each best run
        for i, run_id in enumerate(best_run_ids):
            run_dir = runs_dir / f"run_{int(run_id):06d}"  # 6-digit padding
            binned_file = find_binned_file(run_dir)
            if binned_file is None:
                continue

            ds = xr.open_dataset(binned_file)
            full_monthly_mb = ds['bin_massbalclim'].values[0, bin_idx, :]
            ds.close()

            monthly_mb = full_monthly_mb[FALL_2022_IDX:]
            all_monthly.append(monthly_mb)

            ax1.plot(time_labels, monthly_mb, color=run_colors[i], alpha=0.5,
                    linewidth=1, label=f'Run {int(run_id)}')
            cumulative = np.cumsum(monthly_mb)
            ax2.plot(time_labels, cumulative, color=run_colors[i], alpha=0.5,
                    linewidth=1, label=f'Run {int(run_id)}')

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
        outfile = output_dir / f'monthly_mb_{zone}_{sweep_name}.png'
        plt.savefig(outfile, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"  Saved: {outfile}")


def plot_results(results_df, obs_dict, output_dirs, sweep_name):
    """Generate comparison plots."""
    sorted_df = results_df.sort_values('combined_rmse')
    best_runs = sorted_df.head(10)

    # Plot 1: Observed vs Modeled scatter for best runs
    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    zones = ['ABL', 'ELA', 'ACC']
    colors = ['red', 'orange', 'blue']

    for ax, zone, color in zip(axes, zones, colors):
        obs_vals = []
        mod_vals = []
        years_for_zone = ZONE_YEARS.get(zone, [2023, 2024])
        for year in years_for_zone:
            key = (zone, year)
            if key in obs_dict:
                obs_vals.append(obs_dict[key]['mb_obs'])
                mod_col = f'mod_{zone}_{year}'
                if mod_col in best_runs.columns:
                    mod_vals.append(best_runs[mod_col].mean())

        if obs_vals and mod_vals:
            ax.scatter(obs_vals, mod_vals, c=color, s=100, alpha=0.7, label=zone)
            lims = [min(min(obs_vals), min(mod_vals)) - 0.5,
                    max(max(obs_vals), max(mod_vals)) + 0.5]
            ax.plot(lims, lims, 'k--', alpha=0.5, label='1:1')
            ax.set_xlim(lims)
            ax.set_ylim(lims)

        ax.set_xlabel('Observed MB (m w.e.)')
        ax.set_ylabel('Modeled MB (m w.e.)')
        ax.set_title(f'{zone} Zone ({OBS_ELEVATIONS[zone]["elevation"]}m)')
        ax.legend()
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    outfile = output_dirs['scatter'] / f'obs_vs_mod_{sweep_name}.png'
    plt.savefig(outfile, dpi=150)
    plt.close()
    print(f"  Saved: {outfile}")

    # Plot 2: RMSE heatmap for tbias vs kp
    fig, ax = plt.subplots(figsize=(10, 8))
    pivot = results_df.pivot_table(values='combined_rmse',
                                    index='tbias',
                                    columns='kp',
                                    aggfunc='min')
    im = ax.imshow(pivot.values, aspect='auto', cmap='viridis_r',
                   extent=[pivot.columns.min(), pivot.columns.max(),
                          pivot.index.min(), pivot.index.max()],
                   origin='lower')
    plt.colorbar(im, label='Minimum RMSE (m w.e.)')
    ax.set_xlabel('Precipitation factor (kp)')
    ax.set_ylabel('Temperature bias (C)')
    ax.set_title('Parameter Sensitivity: tbias vs kp (zone-weighted RMSE)')

    best = sorted_df.iloc[0]
    ax.scatter(best['kp'], best['tbias'], c='red', s=200, marker='*',
               edgecolors='white', linewidths=2, label='Best fit')
    ax.legend()

    plt.tight_layout()
    outfile = output_dirs['heatmaps'] / f'rmse_tbias_kp_{sweep_name}.png'
    plt.savefig(outfile, dpi=150)
    plt.close()
    print(f"  Saved: {outfile}")

    # Plot 3: RMSE distribution
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(results_df['combined_rmse'], bins=50, edgecolor='black', alpha=0.7)
    ax.axvline(sorted_df.iloc[0]['combined_rmse'], color='red', linestyle='--',
               linewidth=2, label=f'Best: {sorted_df.iloc[0]["combined_rmse"]:.3f}')
    ax.set_xlabel('Combined RMSE (m w.e.) - Zone Weighted')
    ax.set_ylabel('Number of runs')
    ax.set_title('RMSE Distribution Across Parameter Space')
    ax.legend()
    plt.tight_layout()
    outfile = output_dirs['distributions'] / f'rmse_histogram_{sweep_name}.png'
    plt.savefig(outfile, dpi=150)
    plt.close()
    print(f"  Saved: {outfile}")


def save_analysis_metadata(output_dir, sweep_dir, obs_dict, results_df, sweep_name):
    """Save metadata about the analysis for reproducibility."""
    metadata = {
        'analysis_timestamp': datetime.now().isoformat(),
        'sweep_directory': str(sweep_dir),
        'sweep_name': sweep_name,
        'total_runs_analyzed': len(results_df),
        'observations_file': str(OBS_FILE),
        'observations_used': {
            f'{zone}_{year}': info['mb_obs']
            for (zone, year), info in obs_dict.items()
        },
        'ranking_method': 'zone_weighted_rmse',
        'ranking_description': 'Equal weight per zone (ABL, ELA, ACC each 1/3)',
        'top_n_exported': TOP_N_EXPORT,
        'best_rmse': float(results_df['combined_rmse'].min()),
        'best_parameters': results_df.sort_values('combined_rmse').iloc[0][
            ['tbias', 'kp', 'ddfsnow', 'ddfsnow_iceratio', 'ddfice']
        ].to_dict(),
    }

    metadata_file = output_dir / 'data' / 'analysis_metadata.json'
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"  Saved: {metadata_file}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Analyze parameter sweep results')
    parser.add_argument('--max_runs', type=int, default=None,
                       help='Maximum runs to analyze (for testing)')
    parser.add_argument('--no_plots', action='store_true',
                       help='Skip plot generation')
    parser.add_argument('--resume', action='store_true',
                       help='Resume from checkpoint if available')
    args = parser.parse_args()

    print("=" * 70)
    print("Dixon Glacier Parameter Sweep Analysis")
    print("=" * 70)
    print(f"\nSweep directory: {SWEEP_DIR}")
    print(f"Observations file: {OBS_FILE}")

    # Setup output directories
    output_dir, output_dirs, sweep_name = setup_output_directories(SWEEP_DIR)
    print(f"Output directory: {output_dir}")

    # Load observations
    print("\nLoading observations...")
    obs_dict, obs_df = load_observations()
    seasonal_dict = load_seasonal_observations()
    print(f"  Found {len(obs_dict)} annual observations across zones")
    print(f"  Found {len(seasonal_dict)} seasonal observations")

    # Analyze runs
    print("\nAnalyzing parameter sweep runs...")
    print(f"  Using zone-weighted RMSE (equal weight per zone)")
    print(f"  Checkpointing every {CHECKPOINT_INTERVAL:,} runs")
    results_df = analyze_all_runs(SWEEP_DIR, obs_dict, seasonal_dict, output_dir,
                                   max_runs=args.max_runs, resume=args.resume)
    print(f"\n  Analyzed {len(results_df):,} runs successfully")

    # Save full results
    results_file = output_dirs['data'] / f"sweep_analysis_full_{len(results_df)}runs.csv"
    results_df.to_csv(results_file, index=False)
    print(f"\nFull results saved to: {results_file}")

    # Print best results
    print_best_results(results_df, obs_dict)

    # Save top N parameters for historical runs
    best_df = results_df.sort_values('combined_rmse').head(TOP_N_EXPORT)
    best_file = output_dirs['data'] / f"top_{TOP_N_EXPORT}_params_for_historical.csv"
    best_df.to_csv(best_file, index=False)
    print(f"\nTop {TOP_N_EXPORT} parameter sets saved to: {best_file}")

    # Save metadata
    save_analysis_metadata(output_dir, SWEEP_DIR, obs_dict, results_df, sweep_name)

    # Clean up checkpoint file if analysis completed
    checkpoint_file = output_dir / "checkpoint_results.csv"
    if checkpoint_file.exists():
        checkpoint_file.unlink()
        print("  Cleaned up checkpoint file")

    # Generate plots
    if not args.no_plots:
        print("\nGenerating plots...")
        plot_results(results_df, obs_dict, output_dirs, sweep_name)
        print("\nGenerating monthly time series plots...")
        plot_monthly_timeseries(SWEEP_DIR, results_df, obs_dict, output_dirs['timeseries'],
                               sweep_name, n_best=5, seasonal_dict=seasonal_dict)

    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)
    print(f"\nOutput directory: {output_dir}")
    print(f"Top {TOP_N_EXPORT} parameters ready for historical runs: {best_file}")


if __name__ == "__main__":
    main()
