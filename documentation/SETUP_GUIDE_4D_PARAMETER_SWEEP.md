# Complete Setup Guide: 4D Command-Line Parameter Sweep for PyGEM
## Dixon Glacier Analysis Framework

**Date**: January 2026
**Status**: Production-Ready
**Success Rate**: 96.3% on 4D parameter sweeps

---

## Table of Contents

1. [Overview](#overview)
2. [Critical Breakthrough](#critical-breakthrough)
3. [Data Requirements](#data-requirements)
4. [PyGEM Source Code Modifications](#pygem-source-code-modifications)
5. [Parameter Sweep Framework](#parameter-sweep-framework)
6. [Configuration](#configuration)
7. [Usage Guide](#usage-guide)
8. [Data Sources Documentation](#data-sources-documentation)
9. [Troubleshooting](#troubleshooting)

---

## Overview

This setup enables large-scale parameter sweeps for Dixon Glacier (RGI 1.20947) using PyGEM with **direct command-line parameter control**, bypassing all configuration file issues that plagued earlier attempts.

### Key Features
- ✅ **4D parameter space**: tbias, kp, ddfsnow, ddfsnow_iceratio
- ✅ **96.3%+ success rate** on production runs
- ✅ **Serial execution** with retry mechanism
- ✅ **No config file dependencies** - all parameters via command-line
- ✅ **Proven at scale**: Validated on 5000+ run sweeps

### Performance Metrics
- **Speed**: 6-8 seconds per simulation (2015-2100)
- **Success Rate**: 94.5-96.3% (single worker)
- **Scale**: Tested up to 24,000 successful runs
- **Output**: 2 NetCDF files per run (stats + binned elevation data)

---

## Critical Breakthrough

### The Problem
Early parameter sweep attempts faced a fundamental issue: **PyGEM ignored command-line parameters when `option_calibration` was set in config.yaml**, causing all runs to produce identical results regardless of input parameters.

### The Solution
Three critical modifications to PyGEM source code:

1. **Added `ddfsnow_iceratio` command-line argument**
2. **Fixed parameter detection logic** to recognize command-line overrides
3. **Updated `ddfice` calculation** to use command-line values

This enables **complete parameter control** without touching configuration files.

---

## Data Requirements

### 1. Glacier Outline (RGI)
**Location**: `/inputs/RGI60-01.20947/`

**Files**:
```
outlines.shp          # Glacier polygon shapefile (primary)
outlines.dbf          # Attribute database
outlines.shx          # Shapefile index
outlines.prj          # Projection information (WGS84)
outlines.cpg          # Character encoding
```

**Source**: Randolph Glacier Inventory 6.0
**Glacier ID**: RGI60-01.20947 (Dixon Glacier)
**Region**: Alaska (Region 01)
**Area**: ~41.7 km² (2015)
**Coordinates**: 60.1°N, 142.8°W

**Download**: https://www.glims.org/RGI/ (RGI 6.0 Alaska region)

---

### 2. Ice Thickness Data
**Location**: `/inputs/thickness/`

**Files**:
```
RGI60-01.20947_thickness.tif          # Ice thickness raster (264 KB)
RGI60-01.20947_thickness.tif.aux.xml  # Auxiliary metadata
```

**Source**: Farinotti et al. (2019) consensus ice thickness estimates
**Resolution**: ~100m spatial resolution
**Units**: meters (ice thickness)
**Method**: Multi-model consensus estimate combining multiple ice thickness reconstruction approaches

**Reference**: Farinotti, D., Huss, M., Fürst, J. J., et al. (2019). A consensus estimate for the ice thickness distribution of all glaciers on Earth. *Nature Geoscience*, 12(3), 168-173.

**Download**: Available through OGGM (Open Global Glacier Model) infrastructure
**OGGM URL**: https://cluster.klima.uni-bremen.de/~oggm/gdirs/oggm_v1.6/

---

### 3. Surface Change DEM (Calibration Data)
**Location**: `/inputs/surface_change_2022_2023.TIF`

**Details**:
- **File Size**: 398 MB (high-resolution GeoTIFF)
- **Period**: October 13, 2022 → September 19, 2023
- **Method**: LiDAR-SfM differencing
- **Average Change**: -0.880 m over 341 days
- **Mass Balance**: -0.79 m w.e. ± 0.3 m w.e.
- **Purpose**: Used for PyGEM mass balance parameter calibration

**Source**: Field measurements and photogrammetry (Dixon Glacier field campaign)
**Coordinate System**: Alaska Albers (EPSG:3338)
**Vertical Datum**: NAVD88

---

### 4. Stake Observations (Validation Data)
**Location**: `/inputs/stake_observations_dixon.csv`

**Content**: Point mass balance measurements at three elevation zones

| Site | Elevation | Zone | Observations |
|------|-----------|------|--------------|
| ABL  | 804 m     | Ablation | 2023-2025 (annual, winter, summer) |
| ELA  | 1078 m    | Equilibrium | 2023-2025 (annual, winter, summer) |
| ACC  | 1293 m    | Accumulation | 2023-2025 (annual, winter, summer) |

**Data Structure**:
```csv
site_id,period_type,year,date_start,date_end,mb_obs_mwe,mb_obs_uncertainty_mwe,zone,elevation_m,notes
ABL,annual,2023,2022-10-01,2023-10-03,-4.5,0.12,ABL,804.0,Annual balance...
```

**Fields**:
- `mb_obs_mwe`: Mass balance in meters water equivalent
- `mb_obs_uncertainty_mwe`: Measurement uncertainty
- `period_type`: annual, winter, summer
- `zone`: ABL (ablation), ELA (equilibrium), ACC (accumulation)

**Source**: Dixon Glacier field measurements (2022-2025)
**Measurement Method**: Stake readings with density measurements
**Notes**: 2025 ACC values estimated using scaled historical gradient method

---

### 5. Climate Data: ERA5 (Historical, 2000-2024)
**Location**: `/inputs/ERA5/`

**Source**: ECMWF ERA5 Reanalysis
**Period**: 2000-2024 (historical reference)
**Temporal Resolution**: Monthly
**Spatial Resolution**: 0.25° × 0.25° (~31 km)

**Variables Used**:
- **Temperature**: 2m air temperature (°C)
- **Precipitation**: Total precipitation (mm/month)
- **Geopotential**: Surface elevation (m)
- **Lapse Rates**: Temperature gradient with elevation (°C/m)
- **Temperature Standard Deviation**: Monthly variability

**Download Method**:
```bash
# Using ECMWF Climate Data Store (CDS) API
# Requires account: https://cds.climate.copernicus.eu/
pip install cdsapi
# Configure ~/.cdsapirc with API credentials
```

**CDS Request Example**:
```python
import cdsapi
c = cdsapi.Client()

c.retrieve('reanalysis-era5-single-levels-monthly-means', {
    'product_type': 'monthly_averaged_reanalysis',
    'variable': ['2m_temperature', 'total_precipitation'],
    'year': ['2000', '2001', ..., '2024'],
    'month': ['01', '02', ..., '12'],
    'time': '00:00',
    'area': [61, -144, 59, -141],  # Dixon Glacier region
    'format': 'netcdf'
}, 'ERA5_climate_data.nc')
```

**Reference**: Hersbach, H., et al. (2020). The ERA5 global reanalysis. *Quarterly Journal of the Royal Meteorological Society*, 146(730), 1999-2049.

---

### 6. Climate Data: ACCESS-CM2 CMIP6 (Future Scenarios, 2015-2100)
**Location**: `/inputs/CMIP6/`

**Model**: ACCESS-CM2 (Australian Community Climate and Earth-System Simulator)
**Project**: CMIP6 (Coupled Model Intercomparison Project Phase 6)
**Institution**: CSIRO-ARCCSS (Australia)
**Period**: 2015-2100
**Temporal Resolution**: Monthly
**Spatial Resolution**: ~250 km (regridded to glacier location)

#### Scenarios Available

**SSP126** - Low warming scenario (~1.5°C by 2100)
**Path**: `/inputs/CMIP6/SSP126_near-surface-air-temp_2015to2100/`
**Path**: `/inputs/CMIP6/SSP126_precip_2015to2100/`

**SSP245** - Moderate warming scenario (~2.7°C by 2100) [DEFAULT]
**Path**: `/inputs/CMIP6/SSP245_near-surface-air-temp_2015to2100/`
**Path**: `/inputs/CMIP6/SSP245_precip_2015to2100/`

**SSP370** - High warming scenario (~3.6°C by 2100)
**Path**: `/inputs/CMIP6/SSP370_near-surface-air-temp_2015to2100/`
**Path**: `/inputs/CMIP6/SSP370_precip_2015to2100/`

**SSP585** - Very high warming scenario (~4.4°C by 2100)
**Path**: `/inputs/CMIP6/SSP585_near-surface-air-temp_2015to2100/`
**Path**: `/inputs/CMIP6/SSP585_precip_2015to2100/`

#### Variables
- **tas**: Near-surface air temperature (K) → converted to °C
- **pr**: Precipitation flux (kg/m²/s) → converted to mm/month
- **orog**: Surface orography/elevation (m)

#### File Naming Convention
```
Temperature: tas_Amon_ACCESS-CM2_ssp245_r1i1p1f1_gn_20150116-21001216.nc
Precipitation: pr_Amon_ACCESS-CM2_ssp245_r1i1p1f1_gn_20150116-21001216.nc
```

Where:
- `Amon`: Atmospheric monthly data
- `r1i1p1f1`: Realization 1, Initialization 1, Physics 1, Forcing 1
- `gn`: Native grid

#### Download Method

**Using ESGF (Earth System Grid Federation)**:
```bash
# Register at: https://esgf-node.llnl.gov/
# Search for: ACCESS-CM2 ScenarioMIP

# Direct download URLs available through ESGF search interface
# Example search criteria:
# - Project: CMIP6
# - Source ID: ACCESS-CM2
# - Experiment ID: ssp126, ssp245, ssp370, ssp585
# - Variable: tas, pr
# - Frequency: mon (monthly)
# - Variant Label: r1i1p1f1
```

**Using wget** (after obtaining URLs from ESGF):
```bash
wget https://esgf-data.dkrz.de/...path.../tas_Amon_ACCESS-CM2_ssp245_r1i1p1f1_gn_*.nc
```

**Reference**: Bi, D., et al. (2020). Configuration and spin-up of ACCESS-CM2, the new generation Australian Community Climate and Earth System Simulator Coupled Model. *Journal of Southern Hemisphere Earth Systems Science*, 70(1), 225-251.

**CMIP6 Citation**: Eyring, V., et al. (2016). Overview of the Coupled Model Intercomparison Project Phase 6 (CMIP6) experimental design and organization. *Geoscientific Model Development*, 9(5), 1937-1958.

---

### 7. OGGM Glacier Directories
**Location**: `/data/oggm_gdirs/` (automatically downloaded)

**Purpose**: Preprocessed glacier geometry and flowline data
**Source**: Open Global Glacier Model (OGGM) v1.6
**Content**:
- Glacier centerlines and flowlines
- Elevation band discretization (50m bins)
- Ice thickness distribution along flowlines
- Catchment boundaries

**Auto-download**: PyGEM automatically downloads OGGM data when `has_internet: true` in config

**OGGM Base URL**:
```
https://cluster.klima.uni-bremen.de/~oggm/gdirs/oggm_v1.6/L1-L2_files/elev_bands/
```

**Reference**: Maussion, F., et al. (2019). The Open Global Glacier Model (OGGM) v1.1. *Geoscientific Model Development*, 12(3), 909-931.

---

### Data Directory Structure Summary

```
PygemRound2/
├── inputs/
│   ├── RGI60-01.20947/              # Glacier outline shapefiles
│   │   └── outlines.shp             (36 KB)
│   ├── thickness/
│   │   └── RGI60-01.20947_thickness.tif  (264 KB)
│   ├── surface_change_2022_2023.TIF (399 MB) - Calibration DEM
│   ├── stake_observations_dixon.csv  (3 KB) - Validation data
│   ├── ERA5/                        # Historical climate (2000-2024)
│   │   ├── ERA5_temp_monthly.nc
│   │   ├── ERA5_totalprecip_monthly.nc
│   │   ├── ERA5_geopotential.nc
│   │   └── ... (other ERA5 variables)
│   └── CMIP6/                       # Future climate scenarios (2015-2100)
│       ├── SSP126_near-surface-air-temp_2015to2100/
│       │   └── tas_Amon_ACCESS-CM2_ssp126_*.nc  (1.1 MB)
│       ├── SSP126_precip_2015to2100/
│       │   └── pr_Amon_ACCESS-CM2_ssp126_*.nc
│       ├── SSP245_near-surface-air-temp_2015to2100/
│       ├── SSP245_precip_2015to2100/
│       ├── SSP370_near-surface-air-temp_2015to2100/
│       ├── SSP370_precip_2015to2100/
│       ├── SSP585_near-surface-air-temp_2015to2100/
│       └── SSP585_precip_2015to2100/
│
└── data/
    ├── oggm_gdirs/                  # Auto-downloaded OGGM data
    └── Output/                      # PyGEM simulation outputs
        └── simulations/01/ACCESS-CM2/ssp245/
            ├── stats/               # Glacier-wide time series
            └── binned/              # Elevation-binned outputs
```

### Total Data Requirements
- **Minimum** (single scenario): ~500 MB
- **Full setup** (all 4 CMIP6 scenarios): ~5 GB
- **With outputs** (5000-run sweep): ~50-100 GB

---

## PyGEM Source Code Modifications

### Required File
**Path**: `/PyGEM/pygem/bin/run/run_simulation.py`

### Modification 1: Add ddfsnow_iceratio Command-Line Argument

**Location**: Lines 251-257 (argument parser section)

```python
parser.add_argument(
    '-ddfsnow_iceratio',
    action='store',
    type=float,
    default=pygem_prms['sim']['params']['ddfsnow_iceratio'],
    help='Snow/ice melt ratio parameter for degree-day factor',
)
```

**Purpose**: Enables command-line control of the snow-to-ice melt factor ratio, critical for ablation zone modeling.

---

### Modification 2: Fix Parameter Detection Logic

**Location**: Lines 693-697 (parameter loading section)

**BEFORE** (broken):
```python
if args.option_calibration:
    # Always loads calibrated parameters, ignoring command-line
```

**AFTER** (fixed):
```python
# PARAMETER SWEEP FIX: Check if command-line parameters are provided
cmdline_params_provided = (args.kp is not None or
                          args.tbias is not None or
                          args.ddfsnow is not None or
                          args.ddfsnow_iceratio is not None)

if args.option_calibration and not cmdline_params_provided:
    # Load calibrated parameters only if no command-line params provided
```

**Purpose**: Prevents config file from overriding command-line parameters during parameter sweeps.

---

### Modification 3: Fix ddfice Calculation

**Location**: Lines 840-850 (parameter application section)

**BEFORE** (broken - used config value):
```python
# Used config file value instead of command-line
'ddfice': [args.ddfsnow / pygem_prms['sim']['params']['ddfsnow_iceratio']]
```

**AFTER** (fixed - uses command-line value):
```python
# PARAMETER SWEEP FIX: Using command-line parameters
if cmdline_params_provided and debug:
    print(f"PARAMETER SWEEP: Using command-line parameters - kp={args.kp}, tbias={args.tbias}, ddfsnow={args.ddfsnow}, ddfsnow_iceratio={args.ddfsnow_iceratio}")

# Use command-line value for calculation
modelparameters = {
    'kp': [args.kp],
    'ddfsnow': [args.ddfsnow],
    'ddfice': [args.ddfsnow / args.ddfsnow_iceratio],  # CRITICAL FIX
    'tbias': [args.tbias]
}
```

**Purpose**: Ensures `ddfice` is calculated from command-line `ddfsnow_iceratio`, not config file value.

---

### Modification 4: Disable Interactive Figures (Optional but Recommended)

**Location**: Throughout file (wherever `plt.show()` appears)

**Change**:
```python
# plt.show()  # DISABLED: Prevent interactive figure display during sweeps
```

**Purpose**: Prevents PyGEM from hanging on figure display during background execution.

---

### Verification Commands

After making modifications, verify they work:

```bash
# Test single run with debug output
python3 /PyGEM/pygem/bin/run/run_simulation.py \
  -rgi_glac_number 1.20947 \
  -sim_startyear 2015 \
  -sim_endyear 2020 \
  -kp 3.0 \
  -tbias -6.0 \
  -ddfsnow 0.005 \
  -ddfsnow_iceratio 0.7 \
  -outputfn_sfix _test \
  -v

# Look for this confirmation message:
# "PARAMETER SWEEP: Using command-line parameters - kp=3.0, tbias=-6.0, ddfsnow=0.005, ddfsnow_iceratio=0.7"
```

---

## Parameter Sweep Framework

### Main Script
**File**: `/command_line_parameter_sweep.py`
**Size**: 618 lines
**Type**: Production-ready Python framework

### Key Features

1. **Parameter Space Creation**
   - Flexible 4D grid definition
   - Support for custom parameter ranges
   - Automatic combination generation

2. **Execution Management**
   - Serial execution (single worker)
   - Retry mechanism (up to 3 attempts)
   - Automatic cleanup of failed runs
   - Comprehensive logging

3. **Output Verification**
   - File existence checks
   - Minimum file size validation (>1KB)
   - Automatic file copying to results directory
   - Parameter metadata in JSON format

4. **Progress Tracking**
   - Real-time progress updates
   - Success rate monitoring
   - Average runtime calculation
   - ETA estimation

### Class Structure

```python
class CommandLineParameterSweep:
    def __init__(base_dir, output_dir, use_ssd, collect_binned)
    def create_parameter_combinations(...)  # Generate param grid
    def execute_single_run(run_id, parameters, max_retries)
    def verify_pygem_outputs(run_id)
    def copy_pygem_outputs(run_id, parameters)
    def clean_partial_outputs(run_id)
    def run_parameter_sweep(parameter_df, start_run, max_runs)
    def test_setup(n_test)  # Quick testing
```

---

## Configuration

### Base Config File
**File**: `/config.yaml`

**Critical Settings**:

```yaml
# Glacier selection
setup:
  glac_no: [1.20947]  # Dixon Glacier

# Climate data
climate:
  ref_climate_name: ERA5
  ref_startyear: 2000
  ref_endyear: 2024
  sim_climate_name: ACCESS-CM2
  sim_climate_scenario: ssp245  # Can be overridden by command-line
  sim_startyear: 2015
  sim_endyear: 2100

# Mass balance options
mb:
  option_ablation: 1  # Degree-day model
  option_accumulation: 2
  include_firn: true
  option_refreezing: Woodward

# Parameters (OVERRIDDEN by command-line during sweeps)
sim:
  params:
    kp: 1.5           # Precipitation factor (overridden)
    tbias: -9.0       # Temperature bias °C (overridden)
    ddfsnow: 0.0066   # Snow degree-day factor (overridden)
    ddfsnow_iceratio: 0.7  # Ice/snow ratio (overridden)
    lapserate: -0.007 # Temperature lapse rate °C/m
    precgrad: 0.0002  # Precipitation gradient

  export_extra_vars: true
  export_binned_data: true

# OGGM settings
oggm:
  base_url: https://cluster.klima.uni-bremen.de/~oggm/gdirs/oggm_v1.6/L1-L2_files/elev_bands/
  has_internet: true
  overwrite_gdirs: true

# Root directory (IMPORTANT)
root: /Users/kaimyers/PygemRound2/data/
```

**Note**: Config file is used for general setup, but **all 4 sweep parameters are overridden via command-line**.

---

## Usage Guide

### 1. Quick Test (5 runs)

```bash
python3 command_line_parameter_sweep.py --test 5
```

**Expected Output**:
```
Command-line parameter sweep initialized
Parameter space created: 16 combinations
Testing with 5 runs
...
Test completed: 5/5 runs successful
Test PASSED - Command-line parameter sweep working!
```

---

### 2. Small Sweep (~108 combinations, ~15 minutes)

```bash
python3 command_line_parameter_sweep.py --small
```

**Parameter Grid**:
- tbias: [-8.0, -6.0, -4.0, -2.0] (4 values)
- kp: [2.0, 4.0, 6.0] (3 values)
- ddfsnow: [0.004, 0.006, 0.008] (3 values)
- ddfsnow_iceratio: [0.5, 0.7, 0.9] (3 values)
- **Total**: 4 × 3 × 3 × 3 = 108 combinations

**Output Location**: `/Volumes/Extreme SSD/cmdline_parameter_sweep/` (if SSD connected)

---

### 3. Medium Sweep (~980 combinations, ~2 hours)

```bash
python3 command_line_parameter_sweep.py --medium
```

**Parameter Grid**:
- tbias: 7 values from -9.0 to -3.0°C
- kp: 5 values from 2.0 to 6.0
- ddfsnow: 7 values from 0.003 to 0.009
- ddfsnow_iceratio: [0.4, 0.6, 0.8, 1.0]
- **Total**: 7 × 5 × 7 × 4 = 980 combinations

---

### 4. Large Sweep (~4000 combinations, ~8 hours)

```bash
python3 command_line_parameter_sweep.py --large
```

**Parameter Grid**:
- tbias: 10 values from -9.0 to -3.0°C
- kp: 8 values from 1.0 to 7.0
- ddfsnow: 10 values (log-spaced) from 0.003 to 0.010
- ddfsnow_iceratio: 5 values from 0.4 to 1.0
- **Total**: 10 × 8 × 10 × 5 = 4000 combinations

---

### 5. Custom Parameter Ranges

```python
from command_line_parameter_sweep import CommandLineParameterSweep
import numpy as np

# Initialize
sweep = CommandLineParameterSweep(collect_binned=True)

# Create custom parameter grid
params = sweep.create_parameter_combinations(
    tbias_range=np.linspace(-9.0, -5.0, 9),         # 9 values
    kp_range=np.linspace(2.5, 6.0, 8),              # 8 values
    ddfsnow_range=np.logspace(-3.2, -2.0, 7),       # 7 values (log-spaced)
    ddfsnow_iceratio_range=[0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]  # 7 values
)

# Run sweep
results = sweep.run_parameter_sweep(params)

# Total: 9 × 8 × 7 × 7 = 3528 combinations
```

---

### 6. Background Execution (Recommended for Large Sweeps)

```bash
# Using nohup
nohup python3 command_line_parameter_sweep.py --large > sweep_log.txt 2>&1 &

# Check progress
tail -f sweep_log.txt

# Monitor process
ps aux | grep command_line_parameter_sweep

# Check results
ls -lh /Volumes/Extreme\ SSD/cmdline_parameter_sweep/results/ | wc -l
```

---

### 7. Resume Interrupted Sweep

```bash
# If sweep interrupted at run 500
python3 command_line_parameter_sweep.py --large --start-run 500

# Or limit additional runs
python3 command_line_parameter_sweep.py --large --start-run 500 --max-runs 1000
```

---

### 8. Collect Binned Data (Elevation-Resolved Outputs)

```bash
# By default, only stats files collected (faster)
python3 command_line_parameter_sweep.py --small

# To collect binned files (elevation-resolved data)
python3 command_line_parameter_sweep.py --small --collect-binned
```

**Binned Data**: Contains mass balance by elevation bin (100m resolution, 134 bins for Dixon)
**Use Case**: Required for spatial validation against stake observations

---

## Data Sources Documentation

### Complete Data Provenance

| Data Type | Source | Period | Resolution | File Size | Reference |
|-----------|--------|--------|------------|-----------|-----------|
| Glacier Outline | RGI 6.0 | 2015 (nominal) | Vector | 36 KB | RGI Consortium (2017) |
| Ice Thickness | Farinotti et al. (2019) | 2019 estimate | 100m | 264 KB | Nature Geoscience |
| Surface Change DEM | Field measurements | 2022-2023 | <1m | 399 MB | Dixon field campaign |
| Stake Observations | Field measurements | 2022-2025 | Point (3 sites) | 3 KB | Dixon field campaign |
| Historical Climate | ERA5 Reanalysis | 2000-2024 | 0.25° (~31km) | ~500 MB | ECMWF |
| Future Climate | ACCESS-CM2 CMIP6 | 2015-2100 | ~250km | ~1 MB per scenario | CSIRO |

### Key References

1. **RGI Consortium** (2017). Randolph Glacier Inventory 6.0. GLIMS Technical Report.

2. **Farinotti, D., et al.** (2019). A consensus estimate for the ice thickness distribution of all glaciers on Earth. *Nature Geoscience*, 12(3), 168-173. DOI: 10.1038/s41561-019-0300-3

3. **Hersbach, H., et al.** (2020). The ERA5 global reanalysis. *Quarterly Journal of the Royal Meteorological Society*, 146(730), 1999-2049. DOI: 10.1002/qj.3803

4. **Bi, D., et al.** (2020). Configuration and spin-up of ACCESS-CM2. *Journal of Southern Hemisphere Earth Systems Science*, 70(1), 225-251. DOI: 10.1071/ES19035

5. **Eyring, V., et al.** (2016). Overview of CMIP6 experimental design. *Geoscientific Model Development*, 9(5), 1937-1958. DOI: 10.5194/gmd-9-1937-2016

6. **Maussion, F., et al.** (2019). The Open Global Glacier Model (OGGM) v1.1. *Geoscientific Model Development*, 12(3), 909-931. DOI: 10.5194/gmd-12-909-2019

---

## Troubleshooting

### Issue 1: All Runs Produce Identical Results

**Symptom**: Different parameter combinations yield the same glacier area/volume

**Cause**: PyGEM using config file parameters instead of command-line

**Solution**: Verify PyGEM source code modifications applied (see section above)

**Verification**:
```bash
grep -n "PARAMETER SWEEP FIX" /PyGEM/pygem/bin/run/run_simulation.py
# Should show lines 693 and 840
```

---

### Issue 2: Low Success Rate (<80%)

**Symptom**: Many runs fail with timeout or verification errors

**Cause**: Likely parallel execution or insufficient resources

**Solution**:
- Use serial execution only (single worker)
- Increase timeout: `timeout=1800` (30 minutes)
- Check disk space on output drive
- Verify SSD connection if using external storage

---

### Issue 3: Missing Output Files

**Symptom**: PyGEM runs successfully but no files copied

**Cause**: Files written to unexpected location or verification threshold too strict

**Solution**:
```bash
# Check PyGEM output directories
ls -lh /PygemRound2/data/Output/simulations/01/ACCESS-CM2/ssp245/stats/
ls -lh /PygemRound2/data/Output/simulations/01/ACCESS-CM2/ssp245/binned/

# Check file sizes
find /PygemRound2/data/Output -name "*cmd*.nc" -exec ls -lh {} \;

# Verify output suffix matches run_id
# Should see files like: *_cmd0042all.nc, *_cmd0042binned.nc
```

---

### Issue 4: Extremely Slow Execution

**Symptom**: >60 seconds per run (expected: 6-8 seconds)

**Possible Causes**:
1. **Figure generation enabled** - Check if `plt.show()` commented out
2. **Network latency** - Verify OGGM data already downloaded
3. **Disk I/O bottleneck** - Use SSD for output storage
4. **Memory swapping** - Close other memory-intensive applications

**Solutions**:
```bash
# Pre-download OGGM data
python3 -c "from oggm import cfg, workflow, utils; cfg.initialize(); utils.get_rgi_glacier_entities(['RGI60-01.20947'])"

# Monitor system resources
top -o cpu  # Check CPU usage
df -h       # Check disk space
```

---

### Issue 5: OGGM Download Failures

**Symptom**: "Failed to download glacier directory" errors

**Cause**: Network connectivity or OGGM server issues

**Solution**:
```yaml
# In config.yaml, set:
oggm:
  has_internet: true
  overwrite_gdirs: true  # Forces re-download if corrupted

# Or manually download OGGM data
# URL: https://cluster.klima.uni-bremen.de/~oggm/gdirs/oggm_v1.6/L1-L2_files/elev_bands/RGI60-01/RGI60-01.20/RGI60-01.20947.tar.gz
```

---

### Issue 6: Out of Memory Errors

**Symptom**: Python crashes with memory error during sweep

**Cause**: Accumulating data in memory, insufficient RAM

**Solution**:
- Results are saved per-run (no memory accumulation issue in framework)
- Reduce `nsims` in config if running ensemble mode
- Close other applications
- Add swap space if necessary

---

### Issue 7: Climate Data Not Found

**Symptom**: "FileNotFoundError: ACCESS-CM2_ssp245_*.nc"

**Cause**: Missing climate data files or incorrect paths

**Solution**:
```bash
# Check climate data exists
ls -lh inputs/CMIP6/SSP245_near-surface-air-temp_2015to2100/*.nc
ls -lh inputs/CMIP6/SSP245_precip_2015to2100/*.nc

# Verify file naming matches PyGEM expectations
# Should be: tas_Amon_ACCESS-CM2_ssp245_r1i1p1f1_gn_*.nc
#            pr_Amon_ACCESS-CM2_ssp245_r1i1p1f1_gn_*.nc

# Check config.yaml paths
grep "ssp245_relpath" config.yaml
# Should point to: /climate_data/CMIP6/SSP245/ or similar
```

---

## Summary of Achievements

### What Works
✅ 4D parameter sweep with full control (tbias, kp, ddfsnow, ddfsnow_iceratio)
✅ 96.3% success rate on production runs
✅ Validated on 5000+ run sweeps (94.5% success rate)
✅ Serial execution with retry mechanism
✅ Complete output verification and collection
✅ Elevation-binned spatial validation capability
✅ Multi-scenario climate projections (SSP126, SSP245, SSP370, SSP585)

### What's Documented
✅ All data sources with provenance
✅ Complete PyGEM source code modifications
✅ Step-by-step setup and usage guide
✅ Troubleshooting for common issues
✅ Validated parameter ranges for Dixon Glacier

### Ready for Production
This framework has been tested and validated for large-scale parameter sweeps and is ready for:
- Comprehensive parameter optimization
- Uncertainty quantification
- Multi-scenario climate projections
- Reproducible glacier modeling research

---

**Last Updated**: January 13, 2026
**Framework Version**: 1.0 (Production)
**Tested PyGEM Version**: Custom fork with parameter sweep modifications
**Contact**: Kai Myers (dixon-glacier-pygem repository)
