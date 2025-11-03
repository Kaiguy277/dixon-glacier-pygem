#!/usr/bin/env python3
"""
Test Parameter Fix - Verify Different Parameters Produce Different Results

Tests 3 different parameter combinations to confirm our fix works:
1. Conservative: tbias=-3, kp=1.0, ddf=0.004
2. Moderate: tbias=-2, kp=1.5, ddf=0.005  
3. Aggressive: tbias=-1, kp=2.0, ddf=0.006

Should produce different final areas if fix is working correctly.
"""

import os
import sys
import subprocess
import time
import json
from pathlib import Path
from datetime import datetime

def run_parameter_test(test_id, tbias, kp, ddfsnow):
    """Run single test with specific parameters"""
    
    print(f"\n🧪 Test {test_id}: tbias={tbias}, kp={kp}, ddf={ddfsnow}")
    
    # Create results directory
    results_dir = Path("/Users/kaimyers/PygemRound2/parameter_fix_test")
    run_dir = results_dir / f"test_{test_id}"
    run_dir.mkdir(parents=True, exist_ok=True)
    
    # PyGEM simulation script
    script_path = "/Users/kaimyers/PygemRound2/PyGEM/pygem/bin/run/run_simulation.py"
    
    # Build command
    cmd = [
        sys.executable, script_path,
        '-kp', str(kp),
        '-tbias', str(tbias),
        '-ddfsnow', str(ddfsnow),
        '-rgi_glac_number', '1.20947',
        '-sim_startyear', '2015',
        '-sim_endyear', '2025',  # Shorter run for quick test
        '-export_extra_vars',
        '-outputfn_sfix', f'_fixtest{test_id}'
    ]
    
    print(f"Command: {' '.join(cmd)}")
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            cmd,
            cwd="/Users/kaimyers/PygemRound2",
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        runtime = time.time() - start_time
        
        # Save logs
        with open(run_dir / 'stdout.log', 'w') as f:
            f.write(result.stdout)
        with open(run_dir / 'stderr.log', 'w') as f:
            f.write(result.stderr)
        
        if result.returncode == 0:
            print(f"✅ Test {test_id} SUCCESS in {runtime:.1f}s")
            
            # Check for output files and analyze
            output_base = Path("/Users/kaimyers/PygemRound2/data/Output/simulations/01/ACCESS-CM2/ssp245")
            stats_files = list((output_base / "stats").glob(f"*_fixtest{test_id}*.nc")) if (output_base / "stats").exists() else []
            
            final_area = None
            initial_area = None
            mass_balance = None
            
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
                        
                        if 'glac_massbaltotal_annual' in ds.variables:
                            mb_data = ds.variables['glac_massbaltotal_annual'][0, :]
                            mass_balance = mb_data.sum() / initial_area / 1e6  # Convert to m w.e.
                            print(f"   ⚖️ Total mass balance: {mass_balance:.2f} m w.e.")
                            
                except Exception as e:
                    print(f"   ⚠️ Data analysis error: {e}")
            
            return {
                'test_id': test_id,
                'status': 'success',
                'runtime': runtime,
                'parameters': {'tbias': tbias, 'kp': kp, 'ddfsnow': ddfsnow},
                'initial_area_km2': initial_area,
                'final_area_km2': final_area,
                'mass_balance_mwe': mass_balance,
                'output_files': len(stats_files)
            }
        
        else:
            print(f"❌ Test {test_id} FAILED (code {result.returncode}) after {runtime:.1f}s")
            print(f"Error: {result.stderr[-200:]}")
            
            return {
                'test_id': test_id,
                'status': 'failed',
                'runtime': runtime,
                'parameters': {'tbias': tbias, 'kp': kp, 'ddfsnow': ddfsnow},
                'error': result.stderr[-500:]
            }
    
    except Exception as e:
        print(f"💥 Test {test_id} ERROR: {e}")
        return {
            'test_id': test_id,
            'status': 'error',
            'parameters': {'tbias': tbias, 'kp': kp, 'ddfsnow': ddfsnow},
            'error': str(e)
        }

def main():
    """Test parameter fix with 3 different combinations"""
    print("🔧 TESTING PARAMETER FIX")
    print("=" * 50)
    print("Verifying different parameters produce different results")
    
    # Test cases with different parameter values
    test_cases = [
        (1, -3.0, 1.0, 0.004),  # Conservative
        (2, -2.0, 1.5, 0.005),  # Moderate  
        (3, -1.0, 2.0, 0.006)   # Aggressive
    ]
    
    results = []
    
    for test_id, tbias, kp, ddfsnow in test_cases:
        result = run_parameter_test(test_id, tbias, kp, ddfsnow)
        results.append(result)
        
        # Save individual result
        results_dir = Path("/Users/kaimyers/PygemRound2/parameter_fix_test")
        with open(results_dir / f"test_{test_id}_result.json", 'w') as f:
            json.dump(result, f, indent=2, default=str)
        
        # Brief pause between tests
        time.sleep(3)
    
    # Analysis
    print("\n" + "=" * 50)
    print("🔬 PARAMETER FIX VALIDATION")
    print("=" * 50)
    
    successful = [r for r in results if r['status'] == 'success']
    
    if len(successful) == 3:
        print("✅ All tests successful!")
        
        # Check if results are different
        final_areas = [r['final_area_km2'] for r in successful if r['final_area_km2'] is not None]
        mass_balances = [r['mass_balance_mwe'] for r in successful if r['mass_balance_mwe'] is not None]
        
        if len(set([round(a, 3) for a in final_areas])) > 1:
            print("🎉 SUCCESS: Different parameters produce different results!")
            print("✅ Parameter fix is working correctly")
            
            for result in successful:
                params = result['parameters']
                area = result.get('final_area_km2', 'N/A')
                mb = result.get('mass_balance_mwe', 'N/A')
                print(f"   Test {result['test_id']}: Final area {area:.3f} km², MB {mb:.2f} m w.e.")
                
            # Calculate sensitivity
            area_range = max(final_areas) - min(final_areas)
            area_variability = area_range / min(final_areas) * 100
            print(f"\n📊 SENSITIVITY ANALYSIS:")
            print(f"   Area range: {min(final_areas):.3f} - {max(final_areas):.3f} km²")
            print(f"   Area variability: {area_variability:.1f}%")
            
            if len(mass_balances) == 3:
                mb_range = max(mass_balances) - min(mass_balances)
                print(f"   Mass balance range: {min(mass_balances):.2f} - {max(mass_balances):.2f} m w.e.")
        
        else:
            print("❌ FAILED: All tests still produce identical results")
            print("🚨 Parameter fix did not work as expected")
            for result in successful:
                area = result.get('final_area_km2', 'N/A')
                print(f"   Test {result['test_id']}: Final area {area}")
    
    else:
        print(f"⚠️ Only {len(successful)}/3 tests successful")
        failed = [r for r in results if r['status'] != 'success']
        for result in failed:
            print(f"   Test {result['test_id']}: {result.get('status', 'unknown error')}")
    
    # Save summary
    results_dir = Path("/Users/kaimyers/PygemRound2/parameter_fix_test")
    with open(results_dir / "parameter_fix_test_summary.json", 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Results saved to: {results_dir}")
    
    return results

if __name__ == "__main__":
    results = main()
    print("\n🏁 Parameter fix test completed!")