from hydroadjust.sampling import BoundingBox, get_raster_window, get_raster_interpolator
from hydroadjust.burning import burn_lines

from osgeo import gdal, ogr
import numpy as np
import argparse
import logging

gdal.UseExceptions()
ogr.UseExceptions()

ACCEPTABLE_GEOMETRY_TYPES = set([
    ogr.wkbLineString,
    ogr.wkbLineString25D,
    ogr.wkbLineStringM,
    ogr.wkbLineStringZM,
])

argument_parser = argparse.ArgumentParser()
argument_parser.add_argument('input_raster', type=str, help='input DEM raster dataset to sample')
argument_parser.add_argument('input_lines', type=str, help='input line-object vector data source')
argument_parser.add_argument('output_lines', type=str, help='output geometry file for lines with Z')

input_arguments = argument_parser.parse_args()

input_raster_path = input_arguments.input_raster
input_lines_path = input_arguments.input_lines
output_lines_path = input_arguments.output_lines

input_raster_dataset = gdal.Open(input_raster_path)

input_lines_datasrc = ogr.Open(input_lines_path)
input_lines_layer = input_lines_datasrc.GetLayer()

output_lines_driver = ogr.GetDriverByName("SQLite")
output_lines_datasrc = output_lines_driver.CreateDataSource(output_lines_path)
output_lines_datasrc.CreateLayer(
    "rendered_lines",
    srs=input_lines_layer.GetSpatialRef(),
    geom_type=ogr.wkbLineString25D,
)
output_lines_layer = output_lines_datasrc.GetLayer()

# Counters to track number of valid/invalid objects encountered
expected_pointcount_count = 0
unexpected_pointcount_count = 0
valid_sampling_count = 0
invalid_sampling_count = 0

for input_line_feature in input_lines_layer:
    input_line_geometry = input_line_feature.GetGeometryRef()
    
    # Rule out unexpected geometry types (apparently calling .GetGeomType() on
    # the layer yields weird results)
    if not (input_line_geometry.GetGeometryType() in ACCEPTABLE_GEOMETRY_TYPES):
        raise ValueError("encountered unexpected geometry type")
    
    if input_line_geometry.GetPointCount() == 2:
        # We want to consider only the X and Y of the geometry
        input_line_xy = np.array(input_line_geometry.GetPoints())[:,:2]
        
        input_line_bbox = BoundingBox(
            x_min=np.min(input_line_xy[:,0]),
            x_max=np.max(input_line_xy[:,0]),
            y_min=np.min(input_line_xy[:,1]),
            y_max=np.max(input_line_xy[:,1]),
        )
        
        # Get a raster window just covering this line object
        window_raster_dataset = get_raster_window(input_raster_dataset, input_line_bbox)
        
        window_raster_interpolator = get_raster_interpolator(window_raster_dataset)
        
        # Get raster Z for the respective endpoints
        input_line_z = window_raster_interpolator((input_line_xy[:,0], input_line_xy[:,1]))
        
        # Render only if no Z value is NaN
        if np.all(np.isfinite(input_line_z)):
            # Create output feature
            output_line_feature = ogr.Feature(output_lines_layer.GetLayerDefn())
            output_line_geometry = ogr.Geometry(ogr.wkbLineString25D)
            output_line_geometry.AddPoint(input_line_xy[0,0], input_line_xy[0,1], input_line_z[0])
            output_line_geometry.AddPoint(input_line_xy[1,0], input_line_xy[1,1], input_line_z[1])
            output_line_feature.SetGeometry(output_line_geometry)
            output_lines_layer.CreateFeature(output_line_feature)
            output_line_feature = None
            
            valid_sampling_count += 1
        else:
            invalid_sampling_count += 1
        
        expected_pointcount_count += 1
    else:
        # Point count not equal to 2, skip this geometry and warn.
        # (The input layer may be flawed, which we can tolerate here.)
        unexpected_pointcount_count += 1

logging.info(f"processed {expected_pointcount_count} line geometries")
if unexpected_pointcount_count != 0:
    logging.error(f"skipped {unexpected_pointcount_count} geometries with point count not equal to 2")

logging.info(f"rendered {valid_sampling_count} line objects with sampled Z")
if invalid_sampling_count != 0:
    logging.warning(f"skipped rendering of {invalid_sampling_count} line objects due to missing DEM data")