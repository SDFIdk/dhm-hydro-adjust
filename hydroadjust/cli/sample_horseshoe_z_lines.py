from hydroadjust.sampling import BoundingBox, get_raster_window, get_raster_interpolator

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
argument_parser.add_argument('input_horseshoes', type=str, help='input horseshoe vector data source')
argument_parser.add_argument('output_lines', type=str, help='output linestring geometry file')
argument_parser.add_argument('--max-sample-dist', type=float, help='maximum allowed sampling distance on profiles')

input_arguments = argument_parser.parse_args()

input_raster_path = input_arguments.input_raster
input_horseshoes_path = input_arguments.input_horseshoes
output_lines_path = input_arguments.output_lines

input_raster_dataset = gdal.Open(input_raster_path)
input_raster_geotransform = input_raster_dataset.GetGeoTransform()

if input_arguments.max_sample_dist is None:
    # If not provided, set maximum sample distance to half the diagonal pixel
    # size of the input raster.
    max_profile_sample_dist = 0.5*np.hypot(
        input_raster_geotransform[1],
        input_raster_geotransform[5],
    )
else:
    max_profile_sample_dist = input_arguments.max_sample_dist

input_horseshoes_datasrc = ogr.Open(input_horseshoes_path)
input_horseshoes_layer = input_horseshoes_datasrc.GetLayer()

output_lines_driver = ogr.GetDriverByName("SQLite")
output_lines_datasrc = output_lines_driver.CreateDataSource(output_lines_path)
output_lines_datasrc.CreateLayer(
    "rendered_horseshoe_lines",
    srs=input_horseshoes_layer.GetSpatialRef(),
    geom_type=ogr.wkbLineString25D,
)
output_lines_layer = output_lines_datasrc.GetLayer()

# Counters to track number of valid/invalid objects encountered
expected_pointcount_count = 0
unexpected_pointcount_count = 0
valid_profile_count = 0
invalid_profile_count = 0

for horseshoe_feature in input_horseshoes_layer:
    horseshoe_geometry = horseshoe_feature.GetGeometryRef()
    
    # Rule out non-horseshoe geometries (apparently calling .GetGeomType() on
    # the layer yields weird results)
    if not (horseshoe_geometry.GetGeometryType() in ACCEPTABLE_GEOMETRY_TYPES):
        raise ValueError("encountered unexpected geometry type")
    
    if horseshoe_geometry.GetPointCount() == 4:
        # We want to consider only the X and Y of the geometry
        horseshoe_xy = np.array(horseshoe_geometry.GetPoints())[:,:2]
        
        horseshoe_bbox = BoundingBox(
            x_min=np.min(horseshoe_xy[:,0]),
            x_max=np.max(horseshoe_xy[:,0]),
            y_min=np.min(horseshoe_xy[:,1]),
            y_max=np.max(horseshoe_xy[:,1]),
        )
        
        # Get a raster window just covering this horseshoe
        window_raster_dataset = get_raster_window(input_raster_dataset, horseshoe_bbox)
        
        window_raster_interpolator = get_raster_interpolator(window_raster_dataset)
        
        # Length of (open) AD segment
        open_profile_length = np.hypot(
            horseshoe_xy[3, 0] - horseshoe_xy[0, 0],
            horseshoe_xy[3, 1] - horseshoe_xy[0, 1],
        )
        # Length of (closed) BC segment
        closed_profile_length = np.hypot(
            horseshoe_xy[2, 0] - horseshoe_xy[1, 0],
            horseshoe_xy[2, 1] - horseshoe_xy[1, 1],
        )
        
        # Determine number of samples to take along the profiles (at least 2)
        longest_profile_length = max(open_profile_length, closed_profile_length)
        num_profile_samples = max(2, int(np.ceil(longest_profile_length / max_profile_sample_dist)) + 1)
        
        # Along-profile coordinates
        profile_abscissa = np.linspace(
            0.0,
            1.0,
            num_profile_samples,
            endpoint=True,
        )
        
        # Interpolate (X, Y) along the two profiles
        open_profile_xy = horseshoe_xy[0,:] + profile_abscissa[:,np.newaxis]*(horseshoe_xy[3,:] - horseshoe_xy[0,:])
        closed_profile_xy = horseshoe_xy[1,:] + profile_abscissa[:,np.newaxis]*(horseshoe_xy[2,:] - horseshoe_xy[1,:])
        
        # Sample the raster Z in those interpolated (X, Y) locations
        open_profile_z = window_raster_interpolator((open_profile_xy[:,0], open_profile_xy[:,1]))
        closed_profile_z = window_raster_interpolator((closed_profile_xy[:,0], closed_profile_xy[:,1]))
        
        # Render only if there is no NaN in the profiles
        if np.all(np.isfinite(open_profile_z)) and np.all(np.isfinite(closed_profile_z)):
            # Create line features
            for i in range(num_profile_samples):
                line_feature = ogr.Feature(output_lines_layer.GetLayerDefn())
                line_geometry = ogr.Geometry(ogr.wkbLineString25D)
                line_geometry.AddPoint(open_profile_xy[i,0], open_profile_xy[i,1], open_profile_z[i])
                line_geometry.AddPoint(closed_profile_xy[i,0], closed_profile_xy[i,1], closed_profile_z[i])
                line_feature.SetGeometry(line_geometry)
                output_lines_layer.CreateFeature(line_feature)
                line_feature = None
            
            valid_profile_count += 1
        else:
            invalid_profile_count += 1
        
        expected_pointcount_count += 1
    else:
        # Point count not equal to 4, skip this geometry and warn.
        # (The horseshoe layer may be flawed, which we can tolerate here.)
        unexpected_pointcount_count += 1

logging.info(f"processed {expected_pointcount_count} horseshoe geometries")
if unexpected_pointcount_count != 0:
    logging.error(f"skipped {unexpected_pointcount_count} geometries with point count not equal to 4")

logging.info(f"rendered {valid_profile_count} horseshoe objects as lines")
if invalid_profile_count != 0:
    logging.warning(f"skipped rendering of {invalid_profile_count} horseshoe objects due to missing DEM data")
