# Dixon Glacier PyGEM Data Bundle Checklist

Quick reference for setting up a fresh PyGEM installation with all required data for Dixon Glacier parameter sweeps.

---

## Quick Setup Checklist

### ☐ 1. Core PyGEM Installation
```bash
git clone https://github.com/drounce/PyGEM.git
cd PyGEM
pip install -e .
```

### ☐ 2. Apply Source Code Modifications
**File**: `PyGEM/pygem/bin/run/run_simulation.py`

**Three critical changes required**:
1. ☐ Add `-ddfsnow_iceratio` argument (line ~252)
2. ☐ Fix parameter detection logic (line ~693)
3. ☐ Fix `ddfice` calculation (line ~850)
4. ☐ Comment out `plt.show()` calls (optional but recommended)

**Verification**:
```bash
grep -n "ddfsnow_iceratio" PyGEM/pygem/bin/run/run_simulation.py | wc -l
# Should show: 5 matches
```

---

## Required Data Files

### ☐ 3. Glacier Outline (36 KB)
**Location**: `inputs/RGI60-01.20947/`
```
☐ outlines.shp
☐ outlines.dbf
☐ outlines.shx
☐ outlines.prj
☐ outlines.cpg
```
**Source**: RGI 6.0 - https://www.glims.org/RGI/

---

### ☐ 4. Ice Thickness (264 KB)
**Location**: `inputs/thickness/`
```
☐ RGI60-01.20947_thickness.tif
☐ RGI60-01.20947_thickness.tif.aux.xml
```
**Source**: Farinotti et al. (2019) via OGGM

---

### ☐ 5. Surface Change DEM (399 MB)
**Location**: `inputs/`
```
☐ surface_change_2022_2023.TIF
```
**Source**: Dixon field campaign LiDAR-SfM differencing
**Purpose**: Mass balance calibration data

---

### ☐ 6. Stake Observations (3 KB)
**Location**: `inputs/`
```
☐ stake_observations_dixon.csv
```
**Source**: Dixon field measurements 2022-2025
**Purpose**: Model validation data

---

### ☐ 7. Historical Climate Data: ERA5 (~500 MB)
**Location**: `inputs/ERA5/`
```
☐ ERA5_temp_monthly.nc
☐ ERA5_totalprecip_monthly.nc
☐ ERA5_geopotential.nc
☐ ERA5_lapserates_monthly.nc
☐ ERA5_tempstd_monthly.nc
☐ ERA5_pressureleveltemp_monthly.nc
```
**Source**: ECMWF ERA5 Reanalysis (2000-2024)
**Download**: https://cds.climate.copernicus.eu/ (requires account)

**CDS API Setup**:
```bash
pip install cdsapi
# Configure ~/.cdsapirc with API key from CDS website
```

---

### ☐ 8. Future Climate Data: ACCESS-CM2 CMIP6 (~4 MB)
**Location**: `inputs/CMIP6/`

#### SSP245 (Default - Moderate Warming)
```
☐ SSP245_near-surface-air-temp_2015to2100/
   └── tas_Amon_ACCESS-CM2_ssp245_r1i1p1f1_gn_*.nc
☐ SSP245_precip_2015to2100/
   └── pr_Amon_ACCESS-CM2_ssp245_r1i1p1f1_gn_*.nc
```

#### SSP126 (Optional - Low Warming)
```
☐ SSP126_near-surface-air-temp_2015to2100/
   └── tas_Amon_ACCESS-CM2_ssp126_r1i1p1f1_gn_*.nc
☐ SSP126_precip_2015to2100/
   └── pr_Amon_ACCESS-CM2_ssp126_r1i1p1f1_gn_*.nc
```

#### SSP370 (Optional - High Warming)
```
☐ SSP370_near-surface-air-temp_2015to2100/
   └── tas_Amon_ACCESS-CM2_ssp370_r1i1p1f1_gn_*.nc
☐ SSP370_precip_2015to2100/
   └── pr_Amon_ACCESS-CM2_ssp370_r1i1p1f1_gn_*.nc
```

#### SSP585 (Optional - Very High Warming)
```
☐ SSP585_near-surface-air-temp_2015to2100/
   └── tas_Amon_ACCESS-CM2_ssp585_r1i1p1f1_gn_*.nc
☐ SSP585_precip_2015to2100/
   └── pr_Amon_ACCESS-CM2_ssp585_r1i1p1f1_gn_*.nc
```

**Source**: ESGF CMIP6 archive
**Download**: https://esgf-node.llnl.gov/ (requires registration)

**Search Criteria**:
- Project: CMIP6
- Source ID: ACCESS-CM2
- Experiment ID: ssp245 (or ssp126, ssp370, ssp585)
- Variable: tas, pr
- Frequency: mon
- Variant Label: r1i1p1f1

---

### ☐ 9. OGGM Glacier Directories (Auto-downloaded)
**Location**: `data/oggm_gdirs/` (created automatically)
**Source**: PyGEM auto-downloads when `has_internet: true` in config

**Manual download** (if needed):
```bash
wget https://cluster.klima.uni-bremen.de/~oggm/gdirs/oggm_v1.6/L1-L2_files/elev_bands/RGI60-01/RGI60-01.20/RGI60-01.20947.tar.gz
```

---

## Configuration Files

### ☐ 10. Main Configuration
**File**: `config.yaml`

**Critical settings to verify**:
```yaml
setup:
  glac_no: [1.20947]  # Dixon Glacier RGI ID

climate:
  ref_climate_name: ERA5
  ref_startyear: 2000
  ref_endyear: 2024
  sim_climate_name: ACCESS-CM2
  sim_climate_scenario: ssp245
  sim_startyear: 2015
  sim_endyear: 2100

oggm:
  has_internet: true
  overwrite_gdirs: true

root: /path/to/PygemRound2/data/  # UPDATE THIS PATH
```

---

### ☐ 11. Parameter Sweep Framework
**File**: `command_line_parameter_sweep.py`

**Verify paths in script**:
```python
base_dir = "/Users/kaimyers/PygemRound2"  # Line 39 - UPDATE THIS
pygem_script = self.base_dir / "PyGEM/pygem/bin/run/run_simulation.py"  # Line 58
```

---

## Directory Structure Verification

### ☐ 12. Complete Directory Tree
```
PygemRound2/
├── PyGEM/                           # PyGEM installation (git submodule or clone)
│   └── pygem/
│       └── bin/
│           └── run/
│               └── run_simulation.py  # MODIFIED
│
├── inputs/
│   ├── RGI60-01.20947/              # ☐ Glacier outline
│   ├── thickness/                   # ☐ Ice thickness
│   ├── surface_change_2022_2023.TIF # ☐ Calibration DEM
│   ├── stake_observations_dixon.csv # ☐ Validation data
│   ├── ERA5/                        # ☐ Historical climate
│   └── CMIP6/                       # ☐ Future climate scenarios
│       ├── SSP126_near-surface-air-temp_2015to2100/
│       ├── SSP126_precip_2015to2100/
│       ├── SSP245_near-surface-air-temp_2015to2100/
│       ├── SSP245_precip_2015to2100/
│       ├── SSP370_near-surface-air-temp_2015to2100/
│       ├── SSP370_precip_2015to2100/
│       ├── SSP585_near-surface-air-temp_2015to2100/
│       └── SSP585_precip_2015to2100/
│
├── data/
│   ├── oggm_gdirs/                  # Auto-created by PyGEM
│   └── Output/                      # Auto-created by PyGEM
│       └── simulations/
│
├── config.yaml                      # ☐ Main configuration
├── command_line_parameter_sweep.py  # ☐ Parameter sweep framework
└── SETUP_GUIDE_4D_PARAMETER_SWEEP.md  # ☐ Complete documentation
```

---

## Verification Tests

### ☐ 13. Test PyGEM Installation
```bash
python3 -c "import pygem; print('PyGEM imported successfully')"
```

### ☐ 14. Test Single Simulation
```bash
cd PyGEM/pygem/bin/run
python3 run_simulation.py \
  -rgi_glac_number 1.20947 \
  -sim_startyear 2015 \
  -sim_endyear 2020 \
  -kp 3.0 \
  -tbias -6.0 \
  -ddfsnow 0.005 \
  -ddfsnow_iceratio 0.7 \
  -outputfn_sfix _test

# Should complete in ~5-10 seconds
# Look for: "PARAMETER SWEEP: Using command-line parameters..."
```

### ☐ 15. Test Parameter Sweep Framework
```bash
cd /path/to/PygemRound2
python3 command_line_parameter_sweep.py --test 5

# Expected: 5/5 runs successful
# Runtime: ~30-60 seconds total
```

---

## File Size Summary

| Component | Size | Critical? |
|-----------|------|-----------|
| PyGEM source code | ~50 MB | ✅ Yes |
| Glacier outline | 36 KB | ✅ Yes |
| Ice thickness | 264 KB | ✅ Yes |
| Surface change DEM | 399 MB | ✅ Yes (calibration) |
| Stake observations | 3 KB | ✅ Yes (validation) |
| ERA5 climate data | ~500 MB | ✅ Yes |
| CMIP6 SSP245 (minimum) | ~1 MB | ✅ Yes |
| CMIP6 other scenarios | ~1 MB each | ⚠️ Optional |
| OGGM directories | ~10 MB | Auto-downloaded |
| **TOTAL (minimum)** | **~1 GB** | |
| **TOTAL (all scenarios)** | **~1.5 GB** | |

---

## Common Issues During Setup

### Issue: "ModuleNotFoundError: No module named 'pygem'"
**Solution**:
```bash
cd PyGEM
pip install -e .
```

### Issue: "FileNotFoundError: config.yaml"
**Solution**:
```bash
# Ensure running from project root
cd /path/to/PygemRound2
python3 command_line_parameter_sweep.py --test 5
```

### Issue: "OGGM download failed"
**Solution**:
```yaml
# In config.yaml:
oggm:
  has_internet: true
  overwrite_gdirs: true
```

### Issue: All parameter runs produce identical results
**Solution**: Verify PyGEM source code modifications applied
```bash
grep "PARAMETER SWEEP FIX" PyGEM/pygem/bin/run/run_simulation.py
# Should show 2 matches (lines ~693 and ~840)
```

### Issue: "Permission denied" when writing outputs
**Solution**:
```bash
# Check/create output directory
mkdir -p data/Output/simulations
chmod -R u+w data/
```

---

## Ready to Run

Once all checkboxes are complete:

✅ **Quick Test** (30 seconds):
```bash
python3 command_line_parameter_sweep.py --test 5
```

✅ **Small Sweep** (15 minutes):
```bash
python3 command_line_parameter_sweep.py --small
```

✅ **Production Run** (hours to days):
```bash
nohup python3 command_line_parameter_sweep.py --large > sweep.log 2>&1 &
```

---

## Data Archiving Recommendations

For long-term storage or transfer to another machine:

### Minimal Bundle (For Running Model)
```bash
# ~1 GB compressed
tar -czf dixon_pygem_minimal.tar.gz \
  inputs/RGI60-01.20947/ \
  inputs/thickness/ \
  inputs/surface_change_2022_2023.TIF \
  inputs/stake_observations_dixon.csv \
  inputs/ERA5/ \
  inputs/CMIP6/SSP245_* \
  config.yaml \
  command_line_parameter_sweep.py \
  SETUP_GUIDE_4D_PARAMETER_SWEEP.md
```

### Complete Bundle (All Scenarios)
```bash
# ~1.5 GB compressed
tar -czf dixon_pygem_complete.tar.gz \
  inputs/ \
  config.yaml \
  command_line_parameter_sweep.py \
  SETUP_GUIDE_4D_PARAMETER_SWEEP.md \
  DATA_BUNDLE_CHECKLIST.md
```

### Results Archive (After Sweep)
```bash
# Size varies (50-100 GB for 5000-run sweep)
tar -czf dixon_results_YYYYMMDD.tar.gz \
  cmdline_parameter_sweep/results/ \
  cmdline_parameter_sweep/logs/
```

---

**Setup Time Estimate**:
- PyGEM installation: 10 minutes
- Data download: 30-60 minutes (depending on connection)
- Source code modifications: 5 minutes
- Testing: 5 minutes
- **Total**: ~1-2 hours for complete setup

**Last Updated**: January 13, 2026
