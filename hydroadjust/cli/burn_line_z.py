from hydroadjust.burning import burn_lines

from osgeo import gdal, ogr
import argparse
import logging

argument_parser = argparse.ArgumentParser()
argument_parser.add_argument('lines', type=str, help='linestring features with DEM-sampled Z')
argument_parser.add_argument('input_raster', type=str, help='DEM input raster')
argument_parser.add_argument('output_raster', type=str, help='DEM output raster with objects burned in')

input_arguments = argument_parser.parse_args()

lines_path = input_arguments.lines
input_raster_path = input_arguments.input_raster
output_raster_path = input_arguments.output_raster

input_raster_dataset = gdal.Open(input_raster_path)

lines_datasrc = ogr.Open(lines_path)

output_driver = gdal.GetDriverByName("GTiff")
output_raster_dataset = output_driver.CreateCopy(
    output_raster_path,
    input_raster_dataset,
)

for layer in lines_datasrc:
    burn_lines(output_raster_dataset, layer)
    logging.info(f"burned layer {layer.GetName()} into raster")

output_raster_dataset = None
logging.info("output raster completed")
