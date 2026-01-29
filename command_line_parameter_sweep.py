#!/usr/bin/env python3
"""
Command-Line Parameter Sweep for PyGEM - Dixon Glacier
======================================================

ULTIMATE SOLUTION: This script bypasses ALL config file issues by using
only command-line arguments that we've verified work with PyGEM.

Key Features:
- Uses direct command-line parameter specification (no config files)
- Serial execution with retry mechanism and comprehensive output verification
- Designed for large-scale runs (1000-10000+ parameter combinations)
- Includes figure creation handling to avoid manual intervention
- Uses proven PyGEM source code modifications

Requirements:
- PyGEM source code must have ddfsnow_iceratio command-line argument added
- PyGEM source code must use args.ddfsnow_iceratio in ddfice calculation
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
from typing import Dict, List, Tuple, Optional, Any

class CommandLineParameterSweep:
    """
    Advanced parameter sweep using command-line arguments only (no config files)
    """
    
    def __init__(self, 
                 base_dir: str = "/Users/kaimyers/PygemRound2",
                 output_dir: str = None,
                 use_ssd: bool = True,
                 collect_binned: bool = True):
        """
        Initialize command-line parameter sweep framework
        
        Parameters:
        -----------
        base_dir : str
            PyGEM project root directory
        output_dir : str  
            Output directory for results (defaults to SSD if use_ssd=True)
        use_ssd : bool
            Use SSD for output storage for faster I/O
        collect_binned : bool
            Whether to collect binned files (default False for speed)
        """
        self.base_dir = Path(base_dir)
        self.pygem_script = self.base_dir / "PyGEM/pygem/bin/run/run_simulation.py"
        
        # Set up output directory (SSD for performance)
        if output_dir is None:
            if use_ssd:
                self.output_dir = Path("/Volumes/Extreme SSD") / "cmdline_parameter_sweep"
            else:
                self.output_dir = self.base_dir / "cmdline_parameter_sweep"
        else:
            self.output_dir = Path(output_dir)
        
        # Create directory structure
        self.results_dir = self.output_dir / "results"
        self.logs_dir = self.output_dir / "logs"
        
        for dir_path in [self.results_dir, self.logs_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Logging setup
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.main_log_file = self.logs_dir / f"cmdline_sweep_{timestamp}.log"
        
        # Store collection preferences
        self.collect_binned = collect_binned
        
        print(f"Command-line parameter sweep initialized")
        print(f"PyGEM Script: {self.pygem_script}")
        print(f"Output Directory: {self.output_dir}")
        print(f"Results Directory: {self.results_dir}")
        print(f"Collect binned files: {self.collect_binned}")
        
    def log(self, message: str, run_id: Optional[int] = None):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if run_id is not None:
            log_msg = f"{timestamp} [Run {run_id:04d}]: {message}"
        else:
            log_msg = f"{timestamp}: {message}"
        
        print(log_msg)
        
        # Write to main log
        with open(self.main_log_file, 'a') as f:
            f.write(log_msg + '\n')
        
        # Write to individual run log if specified
        if run_id is not None:
            run_log_file = self.logs_dir / f"run_{run_id:04d}.log"
            with open(run_log_file, 'a') as f:
                f.write(log_msg + '\n')
    
    def create_parameter_combinations(self, 
                                    tbias_range: List[float] = None,
                                    kp_range: List[float] = None, 
                                    ddfsnow_range: List[float] = None,
                                    ddfsnow_iceratio_range: List[float] = None,
                                    **kwargs) -> pd.DataFrame:
        """
        Create parameter combination grid using command-line arguments only
        
        Parameters:
        -----------
        tbias_range : List[float]
            Temperature bias values (°C) - e.g., [-9.0, -8.0, -7.0, -6.0]
        kp_range : List[float] 
            Precipitation factor values - e.g., [3.0, 4.0, 5.0, 6.0]
        ddfsnow_range : List[float]
            Degree-day factor snow values (m°C⁻¹d⁻¹) - e.g., [0.004, 0.005, 0.006, 0.007]
        ddfsnow_iceratio_range : List[float]
            Snow-ice ratio values - e.g., [0.5, 0.6, 0.7, 0.8]
        
        Returns:
        --------
        pd.DataFrame : Parameter combinations with unique run_ids
        """
        
        # Default parameter ranges based on successful test
        default_ranges = {
            'tbias': tbias_range if tbias_range is not None else [-9.0, -7.5, -6.0, -4.5, -3.0],
            'kp': kp_range if kp_range is not None else [1.0, 2.5, 4.0, 5.5, 7.0], 
            'ddfsnow': ddfsnow_range if ddfsnow_range is not None else [0.003, 0.005, 0.007, 0.009],
            'ddfsnow_iceratio': ddfsnow_iceratio_range if ddfsnow_iceratio_range is not None else [0.4, 0.6, 0.8, 1.0]
        }
        
        # Add any additional parameters from kwargs
        for key, value in kwargs.items():
            if isinstance(value, list):
                default_ranges[key] = value
        
        # Create parameter grid using meshgrid
        param_names = list(default_ranges.keys())
        param_values = list(default_ranges.values())
        
        # Create all combinations
        combinations = np.meshgrid(*param_values, indexing='ij')
        combinations_flat = [combo.ravel() for combo in combinations]
        
        # Create DataFrame
        param_data = {}
        for i, param_name in enumerate(param_names):
            param_data[param_name] = combinations_flat[i]
        
        param_df = pd.DataFrame(param_data)
        param_df['run_id'] = range(len(param_df))
        
        # Log parameter space info
        total_combinations = len(param_df)
        self.log(f"Parameter space created: {total_combinations} combinations")
        for param, values in default_ranges.items():
            self.log(f"  {param}: {len(values)} values ({min(values)} to {max(values)})")
        
        return param_df
    
    def verify_pygem_outputs(self, run_id: int) -> bool:
        """
        Verify that PyGEM simulation produced valid output files
        
        Parameters:
        -----------
        run_id : int
            Run identifier
            
        Returns:
        --------
        bool : True if valid outputs exist
        """
        
        # Expected output locations
        output_base = self.base_dir / "data" / "Output" / "simulations" / "01" / "ACCESS-CM2" / "ssp245"
        stats_dir = output_base / "stats"
        binned_dir = output_base / "binned"
        
        # Look for files with run identifier
        run_suffix = f"_cmd{run_id:04d}"
        
        stats_files = list(stats_dir.glob(f"*{run_suffix}all.nc")) if stats_dir.exists() else []
        binned_files = list(binned_dir.glob(f"*{run_suffix}binned.nc")) if binned_dir.exists() else []
        
        # Check file existence and minimum size
        valid_files = 0
        for file_list, file_type in [(stats_files, "stats"), (binned_files, "binned")]:
            for file_path in file_list:
                if file_path.exists() and file_path.stat().st_size > 1024:  # > 1KB
                    valid_files += 1
                    self.log(f"Valid {file_type} file found: {file_path.name}", run_id)
                else:
                    self.log(f"Invalid {file_type} file: {file_path}", run_id)
        
        # Require both files if collecting binned, otherwise just stats
        required_files = 2 if self.collect_binned else 1
        return valid_files >= required_files
    
    def copy_pygem_outputs(self, run_id: int, parameters: Dict[str, float]) -> bool:
        """
        Copy PyGEM output files to results directory
        
        Parameters:
        -----------
        run_id : int
            Run identifier
        parameters : Dict[str, float]
            Parameter values for this run
            
        Returns:
        --------
        bool : True if copy successful
        """
        
        run_dir = self.results_dir / f"run_{run_id:04d}"
        run_dir.mkdir(exist_ok=True)
        
        # Source directories
        output_base = self.base_dir / "data" / "Output" / "simulations" / "01" / "ACCESS-CM2" / "ssp245"
        stats_dir = output_base / "stats"
        binned_dir = output_base / "binned"
        
        run_suffix = f"_cmd{run_id:04d}"
        copied_files = 0
        
        # Copy stats files with today's timestamp
        if stats_dir.exists():
            for stats_file in stats_dir.glob(f"*{run_suffix}all.nc"):
                file_mod_time = stats_file.stat().st_mtime
                import time
                today = time.time() - 24*3600  # Within last 24 hours
                
                if file_mod_time > today:
                    dest_file = run_dir / stats_file.name
                    try:
                        shutil.copy2(stats_file, dest_file)
                        if dest_file.stat().st_size == stats_file.stat().st_size:
                            copied_files += 1
                            self.log(f"Copied stats file: {stats_file.name}", run_id)
                    except Exception as e:
                        self.log(f"Failed to copy stats file {stats_file}: {e}", run_id)
        
        # Copy binned files with today's timestamp (if requested)
        if self.collect_binned and binned_dir.exists():
            for binned_file in binned_dir.glob(f"*{run_suffix}binned.nc"):
                file_mod_time = binned_file.stat().st_mtime
                import time
                today = time.time() - 24*3600  # Within last 24 hours
                
                if file_mod_time > today:
                    dest_file = run_dir / binned_file.name
                    try:
                        shutil.copy2(binned_file, dest_file)
                        if dest_file.stat().st_size == binned_file.stat().st_size:
                            copied_files += 1
                            self.log(f"Copied binned file: {binned_file.name}", run_id)
                    except Exception as e:
                        self.log(f"Failed to copy binned file {binned_file}: {e}", run_id)
        elif not self.collect_binned:
            self.log(f"Skipping binned files (collect_binned=False)", run_id)
        
        # Save parameter info as JSON for easy access
        with open(run_dir / "parameters.json", 'w') as f:
            json.dump(parameters, f, indent=2)
        
        # Require both files if collecting binned, otherwise just stats
        required_files = 2 if self.collect_binned else 1
        return copied_files >= required_files
    
    def clean_partial_outputs(self, run_id: int):
        """
        Clean partial outputs from failed attempts
        
        Parameters:
        -----------
        run_id : int
            Run identifier
        """
        
        output_base = self.base_dir / "data" / "Output" / "simulations" / "01" / "ACCESS-CM2" / "ssp245"
        run_suffix = f"_cmd{run_id:04d}"
        
        # Clean stats and binned directories
        for subdir in ['stats', 'binned']:
            dir_path = output_base / subdir
            if dir_path.exists():
                for partial_file in dir_path.glob(f"*{run_suffix}*"):
                    try:
                        partial_file.unlink()
                        self.log(f"Cleaned partial file: {partial_file}", run_id)
                    except Exception as e:
                        self.log(f"Failed to clean {partial_file}: {e}", run_id)
    
    def execute_single_run(self, run_id: int, parameters: Dict[str, float], max_retries: int = 3) -> Dict[str, Any]:
        """
        Execute single parameter combination with retry mechanism
        
        Parameters:
        -----------
        run_id : int
            Unique run identifier
        parameters : Dict[str, float]
            Parameter values for this run
        max_retries : int
            Maximum retry attempts
            
        Returns:
        --------
        Dict[str, Any] : Run result information
        """
        
        start_time = time.time()
        
        # Initialize run info
        run_info = {
            'run_id': run_id,
            'status': 'started',
            'parameters': parameters.copy(),
            'timestamp': datetime.now().isoformat(),
            'attempts': 0,
            'total_runtime': 0
        }
        
        # Create result directory
        run_dir = self.results_dir / f"run_{run_id:04d}"
        run_dir.mkdir(exist_ok=True)
        
        for attempt in range(max_retries + 1):
            attempt_start = time.time()
            run_info['attempts'] = attempt + 1
            
            try:
                self.log(f"Starting attempt {attempt + 1}/{max_retries + 1}", run_id)
                
                # Clean any partial outputs from previous attempts
                if attempt > 0:
                    self.clean_partial_outputs(run_id)
                    time.sleep(2)  # Brief pause between retries
                
                # Build command with command-line parameters only
                cmd = [
                    sys.executable,
                    str(self.pygem_script),
                    '-rgi_glac_number', '1.20947',
                    '-sim_startyear', '2015',
                    '-sim_endyear', '2100',  # Full simulation
                    '-kp', str(parameters.get('kp', 1.0)),
                    '-tbias', str(parameters.get('tbias', -6.0)),
                    '-ddfsnow', str(parameters.get('ddfsnow', 0.005)),
                    '-ddfsnow_iceratio', str(parameters.get('ddfsnow_iceratio', 0.6)),
                    '-export_extra_vars',  # Export additional variables
                    '-outputfn_sfix', f'_cmd{run_id:04d}'
                    # NOTE: Removed -v flag to prevent figure creation issues
                ]
                
                # Add binned data export if requested
                if self.collect_binned:
                    cmd.insert(-2, '-export_binned_data')  # Insert before -outputfn_sfix
                
                self.log(f"Executing: {' '.join(cmd[-6:])}", run_id)  # Log only key parameters
                
                # Set environment variables to prevent figure display
                env = os.environ.copy()
                env['MPLBACKEND'] = 'Agg'  # Use non-interactive backend
                env['DISPLAY'] = ''  # Disable display
                
                result = subprocess.run(
                    cmd,
                    cwd=self.base_dir,
                    capture_output=True,
                    text=True,
                    timeout=1800,  # 30 minute timeout
                    env=env
                )
                
                attempt_runtime = time.time() - attempt_start
                
                if result.returncode == 0:
                    self.log(f"Simulation completed successfully in {attempt_runtime:.1f}s", run_id)
                    
                    # Verify outputs exist
                    if self.verify_pygem_outputs(run_id):
                        # Copy outputs to results directory
                        if self.copy_pygem_outputs(run_id, parameters):
                            run_info['status'] = 'completed'
                            run_info['total_runtime'] = time.time() - start_time
                            self.log(f"Run completed successfully on attempt {attempt + 1}", run_id)
                            break
                        else:
                            self.log(f"Failed to copy outputs on attempt {attempt + 1}", run_id)
                    else:
                        self.log(f"Output verification failed on attempt {attempt + 1}", run_id)
                else:
                    self.log(f"PyGEM failed (exit code {result.returncode}) on attempt {attempt + 1}: {result.stderr[:200]}", run_id)
            
            except subprocess.TimeoutExpired:
                self.log(f"Simulation timed out on attempt {attempt + 1}", run_id)
            except Exception as e:
                self.log(f"Exception on attempt {attempt + 1}: {str(e)}", run_id)
            
            # If we reach here, the attempt failed
            if attempt < max_retries:
                self.log(f"Attempt {attempt + 1} failed, retrying...", run_id)
                time.sleep(5)  # Wait before retry
            else:
                run_info['status'] = 'failed'
                run_info['total_runtime'] = time.time() - start_time
                self.log(f"All {max_retries + 1} attempts failed", run_id)
        
        # Save run info
        with open(run_dir / 'run_info.json', 'w') as f:
            json.dump(run_info, f, indent=2)
        
        return run_info
    
    def run_parameter_sweep(self, parameter_df: pd.DataFrame, 
                           start_run: int = 0, 
                           max_runs: Optional[int] = None,
                           progress_interval: int = 10) -> List[Dict[str, Any]]:
        """
        Execute full parameter sweep in serial
        
        Parameters:
        -----------
        parameter_df : pd.DataFrame
            DataFrame containing parameter combinations
        start_run : int
            Starting run ID (for resuming)
        max_runs : Optional[int]
            Maximum number of runs to execute (for testing)
        progress_interval : int
            Progress reporting interval
            
        Returns:
        --------
        List[Dict[str, Any]] : Results from all runs
        """
        
        # Determine runs to execute
        total_runs = len(parameter_df)
        if max_runs is not None:
            total_runs = min(total_runs, start_run + max_runs)
        
        self.log(f"Starting command-line parameter sweep: {total_runs - start_run} runs ({start_run} to {total_runs - 1})")
        self.log(f"Results directory: {self.results_dir}")
        self.log("=" * 60)
        
        results = []
        successful_runs = 0
        
        for i in range(start_run, total_runs):
            run_start_time = time.time()
            
            # Get parameters for this run
            params = parameter_df.iloc[i].to_dict()
            run_id = int(params.pop('run_id'))  # Remove run_id from parameters and convert to int
            
            self.log(f"Starting run {run_id:04d} ({i + 1 - start_run}/{total_runs - start_run})")
            self.log(f"Parameters: {params}", run_id)
            
            # Execute run
            result = self.execute_single_run(run_id, params)
            results.append(result)
            
            if result['status'] == 'completed':
                successful_runs += 1
            
            run_time = time.time() - run_start_time
            
            # Progress reporting
            if (i + 1) % progress_interval == 0:
                success_rate = successful_runs / len(results) * 100
                avg_runtime = sum(r.get('total_runtime', 0) for r in results) / len(results)
                self.log(f"Progress: {len(results)} runs completed, {successful_runs} successful ({success_rate:.1f}%)")
                self.log(f"Average runtime: {avg_runtime:.1f}s")
                self.log("-" * 40)
        
        # Final summary
        final_success_rate = successful_runs / len(results) * 100 if results else 0
        total_runtime = sum(r.get('total_runtime', 0) for r in results)
        
        self.log("=" * 60)
        self.log("COMMAND-LINE PARAMETER SWEEP COMPLETE")
        self.log(f"Total runs: {len(results)}")
        self.log(f"Successful: {successful_runs} ({final_success_rate:.1f}%)")
        self.log(f"Failed: {len(results) - successful_runs}")
        self.log(f"Total runtime: {total_runtime / 3600:.1f} hours")
        self.log(f"Average per run: {total_runtime / len(results):.1f}s")
        
        return results

    def test_setup(self, n_test: int = 5) -> List[Dict[str, Any]]:
        """
        Test setup with small parameter combinations
        
        Parameters:
        -----------
        n_test : int
            Number of test runs
            
        Returns:
        --------
        List[Dict[str, Any]] : Test results
        """
        
        self.log(f"Testing command-line parameter sweep with {n_test} runs")
        
        # Create small test parameter space
        test_params = self.create_parameter_combinations(
            tbias_range=[-8.0, -6.0],
            kp_range=[3.0, 5.0], 
            ddfsnow_range=[0.005, 0.007],
            ddfsnow_iceratio_range=[0.6, 0.8]
        )
        
        # Run test subset
        test_results = self.run_parameter_sweep(test_params, max_runs=n_test)
        
        # Test summary
        successful = sum(1 for r in test_results if r['status'] == 'completed')
        self.log(f"Test completed: {successful}/{n_test} runs successful")
        
        if successful > 0:
            self.log("Test PASSED - Command-line parameter sweep working!")
        else:
            self.log("Test FAILED - Check logs for issues")
        
        return test_results

def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Command-Line Parameter Sweep for PyGEM (No Config Files)')
    parser.add_argument('--test', type=int, default=0, metavar='N',
                        help='Run test with N parameter combinations (default: 0 = no test)')
    parser.add_argument('--small', action='store_true',
                        help='Run small parameter sweep (~80 combinations)')
    parser.add_argument('--medium', action='store_true', 
                        help='Run medium parameter sweep (~400 combinations)')
    parser.add_argument('--large', action='store_true',
                        help='Run large parameter sweep (~1600 combinations)')
    parser.add_argument('--output-dir', type=str,
                        help='Custom output directory')
    parser.add_argument('--start-run', type=int, default=0,
                        help='Starting run ID for resuming')
    parser.add_argument('--max-runs', type=int,
                        help='Maximum runs to execute')
    parser.add_argument(
        '--collect-binned', '--collect-bend', '--collect_binned',
        dest='collect_binned',
        action='store_true',
        help='Collect binned files in addition to stats files (aliases: --collect-bend, --collect_binned)'
    )
    
    args = parser.parse_args()
    
    # Initialize parameter sweep
    sweep = CommandLineParameterSweep(
        output_dir=args.output_dir, 
        collect_binned=args.collect_binned
    )
    
    if args.test > 0:
        # Run test
        sweep.test_setup(n_test=args.test)
    
    elif args.small:
        # Small parameter sweep
        params = sweep.create_parameter_combinations(
            tbias_range=[-8.0, -6.0, -4.0, -2.0],
            kp_range=[2.0, 4.0, 6.0],
            ddfsnow_range=[0.004, 0.006, 0.008],
            ddfsnow_iceratio_range=[0.5, 0.7, 0.9]
        )
        sweep.run_parameter_sweep(params, start_run=args.start_run, max_runs=args.max_runs)
    
    elif args.medium:
        # Medium parameter sweep  
        params = sweep.create_parameter_combinations(
            tbias_range=np.linspace(-9.0, -3.0, 7),
            kp_range=np.linspace(2.0, 6.0, 5),
            ddfsnow_range=np.linspace(0.003, 0.009, 7),
            ddfsnow_iceratio_range=[0.4, 0.6, 0.8, 1.0]
        )
        sweep.run_parameter_sweep(params, start_run=args.start_run, max_runs=args.max_runs)
    
    elif args.large:
        # Large parameter sweep
        params = sweep.create_parameter_combinations(
            tbias_range=np.linspace(-9.0, -3.0, 10),
            kp_range=np.linspace(1.0, 7.0, 8),
            ddfsnow_range=np.logspace(np.log10(0.003), np.log10(0.010), 10),
            ddfsnow_iceratio_range=np.linspace(0.4, 1.0, 5)
        )
        sweep.run_parameter_sweep(params, start_run=args.start_run, max_runs=args.max_runs)
    
    else:
        print("Please specify a sweep type:")
        print("  --test N       : Test with N runs")
        print("  --small        : Small sweep (~80 runs)")
        print("  --medium       : Medium sweep (~400 runs)")
        print("  --large        : Large sweep (~1600 runs)")
        print("\nUse --help for more options")

if __name__ == "__main__":
    main()