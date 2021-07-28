from hydroadjust.burning import burn_lines

from osgeo import gdal, ogr, osr
import numpy as np


def test_burn_lines():
    # Test that line features are burned in correctly.
    # In particular, we want this test to fail if Z values are not getting
    # burned in (or have wrong values), or if the "ALL_TOUCHED" option is not
    # correctly enabled.
    
    # Prepare raster input
    raster_input_grid = np.arange(20.0).reshape(4, 5)
    raster_num_rows, raster_num_cols = raster_input_grid.shape
    raster_geotransform = [600000.0, 1.0, 0.0, 6200000.0, 0.0, -1.0]
    raster_projection = "EPSG:25832"
    
    # Prepare line object to burn in
    lines_srs = osr.SpatialReference()
    lines_srs.ImportFromEPSG(25832)
    line_geometry = ogr.Geometry(ogr.wkbLineString25D)
    line_geometry.AddPoint(600000.5, 6199996.5, 42.0)
    line_geometry.AddPoint(600003.5, 6199998.5, 42.0)
    
    # Expected output. Notice how the burned-in values follow the "all-touched"
    # pattern.
    raster_expected_grid = np.array([
        [ 0.,  1.,  2.,  3.,  4.],
        [ 5.,  6., 42., 42.,  9.],
        [10., 42., 42., 13., 14.],
        [42., 42., 17., 18., 19.],
    ])
    
    # Create raster dataset
    raster_driver = gdal.GetDriverByName("MEM")
    raster_dataset = raster_driver.Create(
        "temp_raster",
        raster_num_cols,
        raster_num_rows,
        1,
        gdal.GDT_Float32,
    )
    raster_dataset.SetProjection(raster_projection)
    raster_dataset.SetGeoTransform(raster_geotransform)
    raster_band = raster_dataset.GetRasterBand(1)
    raster_band.WriteArray(raster_input_grid)
    
    # Create vector datasource
    vector_driver = ogr.GetDriverByName("MEMORY")
    lines_datasrc = vector_driver.CreateDataSource("temp_vector")
    lines_datasrc.CreateLayer(
        "lines",
        srs=lines_srs,
        geom_type=ogr.wkbLineString25D,
    )
    lines_layer = lines_datasrc.GetLayer()
    line_feature = ogr.Feature(lines_layer.GetLayerDefn())
    line_feature.SetGeometry(line_geometry)
    lines_layer.CreateFeature(line_feature)
    line_feature = None
    
    # Burn line layer (duh)
    burn_lines(raster_dataset, lines_layer)
    
    # Check result
    raster_output_grid = raster_band.ReadAsArray()
    np.testing.assert_allclose(raster_output_grid, raster_expected_grid)
