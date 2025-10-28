#!/usr/bin/env python3
"""
Convert Downloaded CMIP6 Data to PyGEM Format

This script takes the real ACCESS-CM2 CMIP6 data you downloaded and converts it 
to the exact format PyGEM expects, replacing the artificial climate data.
"""

import xarray as xr
import numpy as np
from pathlib import Path
import shutil

def convert_cmip6_for_pygem():
    """Convert CMIP6 data to PyGEM format"""
    
    print("🔄 CONVERTING CMIP6 DATA TO PYGEM FORMAT")
    print("=" * 50)
    
    # Input paths (downloaded CMIP6 data)
    temp_file = "/Users/kaimyers/PygemRound2/inputs/CMIP6/SSP245_near-surface-air-temp_2015to2100/tas_Amon_ACCESS-CM2_ssp245_r1i1p1f1_gn_20150116-21001216.nc"
    precip_file = "/Users/kaimyers/PygemRound2/inputs/CMIP6/SSP245_precip_2015to2100/pr_Amon_ACCESS-CM2_ssp245_r1i1p1f1_gn_20150116-21001216.nc"
    
    # Output directory (PyGEM expected format)
    output_dir = Path("/Users/kaimyers/PygemRound2/data/climate_data/cmip6/ACCESS-CM2")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load the data
    print("📡 Loading CMIP6 temperature data...")
    temp_ds = xr.open_dataset(temp_file)
    
    print("🌧️  Loading CMIP6 precipitation data...")
    precip_ds = xr.open_dataset(precip_file)
    
    # Convert coordinate names to PyGEM format
    print("🔧 Converting to PyGEM coordinate format...")
    
    # For CMIP6 models, PyGEM expects 'lat' and 'lon' (not 'latitude' and 'longitude')
    # Keep original names since ACCESS-CM2 already uses 'lat' and 'lon'
    temp_pygem = temp_ds.copy()
    precip_pygem = precip_ds.copy()
    
    # Convert longitude from 0-360 to -180-180 format (PyGEM prefers this)
    print("🌍 Converting longitude coordinates...")
    temp_pygem = temp_pygem.assign_coords(lon=((temp_pygem.lon + 180) % 360) - 180)
    temp_pygem = temp_pygem.sortby('lon')
    
    precip_pygem = precip_pygem.assign_coords(lon=((precip_pygem.lon + 180) % 360) - 180)
    precip_pygem = precip_pygem.sortby('lon')
    
    # Check data quality
    print("🔍 Checking data quality...")
    temp_data = temp_pygem.tas.values
    precip_data = precip_pygem.pr.values
    
    temp_nan_pct = (np.isnan(temp_data).sum() / temp_data.size) * 100
    precip_nan_pct = (np.isnan(precip_data).sum() / precip_data.size) * 100
    
    print(f"   Temperature NaN values: {temp_nan_pct:.1f}%")
    print(f"   Precipitation NaN values: {precip_nan_pct:.1f}%")
    
    if temp_nan_pct > 5 or precip_nan_pct > 5:
        print("   ⚠️  Warning: High percentage of NaN values detected")
    else:
        print("   ✅ Data quality looks good")
    
    # Check for warming trends (this should show progressive warming unlike artificial data)
    print("🌡️  Checking for climate warming trends...")
    annual_temp_series = temp_pygem.tas.groupby('time.year').mean()
    
    temp_2015_2025 = annual_temp_series.sel(year=slice(2015, 2025)).mean().values
    temp_2090_2100 = annual_temp_series.sel(year=slice(2090, 2100)).mean().values
    warming_trend = temp_2090_2100 - temp_2015_2025
    
    print(f"   2015-2025 mean temp: {temp_2015_2025-273.15:.1f}°C")
    print(f"   2090-2100 mean temp: {temp_2090_2100-273.15:.1f}°C") 
    print(f"   Warming trend: {warming_trend:.1f}K (+{warming_trend:.1f}°C)")
    
    if warming_trend > 1.0:
        print("   ✅ Real warming trend detected (proper CMIP6 data)")
    else:
        print("   ❌ No warming trend - may still be artificial data")
    
    # Save in PyGEM format
    output_temp = output_dir / "ACCESS-CM2_ssp245_r1i1p1f1_tas.nc"
    output_precip = output_dir / "ACCESS-CM2_ssp245_r1i1p1f1_pr.nc"
    
    print(f"💾 Saving temperature data to: {output_temp}")
    # Keep only essential variables for PyGEM
    temp_clean = temp_pygem[['tas']].copy()
    temp_clean.to_netcdf(output_temp)
    
    print(f"💾 Saving precipitation data to: {output_precip}")
    precip_clean = precip_pygem[['pr']].copy()
    precip_clean.to_netcdf(output_precip)
    
    # Create orography file (copy from ERA5 since topography doesn't change)
    era5_orog = "/Users/kaimyers/PygemRound2/data/climate_data/ERA5_real_extended/ERA5_geopotential.nc"
    output_orog = output_dir / "ACCESS-CM2_orog.nc"
    
    if Path(era5_orog).exists():
        print(f"📄 Copying orography from ERA5: {output_orog}")
        try:
            orog_ds = xr.open_dataset(era5_orog)
            # ERA5 uses 'latitude'/'longitude', need to rename to 'lat'/'lon' for CMIP6 consistency
            orog_pygem = orog_ds.rename({'latitude': 'lat', 'longitude': 'lon'})
            orog_clean = orog_pygem[['z']].rename({'z': 'orog'})
            orog_clean.to_netcdf(output_orog)
            orog_ds.close()
            print("   ✅ Orography file created")
        except Exception as e:
            print(f"   ⚠️  Could not copy orography: {e}")
    else:
        print("   ⚠️  ERA5 orography file not found - you may need to download it separately")
    
    temp_ds.close()
    precip_ds.close()
    
    print(f"\n✅ CONVERSION COMPLETE!")
    print(f"Files created in: {output_dir}")
    print(f"  • {output_temp.name}")
    print(f"  • {output_precip.name}")
    if Path(output_orog).exists():
        print(f"  • {output_orog.name}")
    
    return output_dir

def update_pygem_config():
    """Show how to update PyGEM config for CMIP6 data"""
    
    print(f"\n⚙️  PYGEM CONFIGURATION UPDATE")
    print("=" * 40)
    
    config_updates = """
# Update your config.yaml with these settings:

climate:
  sim_climate_name: ACCESS-CM2
  sim_climate_scenario: ssp245  
  sim_startyear: 2000
  sim_endyear: 2100
  
  paths:
    cmip6_relpath: /climate_data/cmip6/
"""
    
    print(config_updates)
    
    run_command = """
# Run PyGEM with real CMIP6 data:
python3 PyGEM/pygem/bin/run/run_simulation.py \\
  -rgi_glac_number 1.20947 \\
  -sim_climate_name ACCESS-CM2 \\
  -sim_climate_scenario ssp245 \\
  -option_dynamics MassRedistributionCurves \\
  -sim_startyear 2000 \\
  -sim_endyear 2100 \\
  -nsims 1
"""
    
    print(run_command)

def main():
    """Main conversion process"""
    
    print("🌍 REAL CMIP6 DATA INTEGRATION FOR PYGEM")
    print("=" * 60)
    print("This will replace artificial climate data with real ACCESS-CM2 projections")
    print("showing proper warming trends through 2100.\n")
    
    # Convert the data
    output_dir = convert_cmip6_for_pygem()
    
    # Show configuration updates
    update_pygem_config()
    
    print(f"\n🎯 NEXT STEPS:")
    print("1. Update your config.yaml with the settings above")
    print("2. Run the PyGEM simulation command")
    print("3. Compare results with previous artificial data simulation")
    print("4. You should now see realistic warming-driven glacier changes!")

if __name__ == "__main__":
    main()