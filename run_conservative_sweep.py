#!/usr/bin/env python3
"""
Conservative 50k Parameter Sweep for Dixon Glacier
===================================================

Comprehensive sweep addressing the critical ddfsnow boundary issue while
maintaining broad parameter space coverage.

DESIGN RATIONALE:
- Main Focused Sweep (38,400 runs): High-resolution exploration of optimal regime
  with EXTENDED ddfsnow lower bound (0.0002 to 0.003)
- Exploratory Sweep (12,000 runs): Broad coverage of alternative parameter space
  to ensure no optimal regions are missed

CRITICAL FINDING from 147k combined analysis:
- Best parameters STILL at ddfsnow = 0.001 (lower boundary)
- 93% of top 250 runs from targeted sweep
- TRUE OPTIMUM likely at ddfsnow < 0.001
- MUST extend lower bound to 0.0002 (5x deeper than current)

Main Sweep Parameters (38,400 runs):
- tbias: +3.0 to +6.0°C (16 values, 0.2°C resolution)
- kp: 1.5 to 3.5 (12 values, ~0.18 resolution)
- ddfsnow: 0.0002 to 0.003 m°C⁻¹d⁻¹ (20 values, 0.00014 resolution)
- ddfsnow_iceratio: 0.12 to 0.40 (10 values, 0.031 resolution)

Exploratory Sweep Parameters (12,000 runs):
- tbias: -3.0 to +7.0°C (10 values, 1.0°C resolution)
- kp: 0.5 to 4.5 (10 values, 0.44 resolution)
- ddfsnow: 0.0001 to 0.008 m°C⁻¹d⁻¹ (12 values)
- ddfsnow_iceratio: 0.10 to 0.60 (10 values, 0.056 resolution)

TOTAL: 50,400 runs

Usage:
    python3 run_conservative_sweep.py
    python3 run_conservative_sweep.py --max_runs 100   # Test with first 100
    python3 run_conservative_sweep.py --start_run 1000 # Resume from run 1000
    python3 run_conservative_sweep.py --dry_run        # Show parameters only
    python3 run_conservative_sweep.py --exploratory_only  # Run only exploratory sweep
"""

import os
import sys
import subprocess
import time
import json
import shutil
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from itertools import product

# Configuration
BASE_DIR = Path("/home/kai/Documents/PYGEM")
PYGEM_SCRIPT = BASE_DIR / "PyGEM/pygem/bin/run/run_simulation.py"
OUTPUT_BASE = Path("/media/kai/Extreme SSD/Linux_Pygem/conservative_sweep")

# These will be set in main() with timestamp
OUTPUT_DIR = None
LOGS_DIR = None
RUNS_DIR = None

# Glacier and simulation settings
RGI_GLAC_NUMBER = "1.20947"
SIM_STARTYEAR = 2022
SIM_ENDYEAR = 2025  # Fall 2022 to Fall 2025 calibration period

# MAIN FOCUSED SWEEP (38,400 runs)
# High-resolution exploration of optimal parameter space
# CRITICAL: Extended ddfsnow lower bound to 0.0002
MAIN_PARAMETER_GRID = {
    'tbias': np.linspace(3.0, 6.0, 16),              # 16 values, 0.2°C resolution
    'kp': np.linspace(1.5, 3.5, 12),                 # 12 values, ~0.18 resolution
    'ddfsnow': np.linspace(0.0002, 0.003, 20),       # 20 values, EXTENDED to 0.0002
    'ddfsnow_iceratio': np.linspace(0.12, 0.40, 10)  # 10 values, 0.031 resolution
}

# EXPLORATORY SWEEP (12,000 runs)
# Broader parameter space to capture alternative optima
EXPLORATORY_PARAMETER_GRID = {
    'tbias': np.linspace(-3.0, 7.0, 10),             # 10 values, 1.0°C resolution
    'kp': np.linspace(0.5, 4.5, 10),                 # 10 values, 0.44 resolution
    'ddfsnow': np.logspace(-4, -2.1, 12),            # 12 values, 0.0001 to ~0.008, log-spaced
    'ddfsnow_iceratio': np.linspace(0.10, 0.60, 10)  # 10 values, 0.056 resolution
}


def create_parameter_combinations(use_exploratory=False):
    """Create all parameter combinations."""
    if use_exploratory:
        param_grid = EXPLORATORY_PARAMETER_GRID
        sweep_type = 'exploratory'
        print("\nGenerating EXPLORATORY sweep parameters (broad coverage)...")
    else:
        param_grid = MAIN_PARAMETER_GRID
        sweep_type = 'main'
        print("\nGenerating MAIN FOCUSED sweep parameters (high-resolution optimal regime)...")

    param_names = list(param_grid.keys())
    param_values = [param_grid[name] for name in param_names]

    combinations = []
    for i, combo in enumerate(product(*param_values)):
        params = dict(zip(param_names, combo))
        params['run_id'] = i
        params['ddfice'] = params['ddfsnow'] / params['ddfsnow_iceratio']
        params['sweep_type'] = sweep_type
        combinations.append(params)

    df = pd.DataFrame(combinations)
    print(f"  Generated {len(df):,} parameter combinations")
    print(f"  tbias range: {df['tbias'].min():.2f} to {df['tbias'].max():.2f}°C")
    print(f"  kp range: {df['kp'].min():.3f} to {df['kp'].max():.3f}")
    print(f"  ddfsnow range: {df['ddfsnow'].min():.6f} to {df['ddfsnow'].max():.6f}")
    print(f"  ddfsnow_iceratio range: {df['ddfsnow_iceratio'].min():.3f} to {df['ddfsnow_iceratio'].max():.3f}")

    return df


def create_combined_sweep():
    """Create combined parameter set with both main and exploratory sweeps."""
    print("="*70)
    print("CONSERVATIVE 50K SWEEP - DUAL REGIME DESIGN")
    print("="*70)

    # Generate main sweep
    main_df = create_parameter_combinations(use_exploratory=False)

    # Generate exploratory sweep
    exploratory_df = create_parameter_combinations(use_exploratory=True)

    # Offset exploratory run_ids to avoid conflicts
    exploratory_df['run_id'] = exploratory_df['run_id'] + 100000

    # Combine
    combined_df = pd.concat([main_df, exploratory_df], ignore_index=True)

    print("\n" + "="*70)
    print("COMBINED SWEEP SUMMARY")
    print("="*70)
    print(f"Main focused sweep:    {len(main_df):,} runs")
    print(f"Exploratory sweep:     {len(exploratory_df):,} runs")
    print(f"TOTAL:                 {len(combined_df):,} runs")
    print("\nParameter ranges (combined):")
    print(f"  tbias: {combined_df['tbias'].min():.2f} to {combined_df['tbias'].max():.2f}°C")
    print(f"  kp: {combined_df['kp'].min():.3f} to {combined_df['kp'].max():.3f}")
    print(f"  ddfsnow: {combined_df['ddfsnow'].min():.6f} to {combined_df['ddfsnow'].max():.6f}")
    print(f"  ddfsnow_iceratio: {combined_df['ddfsnow_iceratio'].min():.3f} to {combined_df['ddfsnow_iceratio'].max():.3f}")

    return combined_df


def move_output_files(run_id, run_dir):
    """Move output files from PyGEM output directory to run folder."""
    pygem_output_base = OUTPUT_DIR / "Output" / "simulations" / "01" / "ERA5"

    files_moved = []

    # Check stats directory
    stats_dir = pygem_output_base / "stats"
    if stats_dir.exists():
        for nc_file in stats_dir.glob(f"*_run{run_id:06d}*.nc"):
            dest = run_dir / nc_file.name
            shutil.move(str(nc_file), str(dest))
            files_moved.append(nc_file.name)

    # Check binned directory
    binned_dir = pygem_output_base / "binned"
    if binned_dir.exists():
        for nc_file in binned_dir.glob(f"*_run{run_id:06d}*.nc"):
            dest = run_dir / nc_file.name
            shutil.move(str(nc_file), str(dest))
            files_moved.append(nc_file.name)

    return files_moved


def write_run_metadata(run_dir, params, result, start_timestamp):
    """Write metadata file for a run."""
    metadata = {
        'run_id': int(params['run_id']),
        'sweep_type': params['sweep_type'],
        'glacier': RGI_GLAC_NUMBER,
        'simulation_period': f"{SIM_STARTYEAR}-{SIM_ENDYEAR}",
        'parameters': {
            'tbias': float(params['tbias']),
            'kp': float(params['kp']),
            'ddfsnow': float(params['ddfsnow']),
            'ddfsnow_iceratio': float(params['ddfsnow_iceratio']),
            'ddfice': float(params['ddfice']),
        },
        'execution': {
            'timestamp': start_timestamp,
            'runtime_seconds': result['runtime'],
            'success': result['success'],
            'returncode': result['returncode'],
        }
    }

    metadata_file = run_dir / "run_metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)


def run_simulation(params, run_dir, run_id):
    """Execute PyGEM simulation with given parameters."""
    # Create run directory
    run_dir.mkdir(parents=True, exist_ok=True)

    # Build command matching working targeted sweep format
    cmd = [
        sys.executable,
        str(PYGEM_SCRIPT),
        '-rgi_glac_number', RGI_GLAC_NUMBER,
        '-sim_startyear', str(SIM_STARTYEAR),
        '-sim_endyear', str(SIM_ENDYEAR),
        '-kp', str(params['kp']),
        '-tbias', str(params['tbias']),
        '-ddfsnow', str(params['ddfsnow']),
        '-ddfsnow_iceratio', str(params['ddfsnow_iceratio']),
        '-option_dynamics', 'MassRedistributionCurves',
        '-outputfn_sfix', f'_run{run_id:06d}',
        '-output_root', str(OUTPUT_DIR),
        '-export_binned_data',
    ]

    start_time = time.time()
    start_timestamp = datetime.now().isoformat()

    try:
        result = subprocess.run(
            cmd,
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        runtime = time.time() - start_time
        success = result.returncode == 0

        # Move output files to run directory
        files_moved = move_output_files(run_id, run_dir)

        # Save stdout/stderr only on failure to save space
        if not success:
            if result.stdout:
                (run_dir / "stdout.txt").write_text(result.stdout)
            if result.stderr:
                (run_dir / "stderr.txt").write_text(result.stderr)

        return {
            'success': success,
            'returncode': result.returncode,
            'runtime': runtime,
            'timestamp': start_timestamp
        }

    except subprocess.TimeoutExpired:
        runtime = time.time() - start_time
        return {
            'success': False,
            'returncode': -1,
            'runtime': runtime,
            'timestamp': start_timestamp,
            'error': 'timeout'
        }
    except Exception as e:
        runtime = time.time() - start_time
        return {
            'success': False,
            'returncode': -2,
            'runtime': runtime,
            'timestamp': start_timestamp,
            'error': str(e)
        }


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Conservative 50k parameter sweep for Dixon Glacier'
    )
    parser.add_argument('--dry_run', action='store_true',
                       help='Generate parameters without running simulations')
    parser.add_argument('--max_runs', type=int, default=None,
                       help='Maximum number of runs to execute (for testing)')
    parser.add_argument('--start_run', type=int, default=0,
                       help='Start from this run ID (for resuming)')
    parser.add_argument('--sweep_name', type=str, default=None,
                       help='Custom sweep name (default: conservative_TIMESTAMP)')
    parser.add_argument('--exploratory_only', action='store_true',
                       help='Run only the exploratory sweep (12k runs)')
    parser.add_argument('--main_only', action='store_true',
                       help='Run only the main focused sweep (38.4k runs)')
    args = parser.parse_args()

    # Set sweep name
    if args.sweep_name:
        sweep_name = args.sweep_name
    else:
        sweep_name = f"conservative_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Set global directories
    global OUTPUT_DIR, LOGS_DIR, RUNS_DIR
    OUTPUT_DIR = OUTPUT_BASE / sweep_name
    LOGS_DIR = OUTPUT_DIR / "logs"
    RUNS_DIR = OUTPUT_DIR / "runs"

    # Create directories
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)

    # Generate parameter combinations
    if args.exploratory_only:
        params_df = create_parameter_combinations(use_exploratory=True)
    elif args.main_only:
        params_df = create_parameter_combinations(use_exploratory=False)
    else:
        params_df = create_combined_sweep()

    # Save parameters
    params_file = OUTPUT_DIR / "parameters.csv"
    params_df.to_csv(params_file, index=False)
    print(f"\nSaved parameters to: {params_file}")

    # Save sweep configuration
    config = {
        'sweep_name': sweep_name,
        'total_runs': int(len(params_df)),
        'main_sweep_runs': int((params_df['sweep_type'] == 'main').sum()) if 'sweep_type' in params_df else int(len(params_df)),
        'exploratory_runs': int((params_df['sweep_type'] == 'exploratory').sum()) if 'sweep_type' in params_df else 0,
        'glacier': RGI_GLAC_NUMBER,
        'simulation_period': f"{SIM_STARTYEAR}-{SIM_ENDYEAR}",
        'parameter_ranges': {
            'tbias': [float(params_df['tbias'].min()), float(params_df['tbias'].max())],
            'kp': [float(params_df['kp'].min()), float(params_df['kp'].max())],
            'ddfsnow': [float(params_df['ddfsnow'].min()), float(params_df['ddfsnow'].max())],
            'ddfsnow_iceratio': [float(params_df['ddfsnow_iceratio'].min()), float(params_df['ddfsnow_iceratio'].max())]
        },
        'created': datetime.now().isoformat()
    }

    config_file = OUTPUT_DIR / "sweep_config.json"
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)

    if args.dry_run:
        print("\nDRY RUN - Parameters generated but simulations not executed")
        print(f"To run sweep: python3 {__file__}")
        return

    # Filter runs
    runs_to_execute = params_df[params_df['run_id'] >= args.start_run].copy()
    if args.max_runs:
        runs_to_execute = runs_to_execute.head(args.max_runs)

    print(f"\n{'='*70}")
    print(f"EXECUTING SWEEP")
    print(f"{'='*70}")
    print(f"Total runs: {len(params_df):,}")
    print(f"Runs to execute: {len(runs_to_execute):,}")
    print(f"Starting from run: {args.start_run}")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"{'='*70}\n")

    # Execute runs
    results = []
    start_time = time.time()

    for idx, row in runs_to_execute.iterrows():
        run_id = int(row['run_id'])
        run_dir = RUNS_DIR / f"run_{run_id:06d}"

        print(f"[{idx+1}/{len(runs_to_execute)}] Run {run_id:06d}: "
              f"tbias={row['tbias']:.2f}, kp={row['kp']:.3f}, "
              f"ddfsnow={row['ddfsnow']:.6f}, ratio={row['ddfsnow_iceratio']:.3f}",
              end=' ... ')

        result = run_simulation(row, run_dir, run_id)
        write_run_metadata(run_dir, row, result, result['timestamp'])

        status = "SUCCESS" if result['success'] else "FAILED"
        print(f"{status} ({result['runtime']:.1f}s)")

        results.append({
            'run_id': run_id,
            'success': result['success'],
            'runtime': result['runtime'],
            'returncode': result['returncode']
        })

        # Save checkpoint every 1000 runs
        if (idx + 1) % 1000 == 0:
            checkpoint_file = OUTPUT_DIR / f"results_checkpoint_{run_id:06d}.csv"
            pd.DataFrame(results).to_csv(checkpoint_file, index=False)
            elapsed = time.time() - start_time
            rate = (idx + 1) / elapsed
            remaining = (len(runs_to_execute) - idx - 1) / rate
            print(f"\n  Checkpoint: {idx+1} runs complete, {rate:.1f} runs/sec, "
                  f"~{remaining/60:.1f} min remaining\n")

    # Save final results
    results_df = pd.DataFrame(results)
    results_file = OUTPUT_DIR / "results.csv"
    results_df.to_csv(results_file, index=False)

    total_time = time.time() - start_time
    success_count = results_df['success'].sum()

    print(f"\n{'='*70}")
    print(f"SWEEP COMPLETE")
    print(f"{'='*70}")
    print(f"Total runs: {len(results_df)}")
    print(f"Successful: {success_count} ({success_count/len(results_df)*100:.1f}%)")
    print(f"Failed: {len(results_df) - success_count}")
    print(f"Total time: {total_time/3600:.2f} hours")
    print(f"Average time per run: {total_time/len(results_df):.1f} seconds")
    print(f"\nResults saved to: {OUTPUT_DIR}")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()
