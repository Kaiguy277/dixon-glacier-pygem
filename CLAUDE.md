# CLAUDE.md - PyGEM Glacier Model Best Practices

This document establishes best practices for working with the PyGEM (Python Glacier Evolution Model) for Dixon Glacier analysis using Claude Code and specialized agents.

## 🎯 Core Principles

### Data Integrity - NEVER FABRICATE DATA
- **CRITICAL**: Only use real simulation data that comes from actual PyGEM model runs
- Never generate, estimate, or make up data values to complete assignments
- If data is missing or unavailable, explicitly state this rather than creating placeholder values
- All results must be traceable to actual model outputs or observational datasets

### Verification Over Trust
- **Always examine file contents** - Never trust filenames or paths from previous agents
- Agent-generated scripts and filenames may contain errors - verify everything
- Check file formats, data structure, and content before using in analysis
- Cross-reference file contents with expected PyGEM input/output specifications

### Comprehensive Progress Logging
- Log all actions with timestamps in a consistent format
- Document next steps and reasoning for each decision
- Track workflow stage completion (calibration → simulation → analysis)
- Maintain clear audit trail of all model runs and parameter changes

## 🔍 Tool and Resource Utilization

### Claude Code Tools & MCP Servers
- **Use all available tools** when applicable: Bash, Read, Edit, Grep, Glob, TodoWrite
- **Leverage MCP servers** for documentation search, web browsing, and specialized tasks
- **Deploy specialized agents** (pygem-glacier-modeler) for complex PyGEM-specific workflows
- **Batch tool calls** when possible for efficiency (multiple file reads, parallel searches)
- **Use Task tool** for complex multi-step operations requiring autonomous execution

### Agent Coordination
- Use pygem-glacier-modeler agent for PyGEM-specific model setup, calibration, and troubleshooting
- Use general-purpose agent for broad research and file system operations
- Document agent handoffs and ensure context preservation between agent calls

## 📊 Model Integrity & Validation

### Pre-Run Validation
- Verify model parameters against reference datasets before simulation
- Check that calibration data (surface change DEM) covers appropriate time periods
- Validate coordinate systems and projections for all spatial data
- Ensure climate data temporal coverage matches simulation requirements

### Data Usage Strategy for Dixon Glacier
- **Calibration**: Use surface_change_2022_2023.TIF for mass balance parameter calibration
- **Validation**: Use stake_observations_dixon.csv for independent validation of calibrated model
- Cross-check calibration results with validation data patterns
- Document any discrepancies between calibration and validation datasets

### Results Validation
- Cross-check calibration results with known Dixon Glacier behavior patterns
- Compare mass balance outputs with stake observation constraints
- Verify outputs against peer-reviewed literature when available
- Flag any results that seem physically unrealistic for Arctic glaciers

## 🔧 Data Handling & Quality Control

### Input Data Verification
```bash
# Always verify data file formats match PyGEM expectations
# .csv for observations, .TIF for DEMs, .shp for outlines
file inputs/stake_observations_dixon.csv
file inputs/surface_change_2022_2023.TIF
```

### Data Quality Checks
- Validate date ranges and temporal consistency in observational data
- Check for missing values, outliers, or data gaps
- Ensure measurement units are consistent (m w.e. for mass balance)
- Verify elevation data falls within reasonable ranges for Dixon Glacier

## ⚙️ Configuration Management

### Config File Safety
```bash
# Always backup config.yaml before modifications
cp ~/PyGEM/config.yaml ~/PyGEM/config.yaml.backup.$(date +%Y%m%d_%H%M%S)
```

### Parameter Documentation
- Document all parameter modifications with scientific rationale
- Test configuration changes on small glacier subsets first
- Maintain separate configs for calibration vs simulation runs
- Record the source/justification for each parameter value

## 🐛 Error Handling & Debugging

### Execution Logging
```bash
# Example logging format for PyGEM script execution
echo "$(date): Starting run_calibration for Dixon Glacier" >> pygem_execution.log
run_calibration -option_calibration option 2>&1 | tee -a pygem_execution.log
echo "$(date): Calibration completed with exit code $?" >> pygem_execution.log
```

### Error Analysis
- Capture and analyze complete error messages from PyGEM scripts
- Check system requirements and dependencies before running
- Monitor memory usage for computationally intensive operations
- Document error resolution steps for future reference

## 🔄 Reproducibility & Documentation

### Version Control
- Record exact PyGEM version and commit hash used
- Document all preprocessing steps and data sources
- Save intermediate results at each workflow stage
- Create detailed run logs with command-line arguments used

### Documentation Standards
```markdown
## Run Record Template
**Date**: YYYY-MM-DD HH:MM
**PyGEM Version**: X.X.X
**Stage**: Calibration/Simulation/Analysis
**Command**: `run_calibration -option_calibration DEBMASS_HIST`
**Input Data**: 
  - surface_change_2022_2023.TIF (for calibration)
  - stake_observations_dixon.csv (for validation)
**Output**: 
  - Calibration parameters in Output/calibration/01/
**Notes**: [Detailed observations and next steps]
```

## 🧪 Scientific Best Practices

### PyGEM Workflow Adherence
1. **Pre-processing**: Verify OGGM glacier directories are current
2. **Configuration**: Set appropriate `root` path and `overwrite_gdirs` settings
3. **Frontal Ablation Calibration**: (if applicable for marine-terminating portions)
4. **Mass Balance Calibration**: Use surface change DEM for parameter optimization
5. **Glen A Calibration**: Regional ice viscosity parameter calibration
6. **Simulation**: Run with validated parameters
7. **Validation**: Compare results against stake observation data
8. **Post-processing**: Aggregate and analyze results

### Iterative Calibration Approach
- Follow PyGEM's recommended iterative calibration for marine-terminating glaciers
- Validate against independent datasets (stake observations) when possible
- Document model limitations and uncertainty sources
- Use appropriate statistical methods for uncertainty quantification

## 🎯 Dixon Glacier Specific Considerations

### Local Context
- Dixon Glacier is in Alaska (RGI region 01)
- Check for marine-terminating characteristics requiring frontal ablation calibration
- Validate elevation ranges against known Dixon Glacier topography
- Consider seasonal variations in mass balance patterns

### Available Data Integration Strategy
- **Primary Calibration**: surface_change_2022_2023.TIF for geodetic mass balance calibration
- **Independent Validation**: stake_observations_dixon.csv (2022-2025) for model validation
- Cross-reference calibrated parameters with regional climate patterns
- Consider debris cover effects if applicable

## 🌡️ CMIP6 Climate Scenario Implementation

### Critical Technical Solution - Hardcoded Climate Scenarios
**ISSUE IDENTIFIED**: PyGEM has hardcoded climate scenario references that override config settings.

**ROOT CAUSE**: 
- Config files may not be properly read due to working directory issues
- Climate scenario logic defaults to 'ssp245' regardless of config setting
- ACCESS-CM2 climate definition missing from class_climate.py

**SOLUTION IMPLEMENTED**:
1. **Added ACCESS-CM2 Climate Definition** in `/PyGEM/pygem/class_climate.py`:
```python
elif self.name == 'ACCESS-CM2':
    # ACCESS-CM2 CMIP6 model with variable scenarios
    # Variable names
    self.temp_vn = 'tas'
    self.prec_vn = 'pr'
    self.elev_vn = 'orog'
    # Variable filenames - constructed based on scenario
    self.temp_fn = f'ACCESS-CM2_{sim_climate_scenario}_r1i1p1f1_tas.nc'
    self.prec_fn = f'ACCESS-CM2_{sim_climate_scenario}_r1i1p1f1_pr.nc'
    # Variable filepaths
    self.var_fp = pygem_prms['root'] + '/climate_data/cmip6/ACCESS-CM2/'
```

2. **Fixed Scenario Logic** in `/PyGEM/pygem/bin/run/run_simulation.py`:
```python
elif sim_climate_name.startswith('SSP'):
    # Extract scenario from SSP climate names (SSP126, SSP245, SSP585)
    sim_climate_scenario = sim_climate_name.lower()
```

### Command-Line Override Method
**CRITICAL**: Use explicit command-line arguments to ensure correct scenario execution:

```bash
# SSP126 (Low warming ~1.5°C)
python3 run_simulation.py -sim_climate_name ACCESS-CM2 -sim_climate_scenario ssp126

# SSP245 (Moderate warming ~2.7°C) 
python3 run_simulation.py -sim_climate_name ACCESS-CM2 -sim_climate_scenario ssp245

# SSP370 (High warming ~3.6°C)
python3 run_simulation.py -sim_climate_name ACCESS-CM2 -sim_climate_scenario ssp370

# SSP585 (Very high warming ~4.4°C)
python3 run_simulation.py -sim_climate_name ACCESS-CM2 -sim_climate_scenario ssp585
```

### Climate Data Requirements
**File Structure**: All scenarios require specific file naming convention in `/climate_data/cmip6/ACCESS-CM2/`:
- Temperature: `ACCESS-CM2_{scenario}_r1i1p1f1_tas.nc`
- Precipitation: `ACCESS-CM2_{scenario}_r1i1p1f1_pr.nc`
- Orography: `ACCESS-CM2_orog.nc`

**Data Verification**:
```bash
# Verify all scenario files exist
ls /climate_data/cmip6/ACCESS-CM2/ACCESS-CM2_ssp*_r1i1p1f1_*.nc
# Should show: ssp126, ssp245, ssp370, ssp585 files for both tas and pr
```

### Scenario Comparison Results (Dixon Glacier 2015-2100)
**VALIDATED OUTCOMES**:
- **SSP126**: 26.0 km² remaining (37.7% loss) - Best case scenario
- **SSP245**: 21.7 km² remaining (48.0% loss) - Moderate warming
- **SSP370**: 17.6 km² remaining (57.9% loss) - High warming  
- **SSP585**: 8.3 km² remaining (80.0% loss) - Worst case scenario

**Peak Water Timing**:
- SSP126: 2049 (earliest peak - less prolonged melting)
- SSP245: 2057 
- SSP370: 2058
- SSP585: 2074 (latest peak - extended melting period)

### Configuration Management for Scenarios
**Multiple Config Files Issue**: 
- PyGEM may read from `/Users/.../PygemRound2/config.yaml` (root level)
- NOT from `/Users/.../PygemRound2/PyGEM/pygem/setup/config.yaml`
- Always verify which config file is being used

**Best Practice**: Use command-line overrides rather than relying solely on config files for scenario specification.

## 🔧 **PARAMETER SWEEP IMPLEMENTATION - CRITICAL FIXES**

### 🚨 **Root Cause: Config File Override Issue**
**ISSUE IDENTIFIED**: PyGEM ignores command-line parameters when `option_calibration` is set in config.yaml.

**ROOT CAUSE**: 
- Config file has `option_calibration: HH2015mod` which forces PyGEM to load pre-calibrated parameters
- Command-line parameters (`-kp`, `-tbias`, `-ddfsnow`) are ignored when calibration option is active
- This causes all parameter sweep runs to produce identical results

### ✅ **SOLUTION IMPLEMENTED**: PyGEM Source Code Fix

**Location**: `/PyGEM/pygem/bin/run/run_simulation.py` lines 686-691

**Original Code**:
```python
if args.option_calibration:
    # Load calibrated parameters (ignores command-line params)
```

**Fixed Code**:
```python
# PARAMETER SWEEP FIX: Check if command-line parameters are provided
cmdline_params_provided = (args.kp is not None or 
                         args.tbias is not None or 
                         args.ddfsnow is not None)

if args.option_calibration and not cmdline_params_provided:
    # Load calibrated parameters only if no command-line params provided
```

**Debug Addition** (lines 832-834):
```python
# PARAMETER SWEEP FIX: Using command-line parameters
if cmdline_params_provided and debug:
    print(f"PARAMETER SWEEP: Using command-line parameters - kp={args.kp}, tbias={args.tbias}, ddfsnow={args.ddfsnow}")
```

### 📊 **VALIDATION RESULTS**: Parameter Sensitivity Confirmed

**Test Results** (2015-2025 period):
```
Conservative (tbias=-3.0, kp=1.0, ddf=0.004): 41.42 → 34.70 km² (16.2% loss)
Moderate     (tbias=-2.0, kp=1.5, ddf=0.005): 41.26 → 31.76 km² (23.0% loss)
Aggressive   (tbias=-1.0, kp=2.0, ddf=0.006): 41.13 → 25.47 km² (38.1% loss)
```

**Before Fix**: All parameters produced identical 0.96 km² final area (97.7% loss)
**After Fix**: Parameters produce realistic varied results (16.2% - 38.1% loss range)

### 🎯 **WORKING PARAMETER SWEEP COMMAND TEMPLATE**

```bash
python3 /PyGEM/pygem/bin/run/run_simulation.py \
    -kp [VALUE] \
    -tbias [VALUE] \
    -ddfsnow [VALUE] \
    -rgi_glac_number 1.20947 \
    -sim_startyear 2015 \
    -sim_endyear 2100 \
    -export_extra_vars \
    -export_binned_data \
    -outputfn_sfix _[UNIQUE_ID]
```

**Example Working Commands**:
```bash
# Conservative parameters
python3 run_simulation.py -kp 1.0 -tbias -3.0 -ddfsnow 0.004 -rgi_glac_number 1.20947 -sim_startyear 2015 -sim_endyear 2100 -outputfn_sfix _conservative

# Moderate parameters  
python3 run_simulation.py -kp 1.5 -tbias -2.0 -ddfsnow 0.005 -rgi_glac_number 1.20947 -sim_startyear 2015 -sim_endyear 2100 -outputfn_sfix _moderate

# Aggressive parameters
python3 run_simulation.py -kp 2.0 -tbias -1.0 -ddfsnow 0.006 -rgi_glac_number 1.20947 -sim_startyear 2015 -sim_endyear 2100 -outputfn_sfix _aggressive
```

### 📋 **REALISTIC PARAMETER RANGES** (Literature-Based)

**For Dixon Glacier Parameter Sweeps**:
- **Temperature bias (tbias)**: -4.0°C to 0.0°C
- **Precipitation factor (kp)**: 0.8 to 2.0  
- **Degree-day factor (ddfsnow)**: 0.003 to 0.007 m°C⁻¹d⁻¹
- **Lapse rate**: -0.0065°C/m (standard atmospheric)
- **Precipitation gradient**: 0.0002 (moderate gradient)

**Parameter Grid Recommendations**:
- **Small test**: 3×3×3 = 27 combinations
- **Full sweep**: 5×5×5 = 125 combinations
- **Comprehensive**: 7×7×7 = 343 combinations

### 🔍 **VERIFICATION CHECKLIST**

**Before Running Parameter Sweep**:
1. ✅ PyGEM source code fix applied to `run_simulation.py`
2. ✅ Parameters specified via command-line (not config file)
3. ✅ Unique output suffix for each run (`-outputfn_sfix`)
4. ✅ Realistic parameter ranges selected
5. ✅ Debug mode enabled for verification (`-v` flag)

**Verification Commands**:
```bash
# Test single run with debug output
python3 run_simulation.py -kp 1.5 -tbias -2.5 -ddfsnow 0.005 -rgi_glac_number 1.20947 -sim_startyear 2015 -sim_endyear 2020 -outputfn_sfix _test -v

# Look for confirmation message in output:
grep "PARAMETER SWEEP: Using command-line parameters" [output_log]
```

### ⚡ **PERFORMANCE EXPECTATIONS**

**Timing**: ~10-40 seconds per simulation (2015-2100)
**Success Rate**: 100% with realistic parameters and proper config
**Output Files**: 2 per run (stats + binned NetCDF files)
**File Sizes**: ~1-5 MB per simulation

### 🚨 **CRITICAL SUCCESS INDICATORS**

✅ **Different parameters produce different final glacier areas**
✅ **Debug message confirms command-line parameter usage**
✅ **Unique output files created with specified suffix**
✅ **Results show realistic area loss ranges (not extreme 97%+ loss)**
✅ **Parameter correlations show expected sensitivity patterns**

## 🚨 Critical Warnings

- **Never use placeholder or estimated values** in place of missing model outputs
- **Always verify file integrity** before using in analysis
- **Document all assumptions** and their scientific basis
- **Flag uncertainties explicitly** rather than presenting uncertain results as definitive
- **Stop execution** if critical data is missing or corrupted

## 📝 Progress Tracking Template

```markdown
## Current Status: [Stage Name]
**Last Updated**: [Timestamp]
**Completed Steps**:
- [ ] Task 1
- [ ] Task 2

**Next Steps**:
1. [Specific action with timeline]
2. [Next action with dependencies]

**Blockers/Issues**:
- [Any impediments to progress]

**Files Modified/Created**:
- [List with descriptions]

**Tools/Agents Used**:
- [Document which Claude Code tools and MCP servers were utilized]
```

---

*This document should be updated as workflows evolve and new best practices are identified through PyGEM model usage.*