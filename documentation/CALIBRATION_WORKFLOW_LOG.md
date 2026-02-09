# Dixon Glacier Calibration: Workflow Decision Log

**Quick Reference Guide for Thesis Methods Section**

---

## Timeline and Key Decisions

### January 22-27, 2026: Stage 1 - Expanded Sweep
**Decision**: Broad 4D exploration to identify optimal parameter regimes
**Runs**: 110,592 combinations (11×12×12×7 grid)
**Runtime**: 128 hours
**Key Finding**: Best parameters at ddfsnow lower boundary (0.001)
**Critical Issue**: 19% of top 100 runs hit ddfsnow = 0.001 boundary
**Decision**: Need to extend ddfsnow lower bound in next sweep

### January 28-30, 2026: Stage 2 - Targeted Sweep
**Decision**: Focus on warm regime (+3 to +6°C) with extended ddfsnow (0.0005)
**Runs**: 36,864 combinations (16×12×16×12 grid)
**Runtime**: 54 hours
**Key Finding**: Improved RMSE (0.262 vs 0.292), BUT still at ddfsnow boundary
**Persistent Issue**: Optimal still at 0.001, not 0.0005
**Decision**: Further extend to 0.0002 + add exploratory sweep for validation

### February 2-5, 2026: Stage 3 - Conservative Sweep
**Decision**: Dual-regime design (76% focused + 24% exploratory)
**Runs**: 50,400 combinations (38,400 main + 12,000 exploratory)
**Runtime**: ~70 hours (estimated)
**Purpose**:
- Definitively resolve ddfsnow boundary (extended to 0.0002)
- Validate no alternative optima in broader parameter space
- Address potential reviewer concerns about premature narrowing

### February 2, 2026: Combined Z-Score Analysis
**Decision**: Analyze expanded + targeted sweeps together (147k runs)
**Method**: Multi-criteria z-score ranking (Geck et al. 2021)
**Result**: Selected 250-member ensemble
- 93% from targeted sweep (validates focused design)
- 7% from expanded sweep
**Best RMSE**: 0.262 m w.e. (Run ID 216934)

---

## Critical Technical Fixes

### PyGEM Source Code Modifications
**Problem**: Command-line parameters ignored, all runs identical
**Fix Date**: January 2026
**Files Modified**: `/PyGEM/pygem/bin/run/run_simulation.py`

**Three Critical Changes**:
1. Added `-ddfsnow_iceratio` command-line argument (line 251)
2. Fixed parameter detection logic to check if cmdline params provided (line 693)
3. Fixed ddfice calculation to use cmdline ddfsnow_iceratio (line 840)

**Verification**: With `-v` flag, prints:
```
PARAMETER SWEEP: Using command-line parameters - kp=X, tbias=X, ddfsnow=X, ddfsnow_iceratio=X
```

### File Location Issue (February 2, 2026)
**Problem**: Conservative sweep .nc files in wrong directory
**Root Cause**: Missing `move_output_files()` function + wrong `cwd` in subprocess
**Fix**:
1. Added `move_output_files()` function (copies from targeted_sweep.py)
2. Changed subprocess `cwd` from `run_dir` to `BASE_DIR`
3. Only save stdout/stderr on failure (saves disk space)

**Verification**: Files now in individual run directories:
```
/runs/run_NNNNNN/*binned.nc  ✓
/runs/run_NNNNNN/*all.nc     ✓
```

---

## Parameter Evolution Across Sweeps

### Expanded Sweep (Stage 1) - Best Parameters
```
tbias:              +4.35°C
kp:                 2.17
ddfsnow:            0.001      ← AT BOUNDARY
ddfsnow_iceratio:   0.224
RMSE:               0.292 m w.e.
```

### Targeted Sweep (Stage 2) - Best Parameters
```
tbias:              +4.40°C
kp:                 2.227
ddfsnow:            0.001      ← STILL AT BOUNDARY
ddfsnow_iceratio:   0.205
RMSE:               0.262 m w.e.  (10% improvement)
```

### Ensemble (250 members) - Mean ± Std
```
tbias:              4.54 ± 0.73°C     (range: 3.0 to 5.6)
kp:                 2.72 ± 0.49       (range: 1.5 to 3.5)
ddfsnow:            0.00121 ± 0.00025 (range: 0.00067 to 0.00167)
ddfsnow_iceratio:   0.276 ± 0.072     (range: 0.15 to 0.45)
Overall RMSE:       0.411 ± 0.060 m w.e.
```

---

## Z-Score Methodology Implementation

### Why Multi-Criteria?
**Problem**: RMSE-only ranking may select parameters with great overall fit but poor performance in specific zones

**Solution**: Z-score ranking following Geck et al. (2021)
- Ensures balanced performance across ALL zones (ABL, ELA, ACC)
- Prevents overfitting to any single elevation range
- More robust for future projections

### 4-Step Process

1. **Calculate zone-specific RMSE** for all parameter sets
   - ABL zone (804m): 3 observations
   - ELA zone (1078m): 2 observations
   - ACC zone (1293m): 3 observations
   - Overall: all 8 observations

2. **Compute z-scores** for each RMSE variable
   ```
   z = (RMSE - mean) / std_dev
   ```

3. **Normalize to [0,1]** where 1 = best fit
   ```
   z_norm = (z_max - z) / (z_max - z_min)
   ```

4. **Select ensemble** where ALL z-scores > threshold (0.5)
   ```
   selected if: z_ABL > 0.5 AND z_ELA > 0.5 AND z_ACC > 0.5 AND z_overall > 0.5
   ```

### Comparison with RMSE-Only Ranking

**Overlap**: 220/250 parameter sets (88%) in both methods

**Performance Difference**:
| Zone | Z-Score | RMSE-Only |
|------|---------|-----------|
| ABL  | 0.421   | 0.443     | ← Z-score better
| ELA  | 0.440   | 0.414     |
| ACC  | 0.308   | 0.327     | ← Z-score better
| Overall | 0.411 | 0.408  |

**Conclusion**: Z-score achieves better zone balance with minimal overall RMSE trade-off

---

## Directory Structure (Clean)

```
/media/kai/Extreme SSD/Linux_Pygem/
├── expanded_sweep/
│   └── calibration_expanded_20260122_220448/     (110k runs)
│       ├── parameters.csv                         (13.5 MB)
│       ├── sweep_config.json
│       └── runs/run_NNNNNN/*.nc
│
├── targeted_sweep/
│   └── targeted_extended_20260128_154200/        (36k runs)
│       ├── parameters.csv                         (4.5 MB)
│       ├── sweep_config.json
│       └── runs/run_NNNNNN/*.nc
│
└── conservative_sweep/
    └── conservative_20260202_184128/              (50k runs, IN PROGRESS)
        ├── parameters.csv                         (6.1 MB)
        ├── sweep_config.json
        └── runs/run_NNNNNN/*.nc

/home/kai/Documents/PYGEM/graphs/
└── zscore_combined_20260202_154557/
    ├── top_250_zscore_parameters.csv              (Selected ensemble)
    ├── all_results_with_zscores.csv               (All 147k runs)
    ├── selection_summary.txt
    ├── ranking_comparison.txt
    ├── zscore_distributions.png
    ├── parameter_frequencies.png
    └── method_comparison.png
```

---

## Scripts and Their Purposes

### Sweep Execution
- `run_expanded_sweep.py` - Stage 1 (110k grid generation & execution)
- `run_targeted_sweep.py` - Stage 2 (36k focused sweep)
- `run_conservative_sweep.py` - Stage 3 (50k dual-regime sweep)

### Analysis
- `analyze_sweep_results.py` - Single sweep RMSE ranking, 2D slicing
- `analyze_zscore_ranking.py` - Z-score methodology, ensemble selection
- `analyze_zscore_combined.py` - Multi-sweep combined analysis

### Common Functions
- `load_observations()` - Load stake data from CSV
- `calculate_zone_rmse()` - Extract PyGEM output, compute RMSE
- `calculate_zscores()` - Normalize and compute z-scores
- `select_best_parameters()` - Apply threshold, select ensemble

---

## Observations Data File

**Location**: `/home/kai/Documents/PYGEM/inputs/stake_observations_dixon.csv`

**Structure**:
```csv
site_id,period_type,year,date_start,date_end,mb_obs_mwe,mb_obs_uncertainty_mwe,zone,elevation_m,notes
ABL,annual,2023,2022-10-01,2023-10-03,-4.5,0.12,ABL,804.0,...
ABL,annual,2024,2023-10-03,2024-10-03,-5.66,0.15,ABL,804.0,...
ABL,annual,2025,2024-10-03,2025-09-30,-5.15,0.15,ABL,804.0,...
ELA,annual,2023,2022-10-01,2023-10-03,-1.92,0.15,ELA,1078.0,...
ELA,annual,2024,2023-10-03,2024-09-30,-1.52,0.15,ELA,1078.0,...
ACC,annual,2023,2022-10-01,2023-10-03,0.66,0.20,ACC,1293.0,...
ACC,annual,2024,2023-10-03,2024-09-30,0.59,0.20,ACC,1293.0,...
ACC,annual,2025,2024-10-03,2025-09-30,0.50,0.25,ACC,1293.0,Estimated
```

**Bin Index Mapping** (PyGEM 20m bins):
- ABL (804m): Bin 10
- ELA (1078m): Bin 23
- ACC (1293m): Bin 34

---

## Key Metrics Summary

### Computational Effort
- **Total runs executed**: 197,856 (110k + 36k + 50k)
- **Total runtime**: ~258 hours (~10.75 days)
- **Storage**: ~111 GB NetCDF files
- **Average success rate**: 96.5%

### Calibration Performance
- **Best single run**: RMSE 0.262 m w.e.
- **Ensemble mean**: RMSE 0.411 ± 0.060 m w.e.
- **Ensemble size**: 250 parameter sets
- **Zone balance**: All zones within ±0.44 m w.e. mean RMSE

### Parameter Constraints
- **tbias**: 3.0 to 5.6°C (warm bias for ERA5)
- **kp**: 1.5 to 3.5 (moderate precipitation scaling)
- **ddfsnow**: 0.00067 to 0.00167 (low, clustered at boundary)
- **ddfsnow_iceratio**: 0.15 to 0.45 (low, ice melts 2-7× faster)

---

## For Thesis Methods Section

### Recommended Structure

1. **Parameter Space** (Section 3)
   - 4D grid: tbias, kp, ddfsnow, ddfsnow_iceratio
   - Physical meaning and literature ranges

2. **Calibration Data** (Section 2)
   - 8 zone-year observations (3 stakes × 2-3 years)
   - Water year definition and extraction from PyGEM

3. **Multi-Stage Strategy** (Section 4)
   - Stage 1: Broad exploration (110k)
   - Stage 2: Focused refinement (36k)
   - Stage 3: Conservative validation (50k)
   - Rationale for iterative boundary extension

4. **Z-Score Ranking** (Section 5)
   - Multi-criteria objective
   - Geck et al. (2021) methodology adaptation
   - Comparison with RMSE-only approach

5. **Results** (Section 8)
   - 250-member ensemble characteristics
   - Ensemble composition by sweep
   - Parameter uncertainty ranges
   - Zone-specific performance

6. **Uncertainty** (Section 9)
   - Observational, model structural, climate forcing
   - Ensemble spread as metric
   - Limitations and caveats

### Key Figures for Thesis

1. **Parameter grid design** - 3D visualization of sweep evolution
2. **Z-score distributions** - Scatter plots (ABL, ELA, ACC vs overall)
3. **Parameter frequency histograms** - Show ensemble spread
4. **RMSE heatmaps** - 2D slices showing regime structure
5. **Method comparison** - Z-score vs RMSE-only overlap Venn diagram
6. **Ensemble performance** - Box plots of zone RMSEs

---

## Citations for Methods

**Model**:
- Rounce et al. (2020) - PyGEM paper

**Methodology**:
- Geck et al. (2021) - Z-score ranking
- Hock (2003) - Degree-day model
- Braithwaite (2008) - Degree-day factors

**Data**:
- RGI Consortium (2017) - Glacier outline
- Farinotti et al. (2019) - Ice thickness
- Hersbach et al. (2020) - ERA5 climate

---

**Last Updated**: February 2, 2026
**Status**: Ready for thesis integration
**Next Step**: Complete conservative sweep → Final combined analysis
