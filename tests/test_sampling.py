from hydroadjust.sampling import BoundingBox, get_raster_window

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
    
    # Target minimum coverage extent. Non-pixel-aligned and exceeds source
    # raster extent on the eastern side.
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
