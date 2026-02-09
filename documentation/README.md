# Dixon Glacier PyGEM Calibration - Documentation

This directory contains comprehensive documentation of the parameter calibration workflow for Dixon Glacier mass balance modeling using PyGEM. All documentation is thesis/publication-ready with scientific rigor.

---

## Documentation Files

### 📊 **CALIBRATION_METHODS_DOCUMENTATION.md** (Primary Methods Document)
**Size**: 37 KB | **Lines**: ~900 | **Status**: Publication-ready

**Comprehensive methods documentation suitable for thesis Chapter 3 (Methods) and journal article methods sections.**

**Contents**:
1. Overview and Objectives - Calibration philosophy and goals
2. Calibration Data - Zone-specific observations (8 zone-years)
3. Parameter Space and Physical Constraints - 4D parameter definitions
4. Multi-Stage Calibration Strategy - Three sequential sweeps (197k runs)
5. Z-Score Ranking Methodology - Multi-criteria optimization (Geck et al. 2021)
6. Technical Implementation - PyGEM modifications, execution framework
7. Quality Control and Verification - Success rates, validation
8. Results and Ensemble Selection - 250-member ensemble characteristics
9. Uncertainty Quantification - Sources and metrics
10. References - Complete citations

**Use for**:
- Thesis methods chapter (comprehensive version)
- Journal manuscript methods section (condensed)
- Technical documentation for reproducibility

---

### 📝 **CALIBRATION_WORKFLOW_LOG.md** (Quick Reference)
**Size**: 11 KB | **Lines**: ~350 | **Status**: Ready

**Concise decision log and quick reference guide for the calibration workflow.**

**Contents**:
- Timeline and key decisions for each sweep stage
- Critical technical fixes (PyGEM modifications, file location bug)
- Parameter evolution across sweeps
- Z-score methodology summary (4-step process)
- Clean directory structure
- Scripts and their purposes
- Observations data format
- Key metrics summary
- Thesis structure recommendations

**Use for**:
- Quick reference during thesis writing
- Supplementary information for reviewers
- Lab notebook documentation
- Onboarding future researchers

---

### 🔬 **ZSCORE_ANALYSIS_README.md** (Z-Score Methodology)
**Size**: 4.5 KB | **Lines**: ~127 | **Status**: Ready

**Detailed explanation of z-score ranking methodology and its advantages over RMSE-only selection.**

**Contents**:
- Overview of multi-criteria optimization
- Traditional vs z-score ranking comparison
- Usage instructions for analysis scripts
- Output files description
- Key differences from Geck et al. (2021) Eklutna study
- Expected results and interpretation
- References

**Use for**:
- Methods subsection on ensemble selection
- Justification for multi-criteria approach
- Script usage documentation

---

### ⚙️ **SETUP_GUIDE_4D_PARAMETER_SWEEP.md** (Technical Setup)
**Size**: 27 KB | **Lines**: ~876 | **Status**: Ready

**Complete technical setup guide for PyGEM parameter sweeps with 4D command-line control.**

**Contents**:
- Overview and key features
- Critical breakthrough (command-line parameter control)
- Complete data requirements (RGI, thickness, climate, observations)
- PyGEM source code modifications (3 critical fixes)
- Parameter sweep framework documentation
- Configuration files and settings
- Usage guide (test, small, medium, large sweeps)
- Data sources documentation with download instructions
- Troubleshooting guide

**Use for**:
- Technical appendix for thesis
- Reproducibility documentation
- Setup guide for other glaciers
- PyGEM parameter sweep tutorial

---

### 📋 **DATA_SETUP_COMPARISON.md** (Data Provenance)
**Size**: 8.9 KB | **Status**: Reference

**Comparison of data sources and setup configurations.**

**Use for**:
- Data provenance documentation
- Supplementary information on input data

---

## File Organization by Purpose

### For Thesis Chapter 3 (Methods)
**Primary**: `CALIBRATION_METHODS_DOCUMENTATION.md`
- Main text: Sections 1-5, 8
- Appendices: Sections 6-7, 9-10

**Supporting**: `CALIBRATION_WORKFLOW_LOG.md`
- Quick reference for specific details
- Timeline for methods narrative

### For Journal Manuscript Methods
**Condense from**: `CALIBRATION_METHODS_DOCUMENTATION.md`
- Keep: Sections 1-5, 8 (condensed)
- Move to SI: Sections 6-7, 9-10
- Reference: `ZSCORE_ANALYSIS_README.md` for z-score justification

### For Reproducibility
**Primary**: `SETUP_GUIDE_4D_PARAMETER_SWEEP.md`
- Complete technical documentation
- PyGEM modifications with exact line numbers
- Data download instructions

**Supporting**: All parameter files in sweep directories
- `parameters.csv` files contain all tested combinations
- `sweep_config.json` files contain grid definitions

### For Reviewers
**Provide**:
1. `CALIBRATION_METHODS_DOCUMENTATION.md` (main methods)
2. `CALIBRATION_WORKFLOW_LOG.md` (decision rationale)
3. `top_250_zscore_parameters.csv` (selected ensemble)
4. Selected figures from `graphs/zscore_combined_*/` directory

---

## Key Figures (Thesis-Ready)

**Location**: `/home/kai/Documents/PYGEM/graphs/zscore_combined_all3_20260208_183456/`

1. **zscore_distributions.png** (290 KB) - Scatter plots of normalized z-scores
   - Shows selection threshold and ensemble distribution across all 3 sweeps
   - Use for: Methods section (z-score methodology)

2. **parameter_frequencies.png** (119 KB) - Histograms of parameter value distributions
   - Shows ensemble spread and uncertainty from 250-member ensemble
   - Use for: Results section (parameter uncertainty)

3. **method_comparison.png** (83 KB) - Comparison of z-score vs RMSE-only ranking
   - Shows method performance differences and 84% overlap
   - Use for: Methods section (justification for z-score approach)

---

## Associated Data Files

### Calibration Observations
**Location**: `/home/kai/Documents/PYGEM/inputs/stake_observations_dixon.csv`
- 8 zone-year mass balance measurements
- 3 elevation zones (ABL, ELA, ACC)
- Water years 2023-2025

### Selected Ensemble
**Location**: `/home/kai/Documents/PYGEM/graphs/zscore_combined_all3_20260208_183456/`
- `top_250_zscore_parameters.csv` - Final 250-member ensemble (all 3 sweeps)
- `all_results_with_zscores.csv` - All 193k runs with z-scores (76 MB)
- `selection_summary.txt` - Statistical summary
- `ranking_comparison.txt` - Method comparison details

**Previous Analysis** (2 sweeps): `/home/kai/Documents/PYGEM/graphs/zscore_combined_20260202_154557/`

### Parameter Sweep Archives
**Location**: `/media/kai/Extreme SSD/Linux_Pygem/`
- `expanded_sweep/calibration_expanded_20260122_220448/` - 110k runs
- `targeted_sweep/targeted_extended_20260128_154200/` - 36k runs
- `conservative_sweep/conservative_20260203_132620/` - 50k runs

---

## Computational Statistics Summary

| Metric | Value |
|--------|-------|
| **Total parameter combinations tested** | 197,856 |
| **Successful runs analyzed** | 192,998 (97.5% success rate) |
| **Total computation time** | ~258 hours (~10.75 days) |
| **Total storage required** | ~111 GB (NetCDF outputs) |
| **Final ensemble size** | 250 parameter sets |
| **Ensemble composition** | 50% conservative, 47% targeted, 3% expanded |
| **Best single-run RMSE** | 0.251 m w.e. (Run 415052) |
| **Ensemble mean RMSE** | 0.370 ± 0.049 m w.e. |
| **Zone balance (mean RMSE)** | ABL: 0.313, ELA: 0.399, ACC: 0.332 |

---

## Citation Information

When referencing this calibration workflow in publications:

### For Methods
"Parameter calibration employed a multi-stage ensemble approach with 197,856 model runs across three sequential parameter sweeps (expanded, targeted, and conservative exploration). A final ensemble of 250 parameter sets was selected using multi-criteria z-score ranking following Geck et al. (2021) to ensure balanced performance across elevation zones, achieving mean RMSE of 0.370 ± 0.049 m w.e. with balanced contributions from all three sweeps (50% conservative, 47% targeted, 3% expanded)."

### For Z-Score Methodology
Adapted from:
> Geck, J., Hock, R., Loso, M. G., Ostman, J., & Dial, R. (2021). Modeling the impacts of climate change on mass balance and discharge of Eklutna Glacier, Alaska, 1985–2019. *Journal of Glaciology*, 67(265), 909-920. https://doi.org/10.1017/jog.2021.41

### For PyGEM Model
> Rounce, D. R., Hock, R., & Shean, D. E. (2020). Glacier mass change in High Mountain Asia through 2100 using the open-source Python Glacier Evolution Model (PyGEM). *Frontiers in Earth Science*, 7, 331. https://doi.org/10.3389/feart.2019.00331

---

## Document Status

| Document | Status | Last Updated | Version |
|----------|--------|--------------|---------|
| CALIBRATION_METHODS_DOCUMENTATION.md | ✅ Ready | Feb 2, 2026 | 1.0 |
| CALIBRATION_WORKFLOW_LOG.md | ✅ Updated | Feb 8, 2026 | 1.1 |
| ZSCORE_ANALYSIS_README.md | ✅ Ready | Feb 2, 2026 | 1.0 |
| SETUP_GUIDE_4D_PARAMETER_SWEEP.md | ✅ Ready | Jan 15, 2026 | 1.0 |
| DATA_SETUP_COMPARISON.md | 📋 Reference | Jan 15, 2026 | 1.0 |
| README.md | ✅ Updated | Feb 8, 2026 | 1.1 |

---

## Thesis Integration Checklist

### ✅ Completed
- [x] Execute all three parameter sweeps (197,856 runs)
- [x] Run combined z-score analysis (192,998 successful runs)
- [x] Generate thesis-ready figures (z-score distributions, parameter frequencies, method comparison)
- [x] Update all documentation files with final results
- [x] Document ensemble composition and statistics

### 📝 Ready for Thesis
1. **Methods Chapter** (Use CALIBRATION_METHODS_DOCUMENTATION.md):
   - Multi-stage calibration strategy (3 sequential sweeps)
   - Z-score ranking methodology
   - Ensemble selection process
   - Technical implementation details

2. **Results Chapter** (Use graphs/zscore_combined_all3_20260208_183456/):
   - Final ensemble statistics (250 parameter sets)
   - Best parameter set (Run 415052: RMSE 0.251 m w.e.)
   - Parameter uncertainty ranges
   - Zone-specific performance

3. **Figures** (All files in zscore_combined_all3_20260208_183456/):
   - Figure 1: Z-score distributions (zscore_distributions.png)
   - Figure 2: Parameter frequencies (parameter_frequencies.png)
   - Figure 3: Method comparison (method_comparison.png)

### 🔄 Next Steps
1. **Prepare for Publication**:
   - Compress sweep directories (tar.gz)
   - Upload to institutional repository
   - Create DOI for data/code archive

2. **Run Future Projections**:
   - Use top_250_zscore_parameters.csv for ensemble projections
   - Apply to future climate scenarios

---

**Documentation Compiled by**: Kai Myers
**Project**: Dixon Glacier PyGEM Calibration and Future Projections
**Institution**: [Your University]
**Date**: February 8, 2026
**Status**: ✅ COMPLETE - All sweeps executed and analyzed. Ready for thesis integration.
