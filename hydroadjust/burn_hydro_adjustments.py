from hydroadjust.burning import burn_lines

from osgeo import gdal, ogr
import argparse
import logging

argument_parser = argparse.ArgumentParser()
argument_parser.add_argument('input_raster', type=str, help='DEM input raster')
argument_parser.add_argument('output_raster', type=str, help='DEM output raster with objects burned in')
argument_parser.add_argument('--lines', type=str, help='line objects with DEM-sampled Z')
argument_parser.add_argument('--horseshoe-lines', type=str, help='line-rendered horseshoe objects with DEM-sampled Z')

input_arguments = argument_parser.parse_args()

input_raster_path = input_arguments.input_raster
output_raster_path = input_arguments.output_raster
lines_path = input_arguments.lines
horseshoe_lines_path = input_arguments.horseshoe_lines

input_raster_dataset = gdal.Open(input_raster_path)

output_driver = gdal.GetDriverByName("GTiff")
output_raster_dataset = output_driver.CreateCopy(
    output_raster_path,
    input_raster_dataset,
)

if horseshoe_lines_path is not None:
    horseshoe_lines_datasrc = ogr.Open(horseshoe_lines_path)
    horseshoe_lines_layer = horseshoe_lines_datasrc.GetLayer()

    burn_lines(output_raster_dataset, horseshoe_lines_layer)
    logging.info("burned horseshoe lines into output raster")
else:
    logging.info("no datasource provided for horseshoe lines")

if lines_path is not None:
    lines_datasrc = ogr.Open(lines_path)
    lines_layer = lines_datasrc.GetLayer()

    burn_lines(output_raster_dataset, lines_layer)
    logging.info("burned horseshoe lines into output raster")
else:
    logging.info("no datasource provided for line objects")

if lines_path is None and horseshoe_lines_path is None:
    logging.warning("no adjustment object datasets provided, nothing will get burned in")

output_raster_dataset = None
logging.info("output raster completed")
