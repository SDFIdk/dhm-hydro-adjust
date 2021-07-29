from hydroadjust.sampling import BoundingBox, get_raster_window, get_raster_interpolator

from osgeo import gdal, osr
import numpy as np

def test_raster_window():
    # Tests that the window-extraction function grabs a window that is
    # correctly sized, aligned and georeferenced.
    # Also checks that NODATA areas and areas outside of the source raster
    # correctly show NODATA.

    # Prepare raster input
    input_nodata_value = -1337
    input_grid = np.arange(30.0).reshape(6, 5)
    input_grid[3, 2] = input_nodata_value # NODATA in source raster
    input_num_rows, input_num_cols = input_grid.shape
    input_geotransform = [600000.0, 0.1, 0.0, 6200000.0, 0.0, -0.1]
    input_projection = "EPSG:25832"
    
    # Target minimum coverage extent. Note how this is non-pixel-aligned and
    # exceeds source raster extent on the eastern side.
    bbox = BoundingBox(
        x_min=600000.21,
        x_max=600000.42,
        y_min=6199999.61,
        y_max=6199999.79,
    )
    
    # Expected output to verify against
    expected_grid = np.array([
        [6., 7., 8., 9., input_nodata_value,],
        [11., 12., 13., 14., input_nodata_value],
        [16., input_nodata_value, 18., 19., input_nodata_value],
        [21., 22., 23., 24., input_nodata_value],
    ])
    expected_geotransform = [600000.1, 0.1, 0.0, 6199999.9, 0.0, -0.1]
    
    # Create input raster dataset
    input_driver = gdal.GetDriverByName("MEM")
    input_dataset = input_driver.Create(
        "temp_input",
        input_num_cols,
        input_num_rows,
        1,
        gdal.GDT_Float32,
    )
    input_dataset.SetProjection(input_projection)
    input_projection_sr = osr.SpatialReference(input_dataset.GetProjection()) # note: this is a SpatialReference object, to allow checking output with .IsSame()
    input_dataset.SetGeoTransform(input_geotransform)
    input_band = input_dataset.GetRasterBand(1)
    input_band.SetNoDataValue(input_nodata_value)
    input_band.WriteArray(input_grid)
    
    # Perform the window extraction
    output_dataset = get_raster_window(input_dataset, bbox)
    
    # Grab output values for assertions below
    output_projection_sr = osr.SpatialReference(output_dataset.GetProjection())
    output_geotransform = output_dataset.GetGeoTransform()
    output_band = output_dataset.GetRasterBand(1)
    output_nodata_value = output_band.GetNoDataValue()
    output_grid = output_band.ReadAsArray()
    
    # Check output
    np.testing.assert_allclose(output_grid, expected_grid)
    np.testing.assert_allclose(output_geotransform, expected_geotransform)
    assert output_projection_sr.IsSame(input_projection_sr)
    assert output_nodata_value == input_nodata_value


def test_raster_interpolator():
    # Tests that the RegularGridInterpolator is correctly aligned and returns
    # the expected data. This includes checking NODATA/NaN handling and
    # feeding it scalars, 1D and 2D arrays of X and Y input.
    
    input_grid = np.arange(12.0).reshape(3, 4)
    input_num_rows, input_num_cols = input_grid.shape
    input_projection = "EPSG:25832"
    # The X/Y grid below includes a column that sits exactly on the edge of
    # the defined area. Avoid rounding error issues here by taking a pixel
    # size (0.5) that can be exactly represented as a floating-point value.
    input_geotransform = [600000.0, 0.5, 0.0, 6200000.0, 0.0, -0.5]
    input_nodata_value = -9999 # should not appear in output
    
    # Scalar X and Y
    interp_point_x, interp_point_y = (600001.5, 6199999.5)
    expected_point_z = 4.5
    
    # 1D arrays of X and Y
    interp_list_x = np.array([600001.25, 600001.5, 600001.75, 600002.0, 600002.25])
    interp_list_y = np.array([6199999.75, 6199999.625, 6199999.5, 6199999.375, 6199999.25])
    expected_list_z = np.array([2.0, 3.5, 5.0, np.nan, np.nan])
    
    # 2D arrays of X and Y.
    # Allows checking that interpolation is bilinear in a square of
    # neighboring cell centers, and that the interpolator correctly fills in
    # NaN outside the defined area.
    interp_grid_x, interp_grid_y = np.meshgrid(
        600000.0 + np.array([1.25, 1.5, 1.75, 2.0, 2.25]),
        6200000.0 - np.array([0.25, 0.375, 0.5, 0.625, 0.75]),
    )
    expected_grid_z = np.array([
        [2.0, 2.5, 3.0, np.nan, np.nan],
        [3.0, 3.5, 4.0, np.nan, np.nan],
        [4.0, 4.5, 5.0, np.nan, np.nan],
        [5.0, 5.5, 6.0, np.nan, np.nan],
        [6.0, 6.5, 7.0, np.nan, np.nan],
    ]) 
    
    # Create input raster dataset
    input_driver = gdal.GetDriverByName("MEM")
    input_dataset = input_driver.Create(
        "temp_input",
        input_num_cols,
        input_num_rows,
        1,
        gdal.GDT_Float32,
    )
    input_dataset.SetProjection(input_projection)
    input_dataset.SetGeoTransform(input_geotransform)
    input_band = input_dataset.GetRasterBand(1)
    input_band.SetNoDataValue(input_nodata_value)
    input_band.WriteArray(input_grid)
    
    # Create the RegularGridInterpolator
    interpolator = get_raster_interpolator(input_dataset)
    
    # Get the results with X and Y being scalars, lists and grids, respectively
    interp_point_z = interpolator((interp_point_x, interp_point_y))
    interp_list_z = interpolator((interp_list_x, interp_list_y))
    interp_grid_z = interpolator((interp_grid_x, interp_grid_y))
    
    # Check results
    np.testing.assert_allclose(interp_point_z, expected_point_z)
    np.testing.assert_allclose(interp_list_z, expected_list_z)
    np.testing.assert_allclose(interp_grid_z, expected_grid_z)
