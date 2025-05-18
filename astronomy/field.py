from datetime import datetime
from pytz import timezone
from starplot import OpticPlot, DSO, _
from starplot.styles import PlotStyle, extensions, LabelStyle, ZOrderEnum, ObjectStyle, MarkerStyle, FillStyleEnum, FontWeightEnum, MarkerSymbolEnum
from starplot.optics import Scope, Reflector
from astropy.coordinates import SkyCoord
from skyfield.api import load, wgs84
from skyfield.units import Angle
import matplotlib.pyplot as plt

from astronomy.Telescope import Telescope

common_font = {
    "font_size": 80,
    "font_color": "#ffffff",
    "font_weight": "normal"
}

big_font = {
    "font_size": 108,
    "font_color": "#ffffff",
    "font_weight": "bold"
}

style_overrides = {
    # global
    "text_border_width": 0,
    "text_border_color": "#ffffff",

    # Title and info text
    "title": common_font.copy(),
    "info_text": common_font.copy(),

    # Nearby
    "planets": {"label": big_font.copy(), "marker": {"color": "#ff0000", "size": 80}},
    "moon": {"label": common_font.copy()},
    "sun": {"label": common_font.copy()},

    # DSOs
    "dso_galaxy": {
        "label": common_font.copy(),
        "marker": {"size": 80, "color": "#004800", "alpha": 0.5}
    },
    "dso_nebula": {
        "label": common_font.copy(),
        "marker": {"size": 70, "color": "#9900FF", "alpha": 0.5}
    },
    "dso_open_cluster": {
        "label": common_font.copy(),
        "marker": {"size": 60, "color": "#93A600", "alpha": 0.7}
    },
    "dso_globular_cluster": {
        "label": common_font.copy(),
        "marker": {"size": 65, "color": "#EEFF00", "alpha": 0.7}
    },
    "dso_planetary_nebula": {
        "label": common_font.copy(),
        "marker": {"size": 55, "color": "#FF00D9", "alpha": 0.7}
    },
    "dso_double_star": {
        "label": common_font.copy(),
        "marker": {"size": 50, "color": "#FFBF00"}
    },

    # Feature labels
    "constellation_labels": common_font.copy(),
    "gridlines": {"label": common_font.copy()},
    "ecliptic": {"label": common_font.copy()},
    "celestial_equator": {"label": common_font.copy()},
    "horizon": {"label": common_font.copy()},

}

class FieldGenerator:
    pass

def create_telescope_field(telescope: Telescope, t=None, resolution=240):
    ts = load.timescale()
    if t is None:
        t = ts.now()

    style = PlotStyle(background_color="#200000",
                      figure_background_color="#000",
                      border_bg_color="#000",

                      star=ObjectStyle(
                          marker=MarkerStyle(
                              fill=FillStyleEnum.FULL,
                              zorder=ZOrderEnum.LAYER_3,
                              size=40,
                              edge_color=None,
                              color="#fff"
                          ),
                          label=LabelStyle(
                              font_size=160,
                              font_family="monospace",
                              zorder=ZOrderEnum.LAYER_3,
                              offset_x="auto",
                              offset_y="auto",
                              font_color="#fff"
                          ),
                      )).extend(style_overrides)

    optic = Reflector(
        telescope.focal_length,
        telescope.eyepiece,
        telescope.eyepiece_fov,
    )

    plot = OpticPlot(
        ra=telescope.position[0],
        dec=telescope.position[1],
        lat=telescope.location.lat.degree,
        lon=telescope.location.lon.degree,
        dt=t.utc_datetime(),
        style=style,
        resolution=resolution,
        autoscale=True,
        optic=optic
    )

    magnification = telescope.focal_length / telescope.eyepiece
    print(f"Magnification: {magnification:.1f}x")
    aperture_inches = telescope.focal_length / (7 * 25.4)
    limiting_magnitude = 7.5 + 5 * (aperture_inches / 4) ** 0.5
    print(f"Limiting magnitude: {limiting_magnitude:.2f}")

    plot.stars(
        size_fn=lambda star: 1000 * (limiting_magnitude - star.magnitude),
        alpha_fn=lambda star: 1 - (star.magnitude/limiting_magnitude),
        catalog='big-sky')

    # Add any DSOs in the field
    plot.dsos()
    plot.moon()

    #if override_local_target is None:
    #    plot.planets()
    #else:
    #    plot.marker(
    #        ra=ra,
    #        dec=dec,
    #        style={
    #            "marker": {
    #                "size": 100,
    #                "symbol": "circle",
    #                "fill": "full",
    #                "color": "#05ffff",
    #                "edge_color": "#e0c1e0",
    #                "alpha": 0.4,
    #            },
    #            "label": {
    #                "font_size": 120,
    #                "font_weight": "bold",
    #                "font_color": "#ffffff",
    #                "font_alpha": 1,
    #                "font_family": "monospace",
    #                "zorder": ZOrderEnum.LAYER_3,
    #                "offset_x": "auto",
    #                "offset_y": "auto",
    #            },
    #        },
    #        label=override_local_target,
    #    )

    true_fov = telescope.eyepiece_fov / magnification
    info_text = f"{telescope.focal_length}mm {telescope.eyepiece}mm ({telescope.eyepiece_fov}° AFOV)\n" \
        f"{magnification:.1f}x, True FOV: {true_fov:.2f}°"

    # plot.title(info_text)

    return plot


# planets = load("de440s.bsp")
#saturn = planets['SATURN BARYCENTER']
#earth = planets['EARTH']
#rochester = wgs84.latlon(rochesterLat, rochesterLong, rochesterElevation)
#topocentric = earth + rochester
#geocentric = topocentric.at(t).observe(saturn).apparent()

#ra, dec, dist = geocentric.radec(epoch=t)
