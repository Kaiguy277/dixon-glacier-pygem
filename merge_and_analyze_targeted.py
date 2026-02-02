#!/usr/bin/env python3
"""
Merge results from the targeted sweep (original + resume) and analyze.
"""

import pandas as pd
from pathlib import Path

# Sweep directories
ORIGINAL_SWEEP = Path("/media/kai/Extreme SSD/Linux_Pygem/targeted_sweep/targeted_extended_20260128_154200")
RESUME_SWEEP = Path("/media/kai/Extreme SSD/Linux_Pygem/targeted_sweep/targeted_extended_resume_20260130_140714")
OUTPUT_DIR = Path("/home/kai/Documents/PYGEM/graphs")

print("=" * 70)
print("Merging Targeted Sweep Results")
print("=" * 70)

# Load the last checkpoint from original sweep (30,000 runs)
print(f"\nLoading original sweep (checkpoint 30,000 runs)...")
original_checkpoint = ORIGINAL_SWEEP / "results_checkpoint_30000.csv"
df_original = pd.read_csv(original_checkpoint)
print(f"  Loaded: {len(df_original):,} runs")

# Load results from resume sweep (6,105 runs)
print(f"\nLoading resume sweep (6,105 runs)...")
resume_results = RESUME_SWEEP / "results.csv"
df_resume = pd.read_csv(resume_results)
print(f"  Loaded: {len(df_resume):,} runs")

# Combine
print(f"\nCombining results...")
df_combined = pd.concat([df_original, df_resume], ignore_index=True)
print(f"  Total runs: {len(df_combined):,}")

# Summary
successful = df_combined['success'].sum()
print(f"  Successful: {successful:,} ({successful/len(df_combined)*100:.1f}%)")
print(f"  Failed: {len(df_combined) - successful:,}")

# Save combined results
output_file = OUTPUT_DIR / "targeted_sweep_combined_results.csv"
df_combined.to_csv(output_file, index=False)
print(f"\nCombined results saved to: {output_file}")

print("\nNext step: Update analyze_sweep_results.py to point to the combined run directories")
print("  Run directories are split between:")
print(f"    {ORIGINAL_SWEEP / 'runs'}")
print(f"    {RESUME_SWEEP / 'runs'}")
