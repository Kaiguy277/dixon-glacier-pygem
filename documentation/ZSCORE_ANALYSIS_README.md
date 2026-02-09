# Z-Score Parameter Ranking for Dixon Glacier

## Overview

This analysis implements the **multi-criteria z-score optimization** methodology from Geck et al. (2021) for Eklutna Glacier, adapted for Dixon Glacier's zone-based observations.

## Methodology

### Traditional RMSE Ranking (Current)
```python
# Simple approach: rank all parameter sets by overall RMSE
best_params = results.nsmallest(1000, 'rmse_overall')
```

**Limitation**: May select parameter sets that fit well overall but poorly in specific zones.

### Z-Score Ranking (New - Following Geck et al. 2021)

```
For each zone (ABL, ELA, ACC) and overall:
  1. Calculate RMSE for all parameter sets
  2. Compute z-scores: Z_i = (RMSE_i - RMSE_mean) / std_dev
  3. Normalize to [0,1] where 1 = best fit
  4. Select parameter sets where ALL z-scores > threshold
```

**Advantage**: Ensures good performance across ALL zones, not just overall.

## Usage

### Basic Usage
```bash
# Run with defaults (threshold=0.5, top 250 parameter sets)
python3 analyze_zscore_ranking.py

# Custom threshold
python3 analyze_zscore_ranking.py --threshold 0.6 --top_n 100

# Specify sweep directory
python3 analyze_zscore_ranking.py --sweep_dir /path/to/sweep
```

### Output Files

The script creates a new directory `graphs/zscore_analysis_YYYYMMDD_HHMMSS/` containing:

1. **all_results_with_zscores.csv** - Full results with z-scores for all parameter sets
2. **top_N_zscore_parameters.csv** - Selected best parameter sets
3. **zscore_distributions.png** - Z-score scatter plots (similar to Geck Fig 5)
4. **parameter_frequencies.png** - Parameter value distributions (similar to Geck Fig 4)
5. **method_comparison.png** - Comparison of z-score vs RMSE ranking
6. **selection_summary.txt** - Statistics for selected parameter sets
7. **ranking_comparison.txt** - Detailed comparison of both methods

## Key Differences from Eklutna Study

| Aspect | Eklutna (Geck et al. 2021) | Dixon (This Study) |
|--------|---------------------------|-------------------|
| **Variables** | Point balances + snowlines | Zone-specific RMSE (ABL, ELA, ACC) |
| **Observations** | 50 point measurements | 3 zones × monthly |
| **Z-score criteria** | 2 variables (stakes, snowlines) | 4 variables (3 zones + overall) |
| **Ensemble size** | 250 parameter sets | 250 parameter sets (default) |
| **Threshold** | 0.5 | 0.5 (default, adjustable) |

## Expected Results

### Multi-criteria Benefits
- **Balanced performance** across all elevation zones
- **Reduced overfitting** to any single zone
- **Better uncertainty quantification** through ensemble spread
- **More robust parameters** for future predictions

### Potential Tradeoffs
- May have slightly higher overall RMSE than best single parameter set
- Excludes parameter sets that excel in one zone but fail in others
- Smaller ensemble if threshold is too strict

## Interpretation

### Z-Score Plots
- **High z-score (close to 1)**: Better than average fit
- **Low z-score (close to 0)**: Worse than average fit
- **Selected sets**: All normalized z-scores > threshold for ALL zones

### Parameter Frequencies
- Shows distribution of parameter values in selected ensemble
- Multiple peaks suggest equifinality (different parameter combinations achieving similar fits)
- Wide distributions indicate parameter uncertainty

## Comparison with Current Method

Run both analyses and compare:

```bash
# Current method (RMSE-only)
python3 analyze_sweep_results.py

# New method (z-score)
python3 analyze_zscore_ranking.py
```

**Check**:
1. What percentage of top parameter sets overlap?
2. Do z-score selected sets have more balanced zone performance?
3. Are parameter uncertainties different between methods?

## References

Geck, J., Hock, R., Loso, M. G., Ostman, J., & Dial, R. (2021).
Modeling the impacts of climate change on mass balance and discharge of
Eklutna Glacier, Alaska, 1985–2019. *Journal of Glaciology*, 67(265), 909-920.
https://doi.org/10.1017/jog.2021.41

## Next Steps

1. **Run the analysis**: `python3 analyze_zscore_ranking.py`
2. **Compare results**: Examine overlap with RMSE-only method
3. **Validate**: Check if selected ensemble performs better on withheld data
4. **Use for projections**: Run historical simulations with both ensembles and compare

## Notes

- First run will take ~30-60 minutes depending on number of parameter sets
- Results are cached in the output directory
- You can re-run with different thresholds without re-computing RMSE
- The script automatically lowers threshold if no sets meet criteria
