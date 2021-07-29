# DHM Hydro Adjust

Tools to burn hydrological adjustment objects into a DEM raster.

## Background

These tools are intended to modify a DEM raster to ensure that it is
meaningful for hydrological uses. In particular, it is desired that water can
flow uninterrupted through culverts, under bridges etc.

The tools take as input a DEM raster (which should have appropriate elevation
in waterbody surfaces), as well as two kinds of vector "adjustment objects":

- **Line objects**, linestring objects consisting of exactly one line segment
each
- **Horseshoe objects**, linestring objects consisting of exactly three line
segments each

For line objects, the input raster is sampled in each endpoint, and the linear
interpolation between those is burned into the raster, creating a "canal" at
least one pixel wide along the line segment.

For horseshoe objects, two profiles (typically one on each side of a bridge)
are sampled from the raster, and the linear interpolation between those
profiles is burned into the raster. More precisely, a horseshoe object
consists of a linestring connecting points ABCD, with an "open" profile AD and
a "closed" profile BC. Each of those two profiles is sampled in the raster at
a user-configurable density, and the bilinear interpolation between them is
burned into the raster.

In order to work around the complexities of inverse bilinear interpolation,
the horseshoe objects are currently rendered by creating a grill-like pattern
of profile-to-profile line segments with endpoints of appropriate elevation.
Those line segments can then be burned into the raster in a manner similar to
the line objects.

## Installation

A Python 3 environment with GDAL, NumPy and SciPy is required. To run the
tests, pytest is also required.

## Usage

The DEM raster is assumed to be divided into tiles, and since adjustment
objects may straddle tile boundaries, it is generally necessary to sample the
DEM in an area larger than the tile to burn into. In order to most
conveniently handle this, the recommended workflow is conceptually a two-step
process:

1. Sample a DEM VRT for the provided (2D) adjustment objects, creating
intermediate "ready-to-burn" vector objects with appropriate elevation data
2. For each tile, create a copy with those "ready-to-burn" objects burned in

**Please note that the command-line interface for these tools is not
stabilized yet. Expect breaking changes.**

### Preparing line objects for burning

```
python -m hydroadjust.prepare_lines ORIGINAL_DTM.vrt LINE_OBJECTS.sqlite LINES_TO_BURN.sqlite
```

### Preparing horseshoe objects as lines for burning

```
python -m hydroadjust.prepare_horseshoe_lines ORIGINAL_DTM.vrt HORSESHOE_OBJECTS.sqlite HORSESHOE_LINES_TO_BURN.sqlite
```

The horseshoe profile sampling density can be controlled with the optional
`--max-sample-dist` argument; for example, using `--max-sample-dist 0.1` will
require the horseshoe profiles to be sampled at least every 0.1 meters. In
order to avoid gaps in the resulting raster, it is recommended that the value
is chosen to be smaller than the diagonal (georeferenced) pixel size of the
raster to burn into. The default value is half the diagonal pixel size of the
provided input raster.

### Burning the prepared vector objects into a raster tile

```
python -m hydroadjust.burn_adjustments ORIGINAL_DTM/1km_NNNN_EEE.tif ADJUSTED_DTM/1km_NNNN_EEE.tif --lines LINES_TO_BURN.sqlite --horseshoe-lines HORSESHOE_LINES_TO_BURN.sqlite
```

Both of the `--lines` and the `--horseshoe-lines` arguments are optional,
allowing either to be omitted if so desired.
