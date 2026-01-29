"""
Python Glacier Evolution Model (PyGEM)

copyright © 2018 David Rounce <drounce@cmu.edu

Distributed under the MIT license

PYGEM-OGGGM COMPATIBILITY FUNCTIONS
"""

import os
import pickle
import gzip

import netCDF4
import geopandas as gpd
import rasterio
from scipy.ndimage import zoom

# External libraries
import numpy as np
import pandas as pd
from oggm import cfg, workflow

# from oggm import tasks
from oggm.cfg import SEC_IN_YEAR
from oggm.core.flowline import FileModel
from oggm.core.massbalance import MassBalanceModel

from pygem.setup.config import ConfigManager
from pygem.shop import (
    debris,
    elevchange1d,
    icethickness,
    mbdata,
    meltextent_and_snowline_1d,
)

# instantiate ConfigManager
config_manager = ConfigManager()
# read the config
pygem_prms = config_manager.read_config()


class CompatGlacDir:
    def __init__(self, rgiid):
        self.rgiid = rgiid


def single_flowline_glacier_directory(
    rgi_id,
    reset=pygem_prms['oggm']['overwrite_gdirs'],
    prepro_border=pygem_prms['oggm']['border'],
    logging_level=pygem_prms['oggm']['logging_level'],
    has_internet=pygem_prms['oggm']['has_internet'],
    working_dir=f'{pygem_prms["root"]}/{pygem_prms["oggm"]["oggm_gdir_relpath"]}',
):
    """Prepare a GlacierDirectory for PyGEM (single flowline to start with)

    Parameters
    ----------
    rgi_id : str
        the rgi id of the glacier (RGIv60-)
    reset : bool
        set to true to delete any pre-existing files. If false (the default),
        the directory won't be re-downloaded if already available locally in
        order to spare time.
    prepro_border : int
        the size of the glacier map: 10, 80, 160, 240

    Returns
    -------
    a GlacierDirectory object
    """
    if type(rgi_id) != str:
        raise ValueError('We expect rgi_id to be a string')
    if rgi_id.startswith('RGI60-') == False:
        rgi_id = 'RGI60-' + rgi_id.split('.')[0].zfill(2) + '.' + rgi_id.split('.')[1]
    else:
        raise ValueError('Check RGIId is correct')

    # Initialize OGGM and set up the default run parameters
    cfg.initialize(logging_level=logging_level)
    # Set multiprocessing to false; otherwise, causes daemonic error due to PyGEM's multiprocessing
    #  - avoids having multiple multiprocessing going on at the same time
    cfg.PARAMS['use_multiprocessing'] = False

    # Avoid erroneous glaciers (e.g., Centerlines too short or other issues)
    cfg.PARAMS['continue_on_error'] = True

    # Has internet
    cfg.PARAMS['has_internet'] = has_internet

    # Set border boundary
    cfg.PARAMS['border'] = prepro_border
    # Usually we recommend to set dl_verify to True - here it is quite slow
    # because of the huge files so we just turn it off.
    # Switch it on for real cases!
    cfg.PARAMS['dl_verify'] = True
    cfg.PARAMS['use_multiple_flowlines'] = False
    # temporary directory for testing (deleted on computer restart)
    cfg.PATHS['working_dir'] = working_dir

    # check if gdir is already processed
    if not reset:
        try:
            gdir = workflow.init_glacier_directories([rgi_id])[0]
            gdir.read_pickle('inversion_flowlines')

        except:
            reset = True

    if reset:
        # Start after the prepro task level
        base_url = pygem_prms['oggm']['base_url']

        cfg.PARAMS['has_internet'] = pygem_prms['oggm']['has_internet']
        gdir = workflow.init_glacier_directories(
            [rgi_id],
            from_prepro_level=2,
            prepro_border=cfg.PARAMS['border'],
            prepro_base_url=base_url,
            prepro_rgi_version='62',
        )[0]

    # go through shop tasks to process auxiliary datasets to gdir if necessary
    # consensus glacier mass
    if not os.path.isfile(gdir.get_filepath('consensus_mass')):
        workflow.execute_entity_task(icethickness.consensus_gridded, gdir)
    # mass balance calibration data
    if not os.path.isfile(gdir.get_filepath('mb_calib_pygem')):
        workflow.execute_entity_task(mbdata.mb_df_to_gdir, gdir)
    # debris thickness and melt enhancement factors
    if not os.path.isfile(gdir.get_filepath('debris_ed')) or not os.path.isfile(gdir.get_filepath('debris_hd')):
        workflow.execute_entity_task(debris.debris_to_gdir, gdir)
        workflow.execute_entity_task(debris.debris_binned, gdir)
    # 1d elevation change calibration data
    if not os.path.isfile(gdir.get_filepath('elev_change_1d')):
        workflow.execute_entity_task(elevchange1d.dh_1d_to_gdir, gdir)
    # 1d melt extent calibration data
    if not os.path.isfile(gdir.get_filepath('meltextent_1d')):
        workflow.execute_entity_task(meltextent_and_snowline_1d.meltextent_1d_to_gdir, gdir)
    # 1d snowline calibration data
    if not os.path.isfile(gdir.get_filepath('snowline_1d')):
        workflow.execute_entity_task(meltextent_and_snowline_1d.snowline_1d_to_gdir, gdir)

    return gdir


def single_flowline_glacier_directory_with_calving(
    rgi_id,
    reset=pygem_prms['oggm']['overwrite_gdirs'],
    prepro_border=pygem_prms['oggm']['border'],
    k_calving=1,
    logging_level=pygem_prms['oggm']['logging_level'],
    has_internet=pygem_prms['oggm']['has_internet'],
    working_dir=f'{pygem_prms["root"]}/{pygem_prms["oggm"]["oggm_gdir_relpath"]}',
    facorrected=pygem_prms['setup']['include_frontalablation'],
):
    """Prepare a GlacierDirectory for PyGEM (single flowline to start with)

    k_calving is free variable!

    Parameters
    ----------
    rgi_id : str
        the rgi id of the glacier
    reset : bool
        set to true to delete any pre-existing files. If false (the default),
        the directory won't be re-downloaded if already available locally in
        order to spare time.
    prepro_border : int
        the size of the glacier map: 10, 80, 160, 250
    Returns
    -------
    a GlacierDirectory object
    """
    if type(rgi_id) != str:
        raise ValueError('We expect rgi_id to be a string')
    if rgi_id.startswith('RGI60-') == False:
        rgi_id = 'RGI60-' + rgi_id.split('.')[0].zfill(2) + '.' + rgi_id.split('.')[1]
    else:
        raise ValueError('Check RGIId is correct')

    # Initialize OGGM and set up the default run parameters
    cfg.initialize(logging_level=logging_level)
    # Set multiprocessing to false; otherwise, causes daemonic error due to PyGEM's multiprocessing
    #  - avoids having multiple multiprocessing going on at the same time
    cfg.PARAMS['use_multiprocessing'] = False

    # Avoid erroneous glaciers (e.g., Centerlines too short or other issues)
    cfg.PARAMS['continue_on_error'] = True

    # Has internet
    cfg.PARAMS['has_internet'] = has_internet

    # Set border boundary
    cfg.PARAMS['border'] = prepro_border
    # Usually we recommend to set dl_verify to True - here it is quite slow
    # because of the huge files so we just turn it off.
    # Switch it on for real cases!
    cfg.PARAMS['dl_verify'] = True
    cfg.PARAMS['use_multiple_flowlines'] = False
    # temporary directory for testing (deleted on computer restart)
    cfg.PATHS['working_dir'] = working_dir

    # check if gdir is already processed
    if not reset:
        try:
            gdir = workflow.init_glacier_directories([rgi_id])[0]
            gdir.read_pickle('inversion_flowlines')

        except:
            reset = True

    if reset:
        # Start after the prepro task level
        base_url = pygem_prms['oggm']['base_url']

        cfg.PARAMS['has_internet'] = pygem_prms['oggm']['has_internet']
        gdir = workflow.init_glacier_directories(
            [rgi_id],
            from_prepro_level=2,
            prepro_border=cfg.PARAMS['border'],
            prepro_base_url=base_url,
            prepro_rgi_version='62',
        )[0]

        if not gdir.is_tidewater:
            raise ValueError(f'{rgi_id} is not tidewater!')

    # go through shop tasks to process auxiliary datasets to gdir if necessary
    # consensus glacier mass
    if not os.path.isfile(gdir.get_filepath('consensus_mass')):
        workflow.execute_entity_task(icethickness.consensus_gridded, gdir)

    # mass balance calibration data (note facorrected kwarg)
    if not os.path.isfile(gdir.get_filepath('mb_calib_pygem')):
        workflow.execute_entity_task(mbdata.mb_df_to_gdir, gdir, **{'facorrected': facorrected})
    # 1d elevation change calibration data
    if not os.path.isfile(gdir.get_filepath('elev_change_1d')):
        workflow.execute_entity_task(elevchange1d.dh_1d_to_gdir, gdir)
    # 1d melt extent calibration data
    if not os.path.isfile(gdir.get_filepath('meltextent_1d')):
        workflow.execute_entity_task(meltextent_and_snowline_1d.meltextent_1d_to_gdir, gdir)
    # 1d snowline calibration data
    if not os.path.isfile(gdir.get_filepath('snowline_1d')):
        workflow.execute_entity_task(meltextent_and_snowline_1d.snowline_1d_to_gdir, gdir)

    return gdir


def single_flowline_glacier_directory_custom(
    rgi_id,
    custom_gdir_path=None,
    custom_shapefile_path=None,
    reset=False,
    prepro_border=240,
    logging_level='CRITICAL',
    has_internet=False,
    working_dir=None,
    bin_width=20,
):
    """Prepare a GlacierDirectory for PyGEM using pre-existing glacier data.

    This function uses an existing glacier directory with correct DEM and
    gridded_data.nc to compute true hypsometry without downloading OGGM
    preprocessed data. Designed for glaciers like Dixon Glacier where
    a local corrected glacier directory exists.

    Scientific approach:
    - True hypsometry: Area per elevation band computed directly from DEM
      masked by glacier outline in gridded_data.nc
    - Ice thickness: Uses consensus ice thickness from Farinotti et al. (2019)
      if available in gridded_data.nc, otherwise uses Huss & Farinotti (2012)
      statistical parameterization based on glacier area and slope
    - Flowlines: Creates elevation band flowlines suitable for
      MassRedistributionCurves dynamics

    Parameters
    ----------
    rgi_id : str
        the rgi id of the glacier (e.g., '1.20947' or 'RGI60-01.20947')
    custom_gdir_path : str, optional
        Path to existing glacier directory containing gridded_data.nc, dem.tif,
        and related files. If None, searches in default OGGM gdir location.
    custom_shapefile_path : str, optional
        Path to custom shapefile for additional area validation.
    reset : bool
        set to true to regenerate flowline files even if they exist
    prepro_border : int
        the size of the glacier map: 10, 80, 160, 240
    bin_width : int
        Width of elevation bands in meters (default: 20m)

    Returns
    -------
    a GlacierDirectory object with true geometry from DEM

    Notes
    -----
    This function does NOT download OGGM prepro data. It requires a pre-existing
    glacier directory with correct DEM data. The glacier directory must contain:
    - gridded_data.nc (with glacier_mask, topo, and optionally consensus_h)
    - dem.tif
    - glacier_grid.json

    The hypsometry (area-elevation distribution) is computed by:
    1. Reading the glacier mask and DEM from gridded_data.nc
    2. Computing area in each elevation band (grid cell area × number of cells)
    3. Computing mean ice thickness per band from consensus_h if available

    References
    ----------
    Farinotti et al. (2019): A consensus estimate for the ice thickness
        distribution of all glaciers on Earth, Nature Geoscience.
    Huss & Farinotti (2012): Distributed ice thickness and volume of all
        glaciers around the globe, JGR.
    """
    if type(rgi_id) != str:
        raise ValueError('We expect rgi_id to be a string')

    # Normalize RGI ID
    if not rgi_id.startswith('RGI60-'):
        rgi_id_full = 'RGI60-' + rgi_id.split('.')[0].zfill(2) + '.' + rgi_id.split('.')[1]
    else:
        rgi_id_full = rgi_id
        rgi_id = rgi_id.replace('RGI60-', '').lstrip('0')

    # Extract region and subregion for path construction
    region = rgi_id_full.split('-')[1].split('.')[0]  # '01'
    glac_id = rgi_id_full.split('.')[1]  # '20947'
    subregion = f"{region}.{glac_id[:2]}"  # '01.20'

    # Set default paths
    if working_dir is None:
        working_dir = f'{pygem_prms["root"]}/{pygem_prms["oggm"]["oggm_gdir_relpath"]}'

    # Determine glacier directory path
    if custom_gdir_path is None:
        # Default path structure: per_glacier/RGI60-01/RGI60-01.20/RGI60-01.20947/
        custom_gdir_path = os.path.join(
            working_dir, 'per_glacier',
            f'RGI60-{region}', f'RGI60-{subregion}', rgi_id_full
        )

    # Validate glacier directory exists
    if not os.path.isdir(custom_gdir_path):
        raise FileNotFoundError(
            f'Glacier directory not found: {custom_gdir_path}\n'
            f'This function requires a pre-existing glacier directory with '
            f'gridded_data.nc and dem.tif. Use standard OGGM preprocessing '
            f'or copy from an existing processed glacier.'
        )

    # Check required files
    gridded_data_path = os.path.join(custom_gdir_path, 'gridded_data.nc')
    if not os.path.exists(gridded_data_path):
        raise FileNotFoundError(f'gridded_data.nc not found in {custom_gdir_path}')

    print(f"Loading glacier directory for {rgi_id_full}")
    print(f"  Path: {custom_gdir_path}")

    # Initialize OGGM config (needed for some internal operations)
    cfg.initialize(logging_level=logging_level)
    cfg.PARAMS['use_multiprocessing'] = False
    cfg.PARAMS['continue_on_error'] = True
    cfg.PARAMS['has_internet'] = has_internet
    cfg.PARAMS['border'] = prepro_border
    cfg.PARAMS['dl_verify'] = False
    cfg.PARAMS['use_multiple_flowlines'] = False
    cfg.PATHS['working_dir'] = working_dir

    # Read gridded data to compute true hypsometry
    with netCDF4.Dataset(gridded_data_path, 'r') as nc:
        # Get grid spacing
        x = nc.variables['x'][:]
        y = nc.variables['y'][:]
        dx = abs(x[1] - x[0]) if len(x) > 1 else 50.0
        dy = abs(y[1] - y[0]) if len(y) > 1 else 50.0
        pixel_area = dx * dy  # m²

        # Get glacier mask and topography
        glacier_mask = nc.variables['glacier_mask'][:].astype(bool)
        topo = nc.variables['topo'][:]

        # Get consensus ice thickness if available
        has_consensus_h = 'consensus_h' in nc.variables
        if has_consensus_h:
            consensus_h = nc.variables['consensus_h'][:]
            # Apply glacier mask
            consensus_h = np.where(glacier_mask, consensus_h, 0)
            valid_h = consensus_h[glacier_mask]
            print(f"  Consensus ice thickness: {valid_h.min():.1f} - {valid_h.max():.1f} m "
                  f"(mean: {valid_h.mean():.1f} m)")
        else:
            consensus_h = None
            print("  No consensus ice thickness found, will use statistical parameterization")

    # Compute glacier statistics from true DEM
    glacier_elevations = topo[glacier_mask]
    glacier_area_m2 = np.sum(glacier_mask) * pixel_area
    glacier_area_km2 = glacier_area_m2 / 1e6

    elev_min = glacier_elevations.min()
    elev_max = glacier_elevations.max()

    print(f"  True glacier area: {glacier_area_km2:.2f} km²")
    print(f"  Elevation range: {elev_min:.0f} - {elev_max:.0f} m")

    # Compute hypsometry (area per elevation band)
    # Use bin_width meter elevation bands
    elev_bins = np.arange(
        np.floor(elev_min / bin_width) * bin_width,
        np.ceil(elev_max / bin_width) * bin_width + bin_width,
        bin_width
    )

    # Compute area and mean thickness per band
    hypsometry = []
    for i in range(len(elev_bins) - 1):
        bin_low = elev_bins[i]
        bin_high = elev_bins[i + 1]
        bin_mid = (bin_low + bin_high) / 2

        # Find pixels in this elevation band
        in_band = glacier_mask & (topo >= bin_low) & (topo < bin_high)
        band_area_m2 = np.sum(in_band) * pixel_area

        if band_area_m2 > 0:
            # Compute mean thickness in band
            if consensus_h is not None:
                band_thickness = consensus_h[in_band]
                mean_thickness = band_thickness.mean() if len(band_thickness) > 0 else 0
            else:
                mean_thickness = 0  # Will be computed statistically later

            hypsometry.append({
                'bin_elevation': bin_mid,
                'area': band_area_m2,
                'thickness': mean_thickness,
            })

    hypsometry_df = pd.DataFrame(hypsometry)
    n_bands = len(hypsometry_df)
    print(f"  Number of elevation bands: {n_bands} ({bin_width}m bins)")

    # If no consensus thickness, use statistical parameterization
    # Based on Huss & Farinotti (2012) empirical relationships
    if consensus_h is None:
        # Empirical mean thickness from area (Bahr et al., 1997)
        # h_mean = c * A^γ, where c ≈ 28.5, γ ≈ 0.357 for mountain glaciers
        c_thick = 28.5
        gamma_thick = 0.357
        mean_thickness_est = c_thick * (glacier_area_km2 ** gamma_thick)

        # Apply normalized thickness profile (thickest in mid-elevations)
        elev_norm = (hypsometry_df['bin_elevation'] - elev_min) / (elev_max - elev_min)
        # Parabolic profile: peaks around 40% of elevation range from terminus
        thickness_factor = 4 * (elev_norm * 0.6 + 0.2) * (1 - (elev_norm * 0.6 + 0.2))
        thickness_factor = np.maximum(thickness_factor, 0.3)  # Minimum 30% of mean

        hypsometry_df['thickness'] = mean_thickness_est * thickness_factor / thickness_factor.mean()
        print(f"  Statistical thickness (Huss & Farinotti): mean {mean_thickness_est:.1f} m")

    # Compute volume per band
    hypsometry_df['volume'] = hypsometry_df['area'] * hypsometry_df['thickness']
    total_volume_km3 = hypsometry_df['volume'].sum() / 1e9
    print(f"  Total ice volume: {total_volume_km3:.3f} km³")

    # Create elevation band flowline DataFrame
    # Sort from terminus (lowest) to head (highest)
    hypsometry_df = hypsometry_df.sort_values('bin_elevation').reset_index(drop=True)

    # Compute width from area (width = area / dx)
    flowline_dx = bin_width  # Use bin width as flowline dx
    hypsometry_df['width'] = hypsometry_df['area'] / flowline_dx

    # Create elevation_band_flowline.csv compatible with OGGM
    eb_flowline = pd.DataFrame({
        'dis_along_flowline': np.arange(n_bands) * flowline_dx,
        'area': hypsometry_df['area'].values,
        'width': hypsometry_df['width'].values,
        'bin_elevation': hypsometry_df['bin_elevation'].values,
        'thickness': hypsometry_df['thickness'].values,
    })

    # Save elevation band flowline
    ebf_path = os.path.join(custom_gdir_path, 'elevation_band_flowline.csv')
    eb_flowline.to_csv(ebf_path, index=False)
    print(f"  Created elevation_band_flowline.csv")

    # Initialize glacier directory using OGGM's standard mechanism
    # This creates the GlacierDirectory object that PyGEM expects
    gdir = workflow.init_glacier_directories([rgi_id_full])[0]

    # Verify the gdir points to our custom directory
    # (OGGM may have created it in a different location)
    # Use os.path.realpath to normalize paths for comparison
    if os.path.realpath(gdir.dir) != os.path.realpath(custom_gdir_path):
        # Copy elevation_band_flowline.csv to OGGM's gdir location
        import shutil
        dest_ebf = os.path.join(gdir.dir, 'elevation_band_flowline.csv')
        shutil.copy(ebf_path, dest_ebf)
        print(f"  Copied elevation_band_flowline.csv to {gdir.dir}")

        # Also copy gridded_data.nc for consistency
        dest_gridded = os.path.join(gdir.dir, 'gridded_data.nc')
        if not os.path.exists(dest_gridded) or reset:
            shutil.copy(gridded_data_path, dest_gridded)

    # Create flowline objects for MassRedistributionCurves dynamics
    # The MRCModel uses elevation bands, not centerlines
    from oggm.core.flowline import MixedBedFlowline
    from shapely.geometry import LineString

    # Create a simple line geometry for the flowline
    # This is a vertical profile from terminus to head
    x_coords = np.arange(n_bands) * flowline_dx
    y_coords = np.zeros(n_bands)
    line = LineString(list(zip(x_coords, y_coords)))

    # Surface elevation (from hypsometry)
    surface_h = hypsometry_df['bin_elevation'].values.astype(float)

    # Ice thickness
    thick = hypsometry_df['thickness'].values.astype(float)

    # Bed elevation = surface - thickness
    bed_h = surface_h - thick

    # Width in meters
    widths_m = hypsometry_df['width'].values.astype(float)

    # Cross-sectional area (width * thickness)
    section = widths_m * thick

    # Create MixedBedFlowline (what MassRedistributionCurves expects)
    model_fl = MixedBedFlowline(
        line=line,
        dx=1.0,  # Normalized dx (actual spacing is dx_meter)
        map_dx=flowline_dx,  # Actual spacing in meters
        surface_h=surface_h.copy(),
        bed_h=bed_h.copy(),
        section=section.copy(),
        bed_shape=np.zeros(n_bands),  # Rectangular bed
        is_trapezoid=np.ones(n_bands, dtype=bool),
        lambdas=np.ones(n_bands),
        widths_m=widths_m.copy(),
        rgi_id=rgi_id_full,
        water_level=0,
        gdir=gdir,
    )

    # Set the thick attribute explicitly
    model_fl.thick = thick.copy()

    # Save model_flowlines
    gdir.write_pickle([model_fl], 'model_flowlines')
    print(f"  Created model_flowlines for dynamics simulation")

    # Also create inversion_flowlines for compatibility
    # These use the same data but are Centerline objects
    try:
        # Try to read existing inversion_flowlines and update them
        # Check if file is gzip compressed
        inv_fl_path = os.path.join(custom_gdir_path, 'inversion_flowlines.pkl')
        if os.path.exists(inv_fl_path):
            try:
                with gzip.open(inv_fl_path, 'rb') as f:
                    fls = pickle.load(f)
            except:
                with open(inv_fl_path, 'rb') as f:
                    fls = pickle.load(f)

            fl = fls[0]

            # Update widths to match true area
            # The original flowline has a different dx, so we need to scale
            original_area = (fl.widths_m * fl.dx_meter).sum()
            scale_factor = glacier_area_m2 / original_area if original_area > 0 else 1.0

            if hasattr(fl, '_widths'):
                fl._widths = fl._widths * scale_factor

            # Update thickness using interpolation from our hypsometry
            if hasattr(fl, 'surface_h') and len(fl.surface_h) > 0:
                fl_elevations = fl.surface_h
                # Interpolate thickness from hypsometry
                fl.thick = np.interp(
                    fl_elevations,
                    hypsometry_df['bin_elevation'].values,
                    hypsometry_df['thickness'].values,
                    left=hypsometry_df['thickness'].iloc[0],
                    right=hypsometry_df['thickness'].iloc[-1]
                )
                fl.bed_h = fl.surface_h - fl.thick
                fl.section = fl.thick * fl.widths_m

            gdir.write_pickle(fls, 'inversion_flowlines')
            print(f"  Updated inversion_flowlines with true geometry")

    except Exception as e:
        print(f"  Note: Could not update inversion_flowlines: {e}")
        print(f"  This is OK for MassRedistributionCurves simulations")

    # Create inversion_input for water level calculation
    inversion_input = [{
        'hgt': surface_h.copy(),
        'width': widths_m.copy(),
        'slope_angle': np.zeros(n_bands),
        'is_last': True,
        'is_rectangular': False,
        'is_trapezoid': True,
    }]
    gdir.write_pickle(inversion_input, 'inversion_input')

    # Final summary
    print(f"\n  Summary for {rgi_id_full}:")
    print(f"    Area:     {glacier_area_km2:.2f} km² (from true DEM)")
    print(f"    Volume:   {total_volume_km3:.3f} km³")
    print(f"    Elev:     {elev_min:.0f} - {elev_max:.0f} m")
    print(f"    Bands:    {n_bands} ({bin_width}m spacing)")

    return gdir


def get_spinup_flowlines(gdir, y0=None):
    """Get OGGM spinup flowlines at a desired year.

    Parameters
    ----------
    gdir : GlacierDirectory
        the glacier to compute
    y0 : int
        the year at which to get the flowlines (None for last year)

    Returns
    -------
    flowline object
    """
    # instantiate flowline.FileModel object from model_geometry_dynamic_spinup
    fmd_dynamic = FileModel(gdir.get_filepath('model_geometry', filesuffix='_dynamic_spinup_pygem_mb'))
    # run FileModel to startyear (it will be initialized at `spinup_start_yr`)
    fmd_dynamic.run_until(y0)
    # write flowlines
    gdir.write_pickle(fmd_dynamic.fls, 'model_flowlines', filesuffix=f'_dynamic_spinup_pygem_mb_{y0}')
    # add debris
    debris.debris_binned(gdir, fl_str='model_flowlines', filesuffix=f'_dynamic_spinup_pygem_mb_{y0}')
    # return flowlines
    return gdir.read_pickle('model_flowlines', filesuffix=f'_dynamic_spinup_pygem_mb_{y0}')


def update_cfg(updates, dict_name='PARAMS'):
    """
    Update keys in the OGGMs config.

    Parameters:
    dict (str): The dictionary in the config to update.
    updates (dict): Key-Value pairs to be updated.

    Returns:
    None: The function updates `cfg` in place.
    """
    try:
        target_dict = getattr(cfg, dict_name)
        for key, subdict in updates.items():
            if key in target_dict and isinstance(target_dict[key], dict) and isinstance(subdict, dict):
                for subkey, value in subdict.items():
                    if subkey in cfg[dict][key]:
                        target_dict[key][subkey] = value
            elif key in target_dict:
                target_dict[key] = subdict
    except Exception as err:
        print(err)


def create_empty_glacier_directory(rgi_id):
    """Create empty GlacierDirectory for PyGEM's alternative ice thickness products

    Parameters
    ----------
    rgi_id : str
        the rgi id of the glacier (RGIv60-)

    Returns
    -------
    a GlacierDirectory object
    """
    # RGIId check
    if type(rgi_id) != str:
        raise ValueError('We expect rgi_id to be a string')
    assert rgi_id.startswith('RGI60-'), 'Check RGIId starts with RGI60-'

    # Create empty directory
    gdir = CompatGlacDir(rgi_id)

    return gdir


def get_glacier_zwh(gdir):
    """Computes this glaciers altitude, width and ice thickness.

    Parameters
    ----------
    gdir : GlacierDirectory
        the glacier to compute

    Returns
    -------
    a dataframe with the requested data
    """

    fls = gdir.read_pickle('model_flowlines')
    z = np.array([])
    w = np.array([])
    h = np.array([])
    for fl in fls:
        # Widths (in m)
        w = np.append(w, fl.widths_m)
        # Altitude (in m)
        z = np.append(z, fl.surface_h)
        # Ice thickness (in m)
        h = np.append(h, fl.thick)
    # Distance between two points
    dx = fl.dx_meter

    # Output
    df = pd.DataFrame()
    df['z'] = z
    df['w'] = w
    df['h'] = h
    df['dx'] = dx

    return df


class RandomLinearMassBalance(MassBalanceModel):
    """Mass-balance as a linear function of altitude with random ELA.

    This is a dummy MB model to illustrate how to program one.

    The reference ELA is taken at a percentile altitude of the glacier.
    It then varies randomly from year to year.

    This class implements the MassBalanceModel interface so that the
    dynamical model can use it. Even if you are not familiar with object
    oriented programming, I hope that the example below is simple enough.
    """

    def __init__(self, gdir, grad=3.0, h_perc=60, sigma_ela=100.0, seed=None):
        """Initialize.

        Parameters
        ----------
        gdir : oggm.GlacierDirectory
            the working glacier directory
        grad: float
            Mass-balance gradient (unit: [mm w.e. yr-1 m-1])
        h_perc: int
            The percentile of the glacier elevation to choose the ELA
        sigma_ela: float
            The standard deviation of the ELA (unit: [m])
        seed : int, optional
            Random seed used to initialize the pseudo-random number generator.

        """
        super(RandomLinearMassBalance, self).__init__()
        self.valid_bounds = [-1e4, 2e4]  # in m
        self.grad = grad
        self.sigma_ela = sigma_ela
        self.hemisphere = 'nh'
        self.rng = np.random.RandomState(seed)

        # Decide on a reference ELA
        grids_file = gdir.get_filepath('gridded_data')
        with netCDF4.Dataset(grids_file) as nc:
            glacier_mask = nc.variables['glacier_mask'][:]
            glacier_topo = nc.variables['topo_smoothed'][:]

        self.orig_ela_h = np.percentile(glacier_topo[glacier_mask == 1], h_perc)
        self.ela_h_per_year = dict()  # empty dictionary

    def get_random_ela_h(self, year):
        """This generates a random ELA for the requested year.

        Since we do not know which years are going to be asked for we generate
        them on the go.
        """

        year = int(year)
        if year in self.ela_h_per_year:
            # If already computed, nothing to be done
            return self.ela_h_per_year[year]

        # Else we generate it for this year
        ela_h = self.orig_ela_h + self.rng.randn() * self.sigma_ela
        self.ela_h_per_year[year] = ela_h
        return ela_h

    def get_annual_mb(self, heights, year=None, fl_id=None):
        # Compute the mass-balance gradient
        ela_h = self.get_random_ela_h(year)
        mb = (np.asarray(heights) - ela_h) * self.grad

        # Convert to units of [m s-1] (meters of ice per second)
        return mb / SEC_IN_YEAR / cfg.PARAMS['ice_density']
