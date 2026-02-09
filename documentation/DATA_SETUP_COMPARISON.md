# Climate Data Setup Comparison: Mega Sweep vs Standard Sweep

**Created**: January 14, 2026
**Purpose**: Clarify the two different climate data setups used in Dixon Glacier parameter sweeps

---

## Quick Summary

Your codebase contains **two different parameter sweep setups** that use **different climate data**:

| Feature | MEGA SWEEP | STANDARD SWEEP |
|---------|-----------|----------------|
| **Script** | `run_dixon_mega_sweep_no_retry.py` | `command_line_parameter_sweep.py` |
| **Time Period** | 2023-2025 (3 years) | 2015-2100 (86 years) |
| **Climate Data** | SNAP + NUKA weather station | ACCESS-CM2 CMIP6 projections |
| **Temperature Source** | SNAP Alaska 2km downscaled | ACCESS-CM2 GCM |
| **Precipitation Source** | NUKA on-glacier weather station | ACCESS-CM2 GCM |
| **Data Location** | `data/climate_data/ERA5_real_extended/` | `inputs/CMIP6/SSP245_*/` |
| **Purpose** | Short-term calibration with observations | Long-term climate projections |
| **Status** | Ran Dec 2025 (24K runs, stopped at 9.6%) | Production-ready framework |

---

## 1. MEGA SWEEP Setup (2023-2025)

### Overview
- **What**: Large-scale parameter calibration using on-glacier observations
- **When**: December 30, 2025
- **Results**: 23,979 successful runs out of 250,000 attempted (9.6% complete)
- **Success Rate**: 97.9%
- **Runtime**: 9.6 days before SSD disconnected

### Climate Data Used

**Temperature**: SNAP Alaska 2km downscaled reanalysis
- Monthly resolution
- 2023-2025 period (36 months)
- High-resolution local climate

**Precipitation**: NUKA Glacier SNOTEL weather station
- Daily measurements aggregated to monthly
- On-glacier measurements (most accurate possible)
- 2023-2025 observations

**Data Files**:
```
data/climate_data/ERA5_real_extended/
├── ERA5_temp_monthly.nc              (27 MB) - SNAP temperature
├── ERA5_totalprecip_monthly.nc       (29 MB) - NUKA precipitation
├── ERA5_geopotential.nc              (830 KB)
├── ERA5_lapserates_monthly.nc        (60 MB)
├── ERA5_tempstd_monthly.nc           (15 MB)
└── ERA5_pressureleveltemp_monthly.nc (57 MB)

data/climate_data/Dixon_raw/
├── NUKA_2023_precip_daily.csv        (10 KB) - Source data
├── NUKA_2024_precip_daily.csv        (9.6 KB)
├── NUKA_2025_precip_daily.csv        (13 KB)
├── Dixon24WX_RAW.csv                 (78 KB)
└── Dixon25_temp.csv                  (188 KB)
```

**⚠️ IMPORTANT**: Despite the directory name "ERA5_real_extended", these files contain **SNAP + SNOTEL data**, NOT standard ERA5 reanalysis!

### Execution
```bash
python3 run_dixon_mega_sweep_no_retry.py --grid mega250k --ssd
```

**Key Parameters** (from script lines 106-107):
```python
self.start_year = 2023
self.end_year = 2025
```

### Data Preparation
Created with: `prepare_snap_snotel_climate_data.py`
- Processed NUKA weather station daily precipitation → monthly
- Extracted SNAP temperature for Dixon location
- Formatted as PyGEM-compatible NetCDF files
- Date: December 30, 2025

---

## 2. STANDARD SWEEP Setup (2015-2100)

### Overview
- **What**: Long-term climate projection parameter sweeps
- **Purpose**: Peak water timing, long-term glacier evolution
- **Status**: Production-ready, validated (96.3% success rate)
- **Framework**: Documented in SETUP_GUIDE_4D_PARAMETER_SWEEP.md

### Climate Data Used

**Historical Reference**: ERA5 Reanalysis (2000-2024)
- ECMWF ERA5 global reanalysis
- 0.25° resolution (~31 km)
- Standard climate forcing for calibration

**Future Projections**: ACCESS-CM2 CMIP6 (2015-2100)
- Australian climate model
- Multiple scenarios: SSP126, SSP245, SSP370, SSP585
- ~250 km resolution
- Standard for climate change research

**Data Files**:
```
inputs/CMIP6/SSP245_near-surface-air-temp_2015to2100/
└── tas_Amon_ACCESS-CM2_ssp245_r1i1p1f1_gn_20150116-21001216.nc (1.0 MB)

inputs/CMIP6/SSP245_precip_2015to2100/
└── pr_Amon_ACCESS-CM2_ssp245_r1i1p1f1_gn_20150116-21001216.nc (1.2 MB)

(Plus SSP126, SSP370, SSP585 scenarios if needed)
```

### Execution
```bash
# Test
python3 command_line_parameter_sweep.py --test 5

# Production
python3 command_line_parameter_sweep.py --small   # ~108 runs
python3 command_line_parameter_sweep.py --medium  # ~980 runs
python3 command_line_parameter_sweep.py --large   # ~4000 runs
```

**Key Parameters** (from script lines 356-357):
```python
'-sim_startyear', '2015'
'-sim_endyear', '2100'
```

---

## Configuration File Settings

### config.yaml for MEGA SWEEP
```yaml
climate:
  ref_climate_name: ERA5
  ref_startyear: 2000
  ref_endyear: 2024
  sim_climate_name: ACCESS-CM2
  sim_climate_scenario: ssp245
  sim_startyear: 2015  # ← Overridden by script to 2023
  sim_endyear: 2100    # ← Overridden by script to 2025
  paths:
    era5_relpath: /climate_data/ERA5_real_extended/  # ← Points to SNAP+SNOTEL data
```

### config.yaml for STANDARD SWEEP
```yaml
climate:
  ref_climate_name: ERA5
  ref_startyear: 2000
  ref_endyear: 2024
  sim_climate_name: ACCESS-CM2
  sim_climate_scenario: ssp245
  sim_startyear: 2015  # ← Used as-is
  sim_endyear: 2100    # ← Used as-is
  paths:
    ssp245_relpath: /climate_data/CMIP6/SSP245/  # ← Points to CMIP6 projections
```

---

## Which Setup to Use?

### Use MEGA SWEEP Setup (2023-2025) When:
- ✅ Calibrating parameters against recent observations
- ✅ You have on-glacier weather station data
- ✅ Short-term validation is priority
- ✅ Using stake observations from 2023-2025
- ✅ Need highest-resolution local climate data

### Use STANDARD SWEEP Setup (2015-2100) When:
- ✅ Projecting long-term glacier evolution
- ✅ Analyzing peak water timing
- ✅ Comparing climate scenarios (SSP126/245/370/585)
- ✅ Need 21st-century projections
- ✅ Using standard CMIP6 climate data

---

## File Organization Summary

### Core Files (Same for Both)
```
inputs/
├── RGI60-01.20947/              # Glacier outline (SAME)
├── thickness/                   # Ice thickness (SAME)
├── surface_change_2022_2023.TIF # Calibration DEM (SAME)
└── stake_observations_dixon.csv # Validation data (SAME)

config.yaml                      # Configuration (SAME base)
command_line_parameter_sweep.py  # Framework code (SAME)
PyGEM/pygem/bin/run/run_simulation.py  # Modified PyGEM (SAME)
```

### MEGA SWEEP Specific
```
data/climate_data/
├── ERA5_real_extended/          # SNAP + SNOTEL (NetCDF format)
├── Dixon_raw/                   # Raw weather station data
└── SNAP_SNOTEL_combined/        # Processed CSV format

run_dixon_mega_sweep_no_retry.py # Mega sweep script
prepare_snap_snotel_climate_data.py  # Data preparation
```

### STANDARD SWEEP Specific
```
inputs/CMIP6/
├── SSP126_near-surface-air-temp_2015to2100/
├── SSP126_precip_2015to2100/
├── SSP245_near-surface-air-temp_2015to2100/
├── SSP245_precip_2015to2100/
├── SSP370_near-surface-air-temp_2015to2100/
├── SSP370_precip_2015to2100/
├── SSP585_near-surface-air-temp_2015to2100/
└── SSP585_precip_2015to2100/
```

---

## Data Size Comparison

| Component | MEGA SWEEP | STANDARD SWEEP |
|-----------|-----------|----------------|
| Climate data | ~189 MB | ~8 MB (all scenarios) |
| Raw source data | ~475 KB | N/A |
| Time coverage | 3 years | 86 years |
| Temporal resolution | Monthly | Monthly |
| Spatial resolution | 2km (SNAP) + on-glacier | ~250km (GCM) |
| Total required | ~365 MB | ~268 MB |

---

## Key Takeaways

1. **Two Different Purposes**:
   - MEGA: Calibrate with observations (2023-2025)
   - STANDARD: Project future (2015-2100)

2. **Different Climate Data**:
   - MEGA: SNAP + weather station (high resolution, short period)
   - STANDARD: CMIP6 projections (coarse resolution, long period)

3. **Misleading Directory Names**:
   - `ERA5_real_extended/` actually contains SNAP+SNOTEL data
   - Check file contents and metadata, not just directory names!

4. **Both Are Valid**:
   - MEGA: Best for parameter calibration with recent observations
   - STANDARD: Best for climate change projections and peak water

5. **Documentation Files**:
   - `INPUT_DATA_PATHS_MEGA_SWEEP.txt` - For 2023-2025 setup
   - `INPUT_DATA_PATHS_STANDARD.txt` - For 2015-2100 setup
   - This file - Comparison and decision guide

---

## Recommended Workflow

### For New Parameter Calibration:
1. Run **MEGA SWEEP** (2023-2025) to calibrate against observations
2. Identify optimal parameters from validation
3. Use those parameters in **STANDARD SWEEP** (2015-2100) for projections

### For Climate Projections Only:
1. Use existing calibrated parameters
2. Run **STANDARD SWEEP** (2015-2100) directly
3. Compare across climate scenarios (SSP126/245/370/585)

---

**Last Updated**: January 14, 2026
**See Also**:
- `SETUP_GUIDE_4D_PARAMETER_SWEEP.md` - Complete setup guide
- `DATA_BUNDLE_CHECKLIST.md` - Setup verification checklist
- `INPUT_DATA_PATHS_MEGA_SWEEP.txt` - Mega sweep data paths
- `INPUT_DATA_PATHS_STANDARD.txt` - Standard sweep data paths
