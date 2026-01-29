#!/usr/bin/env python3
"""
Dixon Glacier Mega Parameter Sweep - No Retry Version
====================================================

Single-attempt execution for maximum speed on 250,000 parameter combinations.
Based on our proven framework but removes retry mechanism to save time.

Usage:
    python3 run_dixon_mega_sweep_no_retry.py --grid mega250k
    python3 run_dixon_mega_sweep_no_retry.py --runs 100000
    nohup python3 run_dixon_mega_sweep_no_retry.py --grid mega250k --ssd > mega_sweep.log 2>&1 &
"""

import argparse
import sys
import os
import time
import json
import numpy as np
from datetime import datetime
from pathlib import Path
import subprocess
import shutil

# Add project directory to path
sys.path.append('/Users/kaimyers/PygemRound2')

def create_mega_parameter_grid():
    """Create the 250,000 parameter grid based on our design analysis"""
    
    print("🎯 Creating Mega Parameter Grid (250,000 combinations)")
    print("=" * 55)
    
    # Based on our comprehensive analysis from design_mega_parameter_sweep.py
    parameter_ranges = {
        'tbias': np.linspace(-10.0, 5.0, 25),       # 25 values: -10°C to +5°C
        'kp': np.linspace(0.5, 8.0, 25),           # 25 values: 0.5 to 8.0
        'ddfsnow': np.linspace(0.001, 0.012, 20),  # 20 values: 0.001 to 0.012 m°C⁻¹d⁻¹
        'ddfsnow_iceratio': np.linspace(0.2, 1.2, 20)  # 20 values: 0.2 to 1.2
    }
    
    print(f"📊 Parameter Ranges:")
    total_combinations = 1
    for param, values in parameter_ranges.items():
        total_combinations *= len(values)
        print(f"   {param}: {values.min():.3f} to {values.max():.3f} ({len(values)} values)")
    
    print(f"\n🎯 Total combinations: {total_combinations:,}")
    
    return parameter_ranges

def generate_parameter_combinations(param_ranges, max_combinations=None):
    """Generate all parameter combinations"""
    print(f"\n🔄 Generating parameter combinations...")
    
    combinations = []
    run_id = 0
    
    for tbias in param_ranges['tbias']:
        for kp in param_ranges['kp']:
            for ddfsnow in param_ranges['ddfsnow']:
                for iceratio in param_ranges['ddfsnow_iceratio']:
                    # Calculate ice degree-day factor
                    ddfice = ddfsnow / iceratio
                    
                    combinations.append({
                        'run_id': run_id,
                        'tbias': tbias,
                        'kp': kp,
                        'ddfsnow': ddfsnow,
                        'ddfsnow_iceratio': iceratio,
                        'ddfice': ddfice
                    })
                    run_id += 1
                    
                    if max_combinations and len(combinations) >= max_combinations:
                        print(f"   Limited to first {max_combinations:,} combinations")
                        return combinations
    
    print(f"   Generated {len(combinations):,} combinations")
    return combinations

class MegaParameterSweep:
    def __init__(self, output_dir=None, use_ssd=True):
        """Initialize mega parameter sweep"""
        self.base_dir = Path("/Users/kaimyers/PygemRound2")
        
        # Set up output directory
        if output_dir:
            self.output_dir = Path(output_dir)
        elif use_ssd and Path("/Volumes/Extreme SSD").exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.output_dir = Path(f"/Volumes/Extreme SSD/dixon_mega_sweep_{timestamp}")
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.output_dir = Path(f"/Users/kaimyers/PygemRound2/dixon_mega_sweep_{timestamp}")
        
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.log_dir = self.output_dir / "logs"
        self.log_dir.mkdir(exist_ok=True)
        
        # PyGEM configuration
        self.pygem_script = "/Users/kaimyers/PygemRound2/PyGEM/pygem/bin/run/run_simulation.py"
        self.rgi_number = "1.20947"
        self.start_year = 2023
        self.end_year = 2025
        
        print(f"📁 Output directory: {self.output_dir}")
        print(f"📄 Log directory: {self.log_dir}")
    
    def execute_single_run_fast(self, param_combo):
        """Execute single PyGEM run with NO RETRY mechanism for speed"""
        run_id = param_combo['run_id']
        
        try:
            # Clean any existing partial outputs (just in case)
            self.clean_partial_outputs(run_id)
            
            # Build PyGEM command
            cmd = [
                "python3", self.pygem_script,
                "-rgi_glac_number", self.rgi_number,
                "-sim_startyear", str(self.start_year),
                "-sim_endyear", str(self.end_year),
                "-kp", str(param_combo['kp']),
                "-tbias", str(param_combo['tbias']),
                "-ddfsnow", str(param_combo['ddfsnow']),
                "-ddfsnow_iceratio", str(param_combo['ddfsnow_iceratio']),
                "-export_extra_vars",
                "-export_binned_data", 
                "-outputfn_sfix", f"_megasweep_run{run_id:06d}"
            ]
            
            # Execute PyGEM simulation (single attempt only)
            start_time = time.time()
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1200,  # 20 minute timeout (reduced from 30)
                cwd=self.base_dir
            )
            runtime = time.time() - start_time
            
            # Check if execution was successful
            if result.returncode == 0:
                # Verify and copy outputs
                if self.verify_and_copy_outputs(run_id, param_combo):
                    return {
                        'success': True,
                        'run_id': run_id,
                        'runtime': runtime,
                        'attempt': 1
                    }
                else:
                    # Output verification failed
                    return {
                        'success': False,
                        'run_id': run_id,
                        'runtime': runtime,
                        'error': 'Output verification failed',
                        'attempt': 1
                    }
            else:
                # PyGEM execution failed
                return {
                    'success': False,
                    'run_id': run_id,
                    'runtime': runtime,
                    'error': f'PyGEM failed (exit code {result.returncode})',
                    'stderr': result.stderr[:200] if result.stderr else '',
                    'attempt': 1
                }
                
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'run_id': run_id,
                'runtime': 1200,  # Timeout duration
                'error': 'Timeout after 20 minutes',
                'attempt': 1
            }
        except Exception as e:
            return {
                'success': False,
                'run_id': run_id,
                'runtime': 0,
                'error': f'Exception: {str(e)}',
                'attempt': 1
            }
    
    def clean_partial_outputs(self, run_id):
        """Clean partial outputs from any previous runs"""
        stats_pattern = f"*megasweep_run{run_id:06d}all.nc"
        binned_pattern = f"*megasweep_run{run_id:06d}binned.nc"
        
        # Clean PyGEM output directories
        output_paths = [
            Path("/Users/kaimyers/PygemRound2/data/Output/simulations"),
            self.output_dir
        ]
        
        for output_path in output_paths:
            if output_path.exists():
                for pattern in [stats_pattern, binned_pattern]:
                    for file in output_path.rglob(pattern):
                        try:
                            file.unlink()
                        except:
                            pass
    
    def verify_and_copy_outputs(self, run_id, param_combo):
        """Verify PyGEM outputs exist and copy to results directory"""
        
        # PyGEM output file patterns
        stats_pattern = f"*megasweep_run{run_id:06d}all.nc"
        binned_pattern = f"*megasweep_run{run_id:06d}binned.nc"
        
        # Search for files in PyGEM output directories
        search_paths = [
            Path("/Users/kaimyers/PygemRound2/data/Output/simulations/01/ACCESS-CM2/ssp245/stats"),
            Path("/Users/kaimyers/PygemRound2/data/Output/simulations/01/ACCESS-CM2/ssp245/binned")
        ]
        
        copied_files = 0
        run_dir = self.output_dir / f"run_{run_id:06d}"
        run_dir.mkdir(exist_ok=True)
        
        # Find and copy files
        for search_path in search_paths:
            if not search_path.exists():
                continue
                
            for pattern in [stats_pattern, binned_pattern]:
                for source_file in search_path.glob(pattern):
                    if source_file.stat().st_size > 1024:  # At least 1KB
                        dest_file = run_dir / source_file.name
                        shutil.copy2(source_file, dest_file)
                        copied_files += 1
        
        # Save parameter information
        param_file = run_dir / "parameters.json"
        with open(param_file, 'w') as f:
            json.dump(param_combo, f, indent=2)
        
        return copied_files >= 2  # Need both stats and binned files
    
    def execute_mega_sweep(self, param_combinations):
        """Execute the complete mega parameter sweep"""
        print(f"\n🚀 Starting Mega Parameter Sweep (NO RETRY)")
        print("=" * 50)
        print(f"   Total combinations: {len(param_combinations):,}")
        print(f"   Execution mode: Single attempt (no retries)")
        print(f"   Timeout per run: 20 minutes")
        print(f"   Expected higher failure rate but faster completion")
        
        # Estimate performance
        avg_time_per_run = 5.0  # Slightly faster without retry overhead
        estimated_hours = (len(param_combinations) * avg_time_per_run) / 3600
        estimated_days = estimated_hours / 24
        
        print(f"   Estimated runtime: {estimated_hours:.1f} hours ({estimated_days:.1f} days)")
        print()
        
        # Initialize tracking
        start_time = time.time()
        successful_runs = []
        failed_runs = []
        
        # Progress tracking
        last_progress_time = start_time
        progress_interval = 3600  # Update every hour
        
        for i, param_combo in enumerate(param_combinations):
            
            # Progress reporting
            if i % 100 == 0 or i == len(param_combinations) - 1:
                elapsed = time.time() - start_time
                progress_pct = (i + 1) / len(param_combinations) * 100
                
                if i > 0:
                    avg_time = elapsed / (i + 1)
                    remaining_runs = len(param_combinations) - (i + 1)
                    eta_hours = remaining_runs * avg_time / 3600
                    
                    print(f"📊 Run {param_combo['run_id']:6d}/{len(param_combinations):,} "
                          f"({progress_pct:5.2f}%) - "
                          f"Success: {len(successful_runs):,} "
                          f"({len(successful_runs)/(i+1)*100:.1f}%) - "
                          f"ETA: {eta_hours:.1f}h")
                else:
                    print(f"📊 Starting run {param_combo['run_id']:6d}...")
            
            # Execute run (single attempt)
            result = self.execute_single_run_fast(param_combo)
            
            if result['success']:
                successful_runs.append(result)
            else:
                failed_runs.append(result)
            
            # Hourly detailed progress
            current_time = time.time()
            if current_time - last_progress_time >= progress_interval:
                self.log_detailed_progress(i + 1, len(param_combinations), successful_runs, failed_runs, start_time)
                last_progress_time = current_time
        
        # Final summary
        total_time = time.time() - start_time
        success_rate = len(successful_runs) / len(param_combinations) * 100
        
        print(f"\n🎉 MEGA PARAMETER SWEEP COMPLETE!")
        print("=" * 40)
        print(f"   Total runtime: {total_time/3600:.2f} hours ({total_time/86400:.2f} days)")
        print(f"   Successful runs: {len(successful_runs):,} ({success_rate:.1f}%)")
        print(f"   Failed runs: {len(failed_runs):,} ({100-success_rate:.1f}%)")
        print(f"   Average time per run: {total_time/len(param_combinations):.1f}s")
        print(f"   Effective run rate: {len(param_combinations)/(total_time/3600):.0f} runs/hour")
        
        # Save comprehensive summary
        self.save_mega_summary({
            'total_combinations': len(param_combinations),
            'successful_runs': len(successful_runs),
            'failed_runs': len(failed_runs),
            'success_rate': success_rate,
            'total_runtime_hours': total_time / 3600,
            'avg_time_per_run': total_time / len(param_combinations),
            'run_rate_per_hour': len(param_combinations) / (total_time / 3600),
            'execution_mode': 'single_attempt_no_retry',
            'timeout_minutes': 20
        })
        
        return {
            'successful_runs': successful_runs,
            'failed_runs': failed_runs,
            'success_rate': success_rate,
            'total_runtime': total_time
        }
    
    def log_detailed_progress(self, completed, total, successful, failed, start_time):
        """Log detailed progress information"""
        elapsed = time.time() - start_time
        success_rate = len(successful) / completed * 100
        avg_time = elapsed / completed
        
        print(f"\n⏰ Hourly Progress Update:")
        print(f"   Completed: {completed:,}/{total:,} ({completed/total*100:.2f}%)")
        print(f"   Success rate: {success_rate:.1f}% ({len(successful):,} successful)")
        print(f"   Failed runs: {len(failed):,}")
        print(f"   Average time per run: {avg_time:.1f}s")
        print(f"   Runtime so far: {elapsed/3600:.1f} hours")
        print(f"   Estimated completion: {(total-completed)*avg_time/3600:.1f} hours remaining")
        print()
    
    def save_mega_summary(self, summary_data):
        """Save mega sweep summary"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_file = self.output_dir / f"mega_sweep_summary_{timestamp}.json"
        
        with open(summary_file, 'w') as f:
            json.dump(summary_data, f, indent=2)
        
        print(f"📄 Summary saved: {summary_file}")

def main():
    parser = argparse.ArgumentParser(description="Dixon Glacier Mega Parameter Sweep (No Retry)")
    parser.add_argument('--grid', choices=['mega250k'], default='mega250k',
                       help='Parameter grid (mega250k = 250,000 runs)')
    parser.add_argument('--runs', type=int, help='Limit number of runs')
    parser.add_argument('--output', help='Output directory path')
    parser.add_argument('--ssd', action='store_true', default=True, help='Use external SSD')
    
    args = parser.parse_args()
    
    print("🏔️ Dixon Glacier Mega Parameter Sweep (No Retry)")
    print("=" * 55)
    print(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⚡ Mode: Single attempt execution (no retries)")
    print(f"🎯 Target: ~250,000 parameter combinations")
    print()
    
    # Create parameter grid
    param_ranges = create_mega_parameter_grid()
    param_combinations = generate_parameter_combinations(param_ranges, args.runs)
    
    print(f"\n💾 Storage and Performance Estimates:")
    storage_gb = len(param_combinations) * 0.2 / 1024  # ~200KB per run
    print(f"   Expected storage: {storage_gb:.0f} GB")
    print(f"   Files to create: ~{len(param_combinations) * 3:,}")
    
    # Initialize sweep
    sweep = MegaParameterSweep(args.output, args.ssd)
    
    # Execute mega sweep
    print(f"\n🚀 Starting execution...")
    print(f"   Process ID: {os.getpid()}")
    
    try:
        results = sweep.execute_mega_sweep(param_combinations)
        
        if results['success_rate'] > 85:
            print(f"\n✅ EXCELLENT SUCCESS RATE!")
            print(f"🎉 Ready for comprehensive parameter analysis!")
        elif results['success_rate'] > 70:
            print(f"\n✅ GOOD SUCCESS RATE!")
            print(f"📊 Sufficient data for robust analysis!")
        else:
            print(f"\n⚠️ MODERATE SUCCESS RATE")
            print(f"🔍 Consider investigating failure patterns")
        
        return True
        
    except KeyboardInterrupt:
        print(f"\n⏹️ Mega sweep interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Mega sweep failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)