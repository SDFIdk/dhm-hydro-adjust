from setuptools import setup

setup(
    name="dhm-hydro-adjust",
    description="Tools to make hydrological adjustments to DEM rasters",
    license="MIT",
    author="Danish Agency for Data Supply and Efficiency (SDFE)",
    author_email="sdfe@sdfe.dk",
    entry_points={
        "console_scripts": [
            "sample_line_z = hydroadjust.cli.sample_line_z:main",
            "sample_horseshoe_z_lines = hydroadjust.cli.sample_horseshoe_z_lines:main",
            "burn_line_z = hydroadjust.cli.burn_line_z:main",
        ],
    },
)
