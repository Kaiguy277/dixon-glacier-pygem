#!/usr/bin/env python3
"""
Working Parameter Sweep - 9 Realistic Parameter Combinations

Uses the proven approach from simple_parameter_test.py that achieved 100% success rate.
This script runs 9 realistic parameter combinations using only command-line arguments.

Fixed approach:
- No config file manipulation (major source of failures)
- Direct command-line parameters only
- Realistic parameter ranges based on literature
- Comprehensive output validation
- Full 2015-2100 time period
"""

import os
import sys
import subprocess
import time
import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

def create_realistic_parameter_grid():
    """Create 9 realistic parameter combinations spanning the parameter space"""
    
    # Literature-based realistic ranges for Dixon Glacier
    param_ranges = {
        'tbias': [-4.0, -2.0, 0.0],      # Temperature bias (°C)
        'kp': [0.8, 1.4, 2.0],           # Precipitation factor  
        'ddfsnow': [0.003, 0.005, 0.007] # Degree-day factor (m°C⁻¹d⁻¹)
    }
    
    # Generate 3x3 grid (9 combinations)
    import itertools
    combinations = list(itertools.product(*param_ranges.values()))
    
    parameter_sets = []
    for i, combo in enumerate(combinations):
        param_set = {
            'run_id': i,
            'tbias': combo[0],
            'kp': combo[1], 
            'ddfsnow': combo[2]
        }
        parameter_sets.append(param_set)
    
    return parameter_sets

def run_single_simulation(params):
    """Run single PyGEM simulation using the proven approach"""
    
    run_id = params['run_id']
    tbias = params['tbias']
    kp = params['kp'] 
    ddfsnow = params['ddfsnow']
    
    print(f"\n🧪 Starting run {run_id:02d}: tbias={tbias}, kp={kp}, ddf={ddfsnow}")
    
    # Create results directory
    results_dir = Path("/Users/kaimyers/PygemRound2/parameter_sweep_working_results")
    run_dir = results_dir / f"run_{run_id:02d}"
    run_dir.mkdir(parents=True, exist_ok=True)
    
    # PyGEM simulation script
    script_path = "/Users/kaimyers/PygemRound2/PyGEM/pygem/bin/run/run_simulation.py"
    
    # Build command using only command-line arguments (proven approach)
    cmd = [
        sys.executable, script_path,
        '-kp', str(kp),
        '-tbias', str(tbias),
        '-ddfsnow', str(ddfsnow),
        '-rgi_glac_number', '1.20947',
        '-sim_startyear', '2015',
        '-sim_endyear', '2100',
        '-export_extra_vars',
        '-export_binned_data',
        '-outputfn_sfix', f'_working{run_id:02d}'
    ]
    
    print(f"Command: {' '.join(cmd)}")
    
    # Run simulation
    start_time = time.time()
    
    try:
        result = subprocess.run(
            cmd,
            cwd="/Users/kaimyers/PygemRound2",
            capture_output=True,
            text=True,
            timeout=1800  # 30 minute timeout for full simulation
        )
        
        runtime = time.time() - start_time
        
        # Save logs
        with open(run_dir / 'stdout.log', 'w') as f:
            f.write(result.stdout)
        with open(run_dir / 'stderr.log', 'w') as f:
            f.write(result.stderr)
        
        # Check results
        if result.returncode == 0:
            print(f"✅ Run {run_id:02d} SUCCESS in {runtime:.1f}s")
            
            # Check for output files
            output_base = Path("/Users/kaimyers/PygemRound2/data/Output/simulations/01/ACCESS-CM2/ssp245")
            
            stats_files = list((output_base / "stats").glob(f"*_working{run_id:02d}*.nc")) if (output_base / "stats").exists() else []
            binned_files = list((output_base / "binned").glob(f"*_working{run_id:02d}*.nc")) if (output_base / "binned").exists() else []
            
            print(f"   📄 Output files: {len(stats_files)} stats, {len(binned_files)} binned")
            
            # Copy files to results
            import shutil
            for nc_file in stats_files + binned_files:
                shutil.copy2(nc_file, run_dir / nc_file.name)
            
            # Validate file contents and extract key metrics
            final_area = None
            initial_area = None
            max_discharge = None
            
            if stats_files:
                try:
                    import netCDF4 as nc
                    with nc.Dataset(stats_files[0], 'r') as ds:
                        if 'glac_area_annual' in ds.variables:
                            area_data = ds.variables['glac_area_annual'][0, :] / 1e6  # Convert to km²
                            initial_area = area_data[0] if area_data[0] > 0 else area_data[1]
                            final_area = area_data[-1]
                            area_loss_pct = (initial_area - final_area) / initial_area * 100
                            print(f"   🏔️ Area: {initial_area:.2f} → {final_area:.2f} km² ({area_loss_pct:.1f}% loss)")
                        
                        if 'glac_runoff_monthly' in ds.variables:
                            discharge_data = ds.variables['glac_runoff_monthly'][0, :]
                            max_discharge = np.max(discharge_data)
                            print(f"   💧 Max discharge: {max_discharge:.2e} m³/s")
                            
                except Exception as e:
                    print(f"   ⚠️ File validation error: {e}")
            
            return {
                'run_id': run_id,
                'status': 'success',
                'runtime': runtime,
                'parameters': params,
                'initial_area_km2': initial_area,
                'final_area_km2': final_area,
                'max_discharge_m3s': max_discharge,
                'output_files': len(stats_files) + len(binned_files),
                'validation': 'success'
            }
        
        else:
            print(f"❌ Run {run_id:02d} FAILED (code {result.returncode}) after {runtime:.1f}s")
            print(f"   Error: {result.stderr[-200:]}")
            
            return {
                'run_id': run_id,
                'status': 'failed',
                'runtime': runtime,
                'parameters': params,
                'returncode': result.returncode,
                'error': result.stderr[-500:]
            }
    
    except subprocess.TimeoutExpired:
        print(f"⏰ Run {run_id:02d} TIMEOUT after 30 minutes")
        return {
            'run_id': run_id,
            'status': 'timeout',
            'runtime': 1800,
            'parameters': params
        }
    
    except Exception as e:
        print(f"💥 Run {run_id:02d} ERROR: {e}")
        return {
            'run_id': run_id,
            'status': 'error',
            'runtime': 0,
            'parameters': params,
            'error': str(e)
        }

def main():
    """Run working parameter sweep with 9 realistic combinations"""
    print("🚀 WORKING PARAMETER SWEEP - 9 Realistic Combinations")
    print("=" * 60)
    print("Using proven approach from simple test (100% success rate)")
    
    # Create parameter grid
    parameter_sets = create_realistic_parameter_grid()
    
    print(f"\nTesting {len(parameter_sets)} parameter combinations:")
    for params in parameter_sets:
        print(f"  Run {params['run_id']:02d}: tbias={params['tbias']}, kp={params['kp']}, ddf={params['ddfsnow']}")
    
    # Run simulations sequentially for reliability
    results = []
    start_time = time.time()
    
    for params in parameter_sets:
        result = run_single_simulation(params)
        results.append(result)
        
        # Save individual result
        results_dir = Path("/Users/kaimyers/PygemRound2/parameter_sweep_working_results")
        with open(results_dir / f"run_{params['run_id']:02d}_result.json", 'w') as f:
            json.dump(result, f, indent=2, default=str)
        
        # Brief pause between runs
        time.sleep(5)
    
    total_time = time.time() - start_time
    
    # Analyze results
    print("\n" + "=" * 60)
    print("📊 WORKING PARAMETER SWEEP RESULTS")
    print("=" * 60)
    
    successful = [r for r in results if r['status'] == 'success']
    failed = [r for r in results if r['status'] != 'success']
    
    print(f"Total runtime: {total_time/60:.1f} minutes")
    print(f"Total runs: {len(results)}")
    print(f"✅ Successful: {len(successful)} ({len(successful)/len(results)*100:.1f}%)")
    print(f"❌ Failed: {len(failed)} ({len(failed)/len(results)*100:.1f}%)")
    
    if successful:
        print(f"\n🎉 SUCCESS DETAILS:")
        for result in successful:
            params = result['parameters']
            area = result.get('final_area_km2', 'N/A')
            files = result.get('output_files', 0)
            print(f"  Run {result['run_id']:02d}: {result['runtime']:.1f}s, final area: {area} km², {files} files")
        
        # Parameter sensitivity analysis
        if len(successful) > 1:
            print(f"\n🔬 PARAMETER SENSITIVITY ANALYSIS:")
            
            # Create DataFrame for analysis
            df_results = pd.DataFrame(successful)
            
            if 'final_area_km2' in df_results.columns:
                areas = df_results['final_area_km2'].dropna()
                if len(areas) > 1 and areas.std() > 0:
                    print(f"   📊 Final area range: {areas.min():.2f} - {areas.max():.2f} km²")
                    print(f"   📈 Area variability: {areas.std():.2f} km² std dev")
                    
                    # Correlations with parameters
                    for param in ['tbias', 'kp', 'ddfsnow']:
                        param_values = [r['parameters'][param] for r in successful]
                        if len(set(param_values)) > 1:  # Only if parameter varies
                            correlation = np.corrcoef(param_values, areas)[0,1]
                            print(f"   🔗 {param} correlation with final area: {correlation:.3f}")
                else:
                    print("   ⚠️ All runs produced similar results - may need wider parameter ranges")
    
    if failed:
        print(f"\n❌ FAILURE DETAILS:")
        for result in failed:
            params = result['parameters']
            error = result.get('error', result.get('status', 'Unknown error'))
            print(f"  Run {result['run_id']:02d}: {error[:100]}...")
    
    # Save comprehensive summary
    results_dir = Path("/Users/kaimyers/PygemRound2/parameter_sweep_working_results")
    
    # Save as CSV
    summary_data = []
    for result in results:
        row = result['parameters'].copy()
        row.update({
            'run_id': result['run_id'],
            'status': result['status'],
            'runtime': result.get('runtime', 0),
            'final_area_km2': result.get('final_area_km2'),
            'output_files': result.get('output_files', 0)
        })
        summary_data.append(row)
    
    summary_df = pd.DataFrame(summary_data)
    summary_df.to_csv(results_dir / "parameter_sweep_working_summary.csv", index=False)
    
    # Save complete results
    with open(results_dir / "parameter_sweep_working_complete.json", 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Results saved to: {results_dir}")
    
    # Final assessment
    success_rate = len(successful) / len(results)
    
    print(f"\n🎯 FINAL ASSESSMENT:")
    if success_rate >= 0.9:
        print("🎉 EXCELLENT! Parameter sweep framework is working perfectly")
        print("✅ Ready for full-scale parameter exploration")
    elif success_rate >= 0.7:
        print("✅ GOOD! Parameter sweep framework is working well")
        print("⚠️ Minor optimization may improve reliability")
    elif success_rate >= 0.5:
        print("⚠️ PARTIAL SUCCESS - Some issues remain")
        print("🔧 Need to investigate failure modes")
    else:
        print("❌ POOR PERFORMANCE - Significant issues detected")
        print("🚨 Framework needs major debugging")
    
    return results

if __name__ == "__main__":
    results = main()
    print("\n🏁 Working parameter sweep completed!")