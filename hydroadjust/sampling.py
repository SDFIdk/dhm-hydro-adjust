from osgeo import gdal, ogr
import numpy as np

from collections import namedtuple

# The ordering of window X and Y bounds is a mess in GDAL (compare e.g.
# gdal.Translate() and gdal.Warp()). Using this little structure and
# addressing the members by name should help limit confusion.
BoundingBox = namedtuple(
    'BoundingBox',
    ['x_min', 'x_max', 'y_min', 'y_max'],
)

def get_raster_window(dataset, bbox):
    """
    Return a window of the input raster dataset, containing at least the
    provided bounding box.
    
    :param dataset: Source raster dataset
    :type dataset: GDAL Dataset object
    :param bbox: Window bound coordinates
    :type bbox: hydroadjust.sampling.BoundingBox object
    :returns: GDAL Dataset object for the requested window
    """
    
    input_geotransform = dataset.GetGeoTransform()
    
    if input_geotransform[2] != 0.0 or input_geotransform[4] != 0.0:
        raise ValueError("geotransforms with rotation are unsupported")
    
    input_offset_x = input_geotransform[0]
    input_offset_y = input_geotransform[3]
    input_pixelsize_x = input_geotransform[1]
    input_pixelsize_y = input_geotransform[5]
    
    # We want to find window coordinates that:
    # a) are aligned to the source raster pixels
    # b) contain the requested bounding box plus at least one pixel of "padding" on each side, to allow for small floating-point rounding errors in X/Y coordinates
    # 
    # Recall that the pixel size in the geotransform is commonly negative, hence all the min/max calls.
    raw_x_min_col_float = (bbox.x_min - input_offset_x) / input_pixelsize_x
    raw_x_max_col_float = (bbox.x_max - input_offset_x) / input_pixelsize_x
    raw_y_min_row_float = (bbox.y_min - input_offset_y) / input_pixelsize_y
    raw_y_max_row_float = (bbox.y_max - input_offset_y) / input_pixelsize_y
    
    col_min = int(np.floor(min(raw_x_min_col_float, raw_x_max_col_float))) - 1
    col_max = int(np.ceil(max(raw_x_min_col_float, raw_x_max_col_float))) + 1
    row_min = int(np.floor(min(raw_y_min_row_float, raw_y_max_row_float))) - 1
    row_max = int(np.ceil(max(raw_y_min_row_float, raw_y_max_row_float))) + 1
    
    x_col_min = input_offset_x + input_pixelsize_x * col_min
    x_col_max = input_offset_x + input_pixelsize_x * col_max
    y_row_min = input_offset_y + input_pixelsize_y * row_min
    y_row_max = input_offset_y + input_pixelsize_y * row_max
    
    # Padded, georeferenced window coordinates. The target window to use with gdal.Translate().
    padded_bbox = BoundingBox(
        x_min=min(x_col_min, x_col_max),
        x_max=max(x_col_min, x_col_max),
        y_min=min(y_row_min, y_row_max),
        y_max=max(y_row_min, y_row_max),
    )
    
    # Size in pixels of destination raster
    dest_num_cols = col_max - col_min
    dest_num_rows = row_max - row_min
    
    translate_options = gdal.TranslateOptions(
        width=dest_num_cols,
        height=dest_num_rows,
        projWin=(padded_bbox.x_min, padded_bbox.y_max, padded_bbox.x_max, padded_bbox.y_min),
        resampleAlg=gdal.GRA_NearestNeighbour,
    )
    
    # gdal.Translate() needs a destination *name*, not just a Dataset to
    # write into. Create a temporary file in GDAL's virtual filesystem as a
    # stepping stone.
    window_dataset_name = "/vsimem/temp_window.tif"
    window_dataset = gdal.Translate(
        window_dataset_name,
        dataset,
        options=translate_options
    )
    
    return window_dataset
