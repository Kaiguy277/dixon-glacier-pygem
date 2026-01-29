#!/usr/bin/env python3
"""
Full Parameter Sweep for Dixon Glacier (256 runs)
==================================================

Runs a 4x4x4x4 = 256 combination parameter sweep using the corrected
glacier geometry with true hypsometry (42.16 km², 57 elevation bands at 20m).

Parameter ranges:
- tbias: -10.0 to +5.0 °C (4 values)
- kp: 0.5 to 8.0 (4 values)
- ddfsnow: 0.001 to 0.012 m°C⁻¹d⁻¹ (4 values)
- ddfsnow_iceratio: 0.2 to 1.0 (4 values)

Usage:
    python3 run_full_sweep.py
    python3 run_full_sweep.py --max_runs 50   # Test with first 50 runs
    python3 run_full_sweep.py --start_run 100 # Resume from run 100
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
OUTPUT_BASE = Path("/media/kai/Extreme SSD/Linux_Pygem/full_sweep")

# These will be set in main() with timestamp
OUTPUT_DIR = None
LOGS_DIR = None
RUNS_DIR = None

# Glacier and simulation settings
RGI_GLAC_NUMBER = "1.20947"
SIM_STARTYEAR = 2022
SIM_ENDYEAR = 2025  # Fall 2022 to Fall 2025 calibration period (3 years)

# Full parameter grid (4 values each = 256 combinations)
PARAMETER_GRID = {
    'tbias': np.linspace(-10.0, 5.0, 4),         # [-10.0, -5.0, 0.0, 5.0]
    'kp': np.linspace(0.5, 8.0, 4),              # [0.5, 3.0, 5.5, 8.0]
    'ddfsnow': np.linspace(0.001, 0.012, 4),     # [0.001, 0.0047, 0.0083, 0.012]
    'ddfsnow_iceratio': np.linspace(0.2, 1.0, 4) # [0.2, 0.47, 0.73, 1.0]
}


def create_parameter_combinations():
    """Create all parameter combinations."""
    param_names = list(PARAMETER_GRID.keys())
    param_values = [PARAMETER_GRID[name] for name in param_names]

    combinations = []
    for i, combo in enumerate(product(*param_values)):
        params = dict(zip(param_names, combo))
        params['run_id'] = i
        params['ddfice'] = params['ddfsnow'] / params['ddfsnow_iceratio']
        combinations.append(params)

    return pd.DataFrame(combinations)


def write_run_metadata(run_dir, params, result, start_timestamp):
    """Write metadata file for a run."""
    metadata = {
        'run_id': int(params['run_id']),
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

    # Write JSON metadata
    with open(run_dir / 'metadata.json', 'w') as f:
        json.dump(metadata, f, indent=2)

    # Write human-readable text file
    with open(run_dir / 'run_info.txt', 'w') as f:
        f.write(f"Dixon Glacier Full Sweep - Run {int(params['run_id']):04d}\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Glacier: RGI60-{RGI_GLAC_NUMBER} (Dixon Glacier)\n")
        f.write(f"Area: 42.16 km² (true DEM hypsometry)\n")
        f.write(f"Elevation bands: 57 (20m spacing)\n")
        f.write(f"Simulation Period: Fall {SIM_STARTYEAR} - Fall {SIM_ENDYEAR}\n\n")
        f.write("Parameters:\n")
        f.write(f"  Temperature Bias (tbias):     {params['tbias']:+.2f} °C\n")
        f.write(f"  Precipitation Factor (kp):    {params['kp']:.3f}\n")
        f.write(f"  DDF Snow:                     {params['ddfsnow']:.6f} m°C⁻¹d⁻¹\n")
        f.write(f"  DDF Snow/Ice Ratio:           {params['ddfsnow_iceratio']:.3f}\n")
        f.write(f"  DDF Ice (computed):           {params['ddfice']:.6f} m°C⁻¹d⁻¹\n\n")
        f.write("Execution:\n")
        f.write(f"  Timestamp: {start_timestamp}\n")
        f.write(f"  Runtime:   {result['runtime']:.1f} seconds\n")
        f.write(f"  Status:    {'SUCCESS' if result['success'] else 'FAILED'}\n")


def move_output_files(run_id, run_dir):
    """Move output files from PyGEM output directory to run folder."""
    pygem_output_base = OUTPUT_DIR / "Output" / "simulations" / "01" / "ERA5"

    files_moved = []

    # Check stats directory
    stats_dir = pygem_output_base / "stats"
    if stats_dir.exists():
        for nc_file in stats_dir.glob(f"*_run{run_id:04d}*.nc"):
            dest = run_dir / nc_file.name
            shutil.move(str(nc_file), str(dest))
            files_moved.append(nc_file.name)

    # Check binned directory
    binned_dir = pygem_output_base / "binned"
    if binned_dir.exists():
        for nc_file in binned_dir.glob(f"*_run{run_id:04d}*.nc"):
            dest = run_dir / nc_file.name
            shutil.move(str(nc_file), str(dest))
            files_moved.append(nc_file.name)

    return files_moved


def run_single_simulation(params, log_file=None):
    """Execute a single PyGEM simulation with given parameters."""
    run_id = int(params['run_id'])
    start_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Create run directory
    run_dir = RUNS_DIR / f"run_{run_id:04d}"
    run_dir.mkdir(parents=True, exist_ok=True)

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
        '-outputfn_sfix', f'_run{run_id:04d}',
        '-output_root', str(OUTPUT_DIR),
        '-export_binned_data',
    ]

    env = os.environ.copy()
    env['MPLBACKEND'] = 'Agg'

    start_time = time.time()

    try:
        result = subprocess.run(
            cmd,
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            timeout=600,
            env=env
        )

        runtime = time.time() - start_time
        success = result.returncode == 0

        result_dict = {
            'run_id': run_id,
            'success': success,
            'runtime': runtime,
            'returncode': result.returncode
        }

        # Move output files to run directory
        files_moved = move_output_files(run_id, run_dir)

        # Write metadata
        write_run_metadata(run_dir, params, result_dict, start_timestamp)

        # Save stdout/stderr
        if result.stdout:
            with open(run_dir / 'stdout.txt', 'w') as f:
                f.write(result.stdout)
        if result.stderr:
            with open(run_dir / 'stderr.txt', 'w') as f:
                f.write(result.stderr)

        if log_file:
            with open(log_file, 'a') as f:
                status = "OK" if success else "FAIL"
                f.write(f"Run {run_id:04d}: {status} in {runtime:.1f}s | "
                       f"kp={params['kp']:.2f} tbias={params['tbias']:+.1f} "
                       f"ddfsnow={params['ddfsnow']:.4f} iceratio={params['ddfsnow_iceratio']:.2f} | "
                       f"files: {len(files_moved)}\n")

        return result_dict

    except subprocess.TimeoutExpired:
        result_dict = {'run_id': run_id, 'success': False, 'runtime': 600, 'returncode': -1}
        write_run_metadata(run_dir, params, result_dict, start_timestamp)
        return result_dict
    except Exception as e:
        result_dict = {'run_id': run_id, 'success': False, 'runtime': 0, 'returncode': -1}
        write_run_metadata(run_dir, params, result_dict, start_timestamp)
        return result_dict


def main():
    global OUTPUT_DIR, LOGS_DIR, RUNS_DIR

    import argparse
    parser = argparse.ArgumentParser(description='Run full parameter sweep (256 runs)')
    parser.add_argument('--max_runs', type=int, default=None, help='Maximum runs to execute')
    parser.add_argument('--start_run', type=int, default=0, help='Starting run ID')
    parser.add_argument('--dry_run', action='store_true', help='Print parameters without running')
    parser.add_argument('--sweep_name', type=str, default=None, help='Custom name for sweep folder')
    args = parser.parse_args()

    # Create timestamped output directory
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    if args.sweep_name:
        sweep_folder = f"{args.sweep_name}_{timestamp}"
    else:
        sweep_folder = f"sweep_{timestamp}"

    OUTPUT_DIR = OUTPUT_BASE / sweep_folder
    LOGS_DIR = OUTPUT_DIR / "logs"
    RUNS_DIR = OUTPUT_DIR / "runs"

    # Create output directories
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)

    # Create parameter combinations
    param_df = create_parameter_combinations()
    total_runs = len(param_df)

    print("=" * 70)
    print("Dixon Glacier Full Parameter Sweep (256 runs)")
    print("=" * 70)
    print(f"\nGlacier geometry (true DEM hypsometry):")
    print(f"  Area:   42.16 km²")
    print(f"  Volume: 4.248 km³")
    print(f"  Bands:  57 (20m spacing)")
    print(f"\nParameter ranges:")
    for param, values in PARAMETER_GRID.items():
        print(f"  {param}: {[round(v, 4) for v in values]}")
    print(f"\nTotal combinations: {total_runs}")
    print(f"Simulation period: Fall {SIM_STARTYEAR} - Fall {SIM_ENDYEAR} (3 years)")
    print(f"\nOutput directory: {RUNS_DIR}")

    if args.dry_run:
        print("\n[DRY RUN] First 20 parameter combinations:")
        print(param_df.head(20).to_string())
        return

    # Set up logging
    log_file = LOGS_DIR / "sweep.log"

    # Save parameter grid and sweep info
    param_df.to_csv(OUTPUT_DIR / "parameters.csv", index=False)

    # Save sweep configuration
    sweep_config = {
        'glacier': RGI_GLAC_NUMBER,
        'sim_startyear': SIM_STARTYEAR,
        'sim_endyear': SIM_ENDYEAR,
        'total_runs': total_runs,
        'parameter_grid': {k: v.tolist() for k, v in PARAMETER_GRID.items()},
        'timestamp': timestamp,
        'output_dir': str(OUTPUT_DIR),
    }
    with open(OUTPUT_DIR / "sweep_config.json", 'w') as f:
        json.dump(sweep_config, f, indent=2)

    # Filter runs
    runs_to_execute = param_df[param_df['run_id'] >= args.start_run]
    if args.max_runs:
        runs_to_execute = runs_to_execute.head(args.max_runs)

    print(f"\nExecuting {len(runs_to_execute)} runs (starting from {args.start_run})...")
    print(f"Log file: {log_file}\n")

    # Execute sweep
    results = []
    start_time = time.time()

    for idx, (_, params) in enumerate(runs_to_execute.iterrows()):
        run_id = int(params['run_id'])
        elapsed = time.time() - start_time
        if idx > 0:
            avg_time = elapsed / idx
            remaining = avg_time * (len(runs_to_execute) - idx)
            eta = f"ETA: {remaining/60:.1f}min"
        else:
            eta = ""

        print(f"[{idx+1}/{len(runs_to_execute)}] Run {run_id:04d} | "
              f"kp={params['kp']:.2f} tbias={params['tbias']:+.1f} "
              f"ddfsnow={params['ddfsnow']:.4f} iceratio={params['ddfsnow_iceratio']:.2f} {eta}... ",
              end='', flush=True)

        result = run_single_simulation(params.to_dict(), log_file)
        results.append(result)

        status = "OK" if result['success'] else "FAIL"
        print(f"{status} ({result['runtime']:.1f}s)")

    # Summary
    total_time = time.time() - start_time
    successful = sum(1 for r in results if r['success'])

    print("\n" + "=" * 70)
    print("FULL SWEEP COMPLETE")
    print("=" * 70)
    print(f"Total runs: {len(results)}")
    print(f"Successful: {successful} ({successful/len(results)*100:.1f}%)")
    print(f"Failed: {len(results) - successful}")
    print(f"Total time: {total_time/60:.1f} minutes ({total_time/3600:.2f} hours)")
    print(f"Avg time per run: {total_time/len(results):.1f}s")
    print(f"\nRun folders: {RUNS_DIR}")

    # Save results
    results_df = pd.DataFrame(results)
    results_df.to_csv(OUTPUT_DIR / "results.csv", index=False)
    print(f"Results saved to: {OUTPUT_DIR / 'results.csv'}")


if __name__ == "__main__":
    main()
