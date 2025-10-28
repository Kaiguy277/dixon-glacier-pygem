# CMIP6 Real Climate Data Download Guide for PyGEM Dixon Glacier

## 🎯 Summary: Replace Artificial Climate Data with Real CMIP6 Projections

**Current Issue**: PyGEM is using artificial climate data (repeated 2020-2024 climatology) for 2025-2100, which has no warming trends.

**Solution**: Download real CMIP6 climate model projections with proper warming scenarios.

## 📋 Required Data Specifications

### Variables Needed
- **tas**: Surface Air Temperature (monthly means)
- **pr**: Precipitation Rate (monthly means)  
- **orog**: Surface Altitude/Orography (time-invariant)

### Format Requirements
- **File Format**: NetCDF (.nc files)
- **Variable Names**: Must be exactly `tas`, `pr`, `orog` (PyGEM hardcoded)
- **Coordinate Names**: `lat`, `lon`, `time`
- **Units**: 
  - Temperature: Kelvin [K] 
  - Precipitation: kg m⁻² s⁻¹
  - Elevation: meters [m]

### Temporal Coverage
- **Historical**: 2015-2014 (for bias correction)
- **Future**: 2015-2100 (scenario projections)
- **Frequency**: Monthly means (`mon`)
- **Time format**: CF-compliant datetime

### Spatial Coverage
- **Region**: Must include Alaska/Arctic (55-70°N, 170-130°W)
- **Grid**: Regular lat-lon grid
- **Resolution**: 1-2.5° typical (PyGEM regridding handles this)

## 🌍 Download Sources & Methods

### Method 1: ESGF Data Portal (Recommended)
**URL**: https://esgf-node.llnl.gov/search/cmip6/

**Search Parameters**:
```
Project: CMIP6
Source ID: ACCESS-CM2 (or other recommended model)
Experiment ID: historical, ssp245
Variable ID: tas, pr, orog
Frequency: mon
Realm: atmos
Grid Label: gn (native grid)
Variant Label: r1i1p1f1 (first realization)
```

**Step-by-step**:
1. Go to ESGF search portal
2. Select CMIP6 project
3. Choose model (ACCESS-CM2 recommended)
4. Select experiments: `historical` + `ssp245`
5. Select variables: `tas`, `pr`, `orog` 
6. Download files to local directory
7. Rename files to PyGEM format (see below)

### Method 2: Climate Data Store (Copernicus)
**URL**: https://cds.climate.copernicus.eu/cdsapp#!/dataset/projections-cmip6

**Advantages**: 
- More user-friendly interface
- Pre-processed data
- Good documentation

### Method 3: Google Cloud CMIP6
**URL**: https://cloud.google.com/datasets/cmip6

**Advantages**:
- Programmatic access
- Fast downloads
- Consistent file organization

## 🎨 Recommended CMIP6 Models (Arctic Performance)

### Priority 1: ACCESS-CM2 (Australia)
- **Institution**: CSIRO-ARCCSS
- **Arctic Rating**: Excellent
- **Grid**: gn (native)
- **Strong Points**: Arctic sea ice, temperature trends
- **Download Priority**: ⭐⭐⭐⭐⭐

### Priority 2: CanESM5 (Canada) 
- **Institution**: CCCma
- **Arctic Rating**: Very Good
- **Grid**: gn (native)
- **Strong Points**: Arctic focus, high resolution
- **Download Priority**: ⭐⭐⭐⭐

### Priority 3: CESM2 (USA)
- **Institution**: NCAR
- **Arctic Rating**: Very Good  
- **Grid**: gn (native)
- **Strong Points**: Community validation, Arctic
- **Download Priority**: ⭐⭐⭐⭐

## 📝 File Naming Convention for PyGEM

PyGEM expects specific file naming patterns:

### Current PyGEM Format (in code)
```python
# From class_climate.py lines 376-392
self.temp_fn = name + '_' + sim_climate_scenario + '_r1i1p1f1_' + self.temp_vn + '.nc'
self.prec_fn = name + '_' + sim_climate_scenario + '_r1i1p1f1_' + self.prec_vn + '.nc'  
self.elev_fn = name + '_' + self.elev_vn + '.nc'
```

### Required File Names
```
# For ACCESS-CM2 model, SSP2-4.5 scenario:
ACCESS-CM2_ssp245_r1i1p1f1_tas.nc    # Temperature
ACCESS-CM2_ssp245_r1i1p1f1_pr.nc     # Precipitation  
ACCESS-CM2_orog.nc                   # Topography
```

### Directory Structure
```
/Users/kaimyers/PygemRound2/data/climate_data/cmip6/
├── ACCESS-CM2/
│   ├── ACCESS-CM2_ssp245_r1i1p1f1_tas.nc
│   ├── ACCESS-CM2_ssp245_r1i1p1f1_pr.nc
│   └── ACCESS-CM2_orog.nc
├── CanESM5/
│   ├── CanESM5_ssp245_r1i1p1f1_tas.nc
│   ├── CanESM5_ssp245_r1i1p1f1_pr.nc
│   └── CanESM5_orog.nc
```

## ⚙️ PyGEM Configuration Updates

### Update config.yaml
```yaml
climate:
  sim_climate_name: ACCESS-CM2          # Model name
  sim_climate_scenario: ssp245          # SSP scenario  
  sim_startyear: 2000                   # Start year
  sim_endyear: 2100                     # End year
  
  paths:
    cmip6_relpath: /climate_data/cmip6/  # Path to CMIP6 data
```

### Run Simulation Command
```bash
python3 PyGEM/pygem/bin/run/run_simulation.py \
  -rgi_glac_number 1.20947 \
  -sim_climate_name ACCESS-CM2 \
  -sim_climate_scenario ssp245 \
  -option_dynamics MassRedistributionCurves \
  -sim_startyear 2000 \
  -sim_endyear 2100 \
  -nsims 1
```

## 🌡️ Expected Results with Real CMIP6 Data

### SSP2-4.5 Scenario (Moderate Warming)
- **2050**: +2.0-2.5°C warming
- **2100**: +2.5-3.5°C warming
- **Precipitation**: Variable changes (±10-20%)
- **Glacier Response**: Accelerated mass loss, earlier peak water

### Comparison to Current Artificial Data
| Aspect | Current (Artificial) | Real CMIP6 |
|--------|---------------------|-------------|
| Warming | 0°C (no trend) | +2.5-3.5°C by 2100 |
| Seasonality | Fixed cycles | Progressive changes |
| Glacier Loss | Minimal (15.8% area) | Likely 40-60% area |
| Peak Water | Not evident | Clear peak ~2040-2060 |

## 📊 Download Size Estimates

### Per Model/Scenario
- **Temperature (tas)**: ~500 MB (monthly, 2015-2100)
- **Precipitation (pr)**: ~500 MB (monthly, 2015-2100)  
- **Topography (orog)**: ~50 MB (time-invariant)
- **Total per model**: ~1 GB

### Multiple Models
- **3 models × 3 scenarios**: ~9 GB total
- **Recommended minimum**: ACCESS-CM2 SSP2-4.5 (~1 GB)

## 🚀 Quick Start Commands

### 1. Create Directory Structure
```bash
mkdir -p /Users/kaimyers/PygemRound2/data/climate_data/cmip6/ACCESS-CM2
```

### 2. Download from ESGF (Example URLs)
```bash
# Replace these with actual ESGF download URLs
wget -P data/climate_data/cmip6/ACCESS-CM2/ \
  "https://esgf-node.llnl.gov/thredds/fileServer/cmip6/.../tas_Amon_ACCESS-CM2_ssp245_r1i1p1f1_gn_201501-210012.nc"

wget -P data/climate_data/cmip6/ACCESS-CM2/ \
  "https://esgf-node.llnl.gov/thredds/fileServer/cmip6/.../pr_Amon_ACCESS-CM2_ssp245_r1i1p1f1_gn_201501-210012.nc"
```

### 3. Rename Files to PyGEM Format
```bash
cd data/climate_data/cmip6/ACCESS-CM2/
mv tas_Amon_ACCESS-CM2_ssp245_r1i1p1f1_gn_201501-210012.nc ACCESS-CM2_ssp245_r1i1p1f1_tas.nc
mv pr_Amon_ACCESS-CM2_ssp245_r1i1p1f1_gn_201501-210012.nc ACCESS-CM2_ssp245_r1i1p1f1_pr.nc
```

## ⚠️ Important Notes

1. **ESGF Registration**: May require free ESGF account for downloads
2. **File Size**: Each model ~1 GB, plan storage accordingly  
3. **Processing Time**: Downloads may take hours depending on connection
4. **Grid Compatibility**: PyGEM handles different grids via nearest-neighbor interpolation
5. **Bias Correction**: PyGEM automatically bias-corrects CMIP6 data against ERA5 reference period

## 🎯 Success Criteria

After downloading real CMIP6 data, you should see:
- **Progressive warming trends** in temperature data
- **Realistic seasonal cycles** that evolve over time
- **Accelerated glacier mass loss** in simulations
- **Clear peak water timing** in discharge projections
- **Physically consistent** climate-glacier response

This will replace the current artificial repetitive climate forcing with proper physics-based projections.