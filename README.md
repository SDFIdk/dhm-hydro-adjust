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

A Python 3 environment with GDAL, NumPy and SciPy is required.

## Usage

The DEM raster is assumed to be divided into tiles, and since adjustment
objects may straddle tile boundaries, it is generally necessary to sample the
DEM in an area larger than the tile to burn into. In order to most
conveniently handle this, the recommended workflow is a two-step process:

1. Sample a DEM VRT for the provided (2D) adjustment objects, creating
intermediate "ready-to-burn" vector objects with appropriate elevation data
2. For each tile, create a copy with those "ready-to-burn" objects burned in
