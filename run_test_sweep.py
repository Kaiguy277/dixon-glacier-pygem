#!/usr/bin/env python3
"""
Small Test Parameter Sweep for Dixon Glacier
=============================================

Runs a 2x2x2x2 = 16 combination parameter sweep to verify
the updated geometry with true hypsometry works correctly.

Uses the corrected glacier directory with:
- True area: 42.16 km² (from DEM masking)
- Volume: 4.248 km³ (from Farinotti consensus thickness)
- 39 elevation bands (30m spacing)
- Elevation: 414 - 1533 m

Parameter ranges (subset of full sweep):
- tbias: -5.0 to +2.0 °C
- kp: 1.0 to 4.0
- ddfsnow: 0.003 to 0.008 m°C⁻¹d⁻¹
- ddfsnow_iceratio: 0.4 to 0.8

Usage:
    python3 run_test_sweep.py
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
OUTPUT_DIR = Path("/media/kai/Extreme SSD/Linux_Pygem/test_sweep")
LOGS_DIR = OUTPUT_DIR / "logs"
RUNS_DIR = OUTPUT_DIR / "runs"

# Glacier and simulation settings
RGI_GLAC_NUMBER = "1.20947"
SIM_STARTYEAR = 2023
SIM_ENDYEAR = 2025  # 2-year simulation for better testing

# Small test grid (2 values each = 16 combinations)
PARAMETER_GRID = {
    'tbias': np.array([-5.0, 2.0]),           # Cold and warm bias
    'kp': np.array([1.0, 4.0]),               # Low and high precip
    'ddfsnow': np.array([0.003, 0.008]),      # Low and high melt rate
    'ddfsnow_iceratio': np.array([0.4, 0.8])  # Different snow/ice ratios
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
        f.write(f"Dixon Glacier Test Sweep - Run {int(params['run_id']):04d}\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Glacier: RGI60-{RGI_GLAC_NUMBER}\n")
        f.write(f"Simulation Period: {SIM_STARTYEAR} - {SIM_ENDYEAR}\n\n")
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
        for nc_file in stats_dir.glob(f"*_test{run_id:04d}*.nc"):
            dest = run_dir / nc_file.name
            shutil.move(str(nc_file), str(dest))
            files_moved.append(nc_file.name)

    # Check binned directory
    binned_dir = pygem_output_base / "binned"
    if binned_dir.exists():
        for nc_file in binned_dir.glob(f"*_test{run_id:04d}*.nc"):
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
        '-outputfn_sfix', f'_test{run_id:04d}',
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
                status = "SUCCESS" if success else "FAILED"
                f.write(f"Run {run_id:04d}: {status} in {runtime:.1f}s | "
                       f"kp={params['kp']:.2f} tbias={params['tbias']:.1f} "
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
    # Create output directories
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)

    # Create parameter combinations
    param_df = create_parameter_combinations()
    total_runs = len(param_df)

    print("=" * 60)
    print("Dixon Glacier Test Parameter Sweep")
    print("=" * 60)
    print(f"\nUsing TRUE GEOMETRY from corrected glacier directory:")
    print(f"  Area:   42.16 km² (from DEM)")
    print(f"  Volume: 4.248 km³ (from consensus thickness)")
    print(f"  Bands:  39 (30m spacing)")
    print(f"\nParameter ranges:")
    for param, values in PARAMETER_GRID.items():
        print(f"  {param}: {values}")
    print(f"\nTotal combinations: {total_runs}")
    print(f"Glacier: RGI60-{RGI_GLAC_NUMBER}")
    print(f"Simulation period: {SIM_STARTYEAR}-{SIM_ENDYEAR}")
    print(f"\nOutput directory: {RUNS_DIR}")

    # Set up logging
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = LOGS_DIR / f"test_sweep_{timestamp}.log"

    # Save parameter grid
    param_df.to_csv(OUTPUT_DIR / f"parameters_{timestamp}.csv", index=False)

    print(f"\nExecuting {total_runs} runs...")
    print(f"Log file: {log_file}\n")

    # Execute sweep
    results = []
    start_time = time.time()

    for idx, (_, params) in enumerate(param_df.iterrows()):
        run_id = int(params['run_id'])

        print(f"[{idx+1}/{total_runs}] Run {run_id:04d} | "
              f"kp={params['kp']:.1f} tbias={params['tbias']:+.1f} "
              f"ddfsnow={params['ddfsnow']:.4f} iceratio={params['ddfsnow_iceratio']:.2f} ... ",
              end='', flush=True)

        result = run_single_simulation(params.to_dict(), log_file)
        results.append(result)

        status = "OK" if result['success'] else "FAIL"
        print(f"{status} ({result['runtime']:.1f}s)")

    # Summary
    total_time = time.time() - start_time
    successful = sum(1 for r in results if r['success'])

    print("\n" + "=" * 60)
    print("TEST SWEEP COMPLETE")
    print("=" * 60)
    print(f"Total runs: {len(results)}")
    print(f"Successful: {successful} ({successful/len(results)*100:.1f}%)")
    print(f"Failed: {len(results) - successful}")
    print(f"Total time: {total_time/60:.1f} minutes")
    print(f"Avg time per run: {total_time/len(results):.1f}s")
    print(f"\nRun folders: {RUNS_DIR}")

    # Save results
    results_df = pd.DataFrame(results)
    results_df.to_csv(OUTPUT_DIR / f"results_{timestamp}.csv", index=False)
    print(f"Results saved to: {OUTPUT_DIR / f'results_{timestamp}.csv'}")


if __name__ == "__main__":
    main()
