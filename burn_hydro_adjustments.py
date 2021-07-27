from osgeo import gdal, ogr
import argparse
import logging

def burn_lines(raster, lines):
    """
    Burn elevation of vector line segments into raster, modifying the raster
    dataset in-place.

    :param raster: DEM raster to burn lines into
    :type raster: GDAL Dataset object
    :param lines: line segments whose elevation should be burned in
    :type lines: OGR Layer object
    """

    # The "burn value" must be set to 0, resulting in 0 + the z value being
    # burned in. The default is 255 + z (yes, really).
    # See https://lists.osgeo.org/pipermail/gdal-dev/2015-August/042360.html
    gdal.RasterizeLayer(
        raster,
        [1], # band 1
        lines,
        burn_values=[0],
        options=[
            'BURN_VALUE_FROM=Z',
            'ALL_TOUCHED=TRUE', # ensure connectedness of resulting pixels
        ],
    )

argument_parser = argparse.ArgumentParser()
argument_parser.add_argument('input_raster', type=str, help='DEM input raster')
argument_parser.add_argument('output_raster', type=str, help='DEM output raster with objects burned in')
# argument_parser.add_argument('--lines', type=str, help='line objects with DEM-sampled Z') # TODO
argument_parser.add_argument('--horseshoe-lines', type=str, help='line-rendered horseshoe objects with DEM-sampled Z')

input_arguments = argument_parser.parse_args()

input_raster_path = input_arguments.input_raster
output_raster_path = input_arguments.output_raster
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

# lines_datasrc = ogr.Open(lines_path)
# lines_layer = lines_datasrc.GetLayer()

# burn_lines(output_raster_dataset, lines_layer)

output_raster_dataset = None
logging.info("output raster completed")
