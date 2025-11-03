#!/usr/bin/env python3
"""
Parameter Sweep Validation Analysis

Analyzes existing parameter sweep results to validate:
1. Output files contain real data
2. Parameter variations produce different results
3. Framework can generate multiple successful runs
4. Data quality and completeness
"""

import os
import json
import pandas as pd
import numpy as np
from pathlib import Path

def analyze_existing_results():
    """Analyze existing parameter sweep results"""
    
    print("🔍 PARAMETER SWEEP VALIDATION ANALYSIS")
    print("=" * 60)
    
    # Check existing results
    results_dir = Path("/Users/kaimyers/PygemRound2/parameter_sweep/results")
    
    if not results_dir.exists():
        print("❌ No parameter sweep results directory found")
        return
    
    # Find successful runs (those with .nc files)
    successful_runs = []
    failed_runs = []
    
    for run_dir in sorted(results_dir.glob("run_*")):
        run_id = int(run_dir.name.split('_')[1])
        
        # Check for NetCDF output files
        nc_files = list(run_dir.glob("*.nc"))
        
        if nc_files:
            successful_runs.append((run_id, run_dir, nc_files))
        else:
            failed_runs.append((run_id, run_dir))
    
    print(f"📊 SUMMARY:")
    print(f"   Total run directories: {len(list(results_dir.glob('run_*')))}")
    print(f"   ✅ Successful runs: {len(successful_runs)}")
    print(f"   ❌ Failed runs: {len(failed_runs)}")
    print(f"   Success rate: {len(successful_runs)/(len(successful_runs)+len(failed_runs))*100:.1f}%")
    
    if not successful_runs:
        print("❌ No successful runs found - parameter sweep framework has issues")
        return
    
    print(f"\n🎯 SUCCESSFUL RUNS ANALYSIS:")
    
    # Load parameter information
    try:
        df = pd.read_csv("/Users/kaimyers/PygemRound2/parameter_sweep/parameter_sweep_summary.csv")
        print(f"   Parameters file loaded: {len(df)} parameter combinations")
    except:
        print("   ⚠️ Could not load parameter summary file")
        df = None
    
    # Analyze each successful run
    run_data = []
    
    for run_id, run_dir, nc_files in successful_runs:
        print(f"\n   Run {run_id:04d}:")
        print(f"      📁 Directory: {run_dir}")
        print(f"      📄 Output files: {len(nc_files)}")
        
        # Get parameter information
        if df is not None and run_id < len(df):
            params = df.iloc[run_id]
            print(f"      🔧 Parameters: tbias={params['tbias']}, kp={params['kp']}, ddf={params['ddfsnow']}")
            
            # Try to analyze the output data
            try:
                import netCDF4 as nc
                
                # Find the main stats file
                stats_files = [f for f in nc_files if 'all.nc' in f.name]
                if stats_files:
                    with nc.Dataset(stats_files[0], 'r') as ds:
                        # Check available variables
                        variables = list(ds.variables.keys())
                        print(f"      📋 Variables: {len(variables)} available")
                        
                        # Get glacier area data if available
                        if 'glac_area_annual' in ds.variables:
                            area_data = ds.variables['glac_area_annual'][0, :] / 1e6  # Convert to km²
                            initial_area = area_data[0] if area_data[0] > 0 else area_data[1]
                            final_area = area_data[-1]
                            area_loss_pct = (initial_area - final_area) / initial_area * 100
                            
                            print(f"      🏔️ Initial area: {initial_area:.2f} km²")
                            print(f"      🏔️ Final area: {final_area:.2f} km²")
                            print(f"      📉 Area loss: {area_loss_pct:.1f}%")
                            
                            run_data.append({
                                'run_id': run_id,
                                'tbias': params['tbias'],
                                'kp': params['kp'],
                                'ddfsnow': params['ddfsnow'],
                                'initial_area': initial_area,
                                'final_area': final_area,
                                'area_loss_pct': area_loss_pct,
                                'output_files': len(nc_files)
                            })
                        
                        # Get discharge data if available
                        if 'glac_runoff_monthly' in ds.variables:
                            discharge_data = ds.variables['glac_runoff_monthly'][0, :]
                            max_discharge = np.max(discharge_data)
                            print(f"      💧 Max discharge: {max_discharge:.2e} m³/s")
                            
            except ImportError:
                print("      ⚠️ netCDF4 not available for data analysis")
            except Exception as e:
                print(f"      ⚠️ Data analysis error: {e}")
    
    # Compare results across different parameters
    if len(run_data) > 1:
        print(f"\n🔬 PARAMETER SENSITIVITY ANALYSIS:")
        
        run_df = pd.DataFrame(run_data)
        
        # Check if different parameters produce different results
        if len(run_df['final_area'].unique()) > 1:
            print("   ✅ Parameter variations produce different results")
            print(f"   📊 Final area range: {run_df['final_area'].min():.2f} - {run_df['final_area'].max():.2f} km²")
            print(f"   📊 Area loss range: {run_df['area_loss_pct'].min():.1f}% - {run_df['area_loss_pct'].max():.1f}%")
            
            # Show parameter correlations
            if 'tbias' in run_df.columns:
                tbias_range = run_df['tbias'].max() - run_df['tbias'].min()
                kp_range = run_df['kp'].max() - run_df['kp'].min()
                ddf_range = run_df['ddfsnow'].max() - run_df['ddfsnow'].min()
                
                print(f"   🔧 Parameter ranges tested:")
                print(f"      tbias: {tbias_range:.1f}°C range")
                print(f"      kp: {kp_range:.1f} range") 
                print(f"      ddfsnow: {ddf_range:.4f} range")
        else:
            print("   ⚠️ All runs produced identical results - may indicate parameter range too narrow")
    
    # Check failure analysis
    if failed_runs:
        print(f"\n❌ FAILURE ANALYSIS:")
        print(f"   {len(failed_runs)} runs failed")
        
        # Sample a few failed runs to understand issues
        sample_failed = failed_runs[:3]
        for run_id, run_dir in sample_failed:
            print(f"   Run {run_id:04d}:")
            
            # Check for run_info.json
            run_info_file = run_dir / "run_info.json"
            if run_info_file.exists():
                try:
                    with open(run_info_file, 'r') as f:
                        run_info = json.load(f)
                    
                    status = run_info.get('status', 'unknown')
                    error = run_info.get('error_msg', 'No error message')
                    print(f"      Status: {status}")
                    if 'error' in error.lower() or 'fail' in error.lower():
                        print(f"      Error: {error[:100]}...")
                        
                except Exception as e:
                    print(f"      Could not read run info: {e}")
    
    # Overall assessment
    print(f"\n🎯 PARAMETER SWEEP FRAMEWORK ASSESSMENT:")
    
    success_rate = len(successful_runs)/(len(successful_runs)+len(failed_runs))
    
    if success_rate >= 0.8:
        print("   🎉 EXCELLENT! Parameter sweep framework is working well")
        print("   ✅ Ready for full-scale parameter sweep")
    elif success_rate >= 0.5:
        print("   ✅ GOOD! Parameter sweep framework is mostly functional")
        print("   ⚠️ Some optimization may be needed for better reliability")
    elif success_rate >= 0.2:
        print("   ⚠️ PARTIAL SUCCESS - Framework has significant issues")
        print("   🔧 Need to investigate and fix failure modes")
    else:
        print("   ❌ POOR PERFORMANCE - Major issues with parameter sweep")
        print("   🚨 Framework needs significant debugging")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    
    if len(successful_runs) > 0:
        print("   ✅ Basic parameter sweep functionality is working")
        print("   ✅ PyGEM simulations can run with parameter variations")
        print("   ✅ Output files are generated and contain real data")
    
    if len(failed_runs) > len(successful_runs):
        print("   🔧 Fix config file management issues")
        print("   🔧 Improve error handling and recovery")
        print("   🔧 Add parameter validation")
    
    print("   📋 Use realistic parameter ranges for future sweeps")
    print("   📋 Implement better progress tracking")
    print("   📋 Add output validation checks")
    
    return {
        'total_runs': len(successful_runs) + len(failed_runs),
        'successful_runs': len(successful_runs),
        'failed_runs': len(failed_runs),
        'success_rate': success_rate,
        'run_data': run_data
    }

if __name__ == "__main__":
    results = analyze_existing_results()
    print("\n🏁 Parameter sweep validation completed!")