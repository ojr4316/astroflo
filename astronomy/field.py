import math
from starplot import OpticPlot, _
from starplot.styles import PlotStyle, LabelStyle, ZOrderEnum, ObjectStyle, MarkerStyle, FillStyleEnum, MarkerSymbolEnum
from astropy.coordinates import SkyCoord
from skyfield.api import load
import numpy as np
from astronomy.Telescope import Telescope
import astropy.units as u

common_font = {
    "font_size": 6,
    "font_color": "#ffffff",
    "font_weight": "normal"
}

big_font = {
    "font_size": 8,
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
    "planets": {"label": big_font.copy(), "marker": {"color": "#ff0000", "size": 5}},
    "moon": {"label": common_font.copy()},
    "sun": {"label": common_font.copy()},

    # DSOs
    "dso_galaxy": {
        "label": common_font.copy(),
        "marker": {"size": 1, "color": "#004800", "alpha": 0.5}
    },
    "dso_nebula": {
        "label": common_font.copy(),
        "marker": {"size": 1, "color": "#9900FF", "alpha": 0.5}
    },
    "dso_open_cluster": {
        "label": common_font.copy(),
        "marker": {"size": 1, "color": "#93A600", "alpha": 0.7}
    },
    "dso_globular_cluster": {
        "label": common_font.copy(),
        "marker": {"size": 1, "color": "#EEFF00", "alpha": 0.7}
    },
    "dso_planetary_nebula": {
        "label": common_font.copy(),
        "marker": {"size": 1, "color": "#FF00D9", "alpha": 0.7}
    },
    "dso_double_star": {
        "label": common_font.copy(),
        "marker": {"size": 1, "color": "#FFBF00"}
    },

    # Feature labels
    "constellation_labels": common_font.copy(),
    "gridlines": {"label": common_font.copy()},
    "ecliptic": {"label": common_font.copy()},
    "celestial_equator": {"label": common_font.copy()},
    "horizon": {"label": common_font.copy()},

}

style = PlotStyle(background_color="#200000",
                      figure_background_color="#000",
                      border_bg_color="#000",

                      star=ObjectStyle(
                          marker=MarkerStyle(
                              fill=FillStyleEnum.FULL,
                              zorder=ZOrderEnum.LAYER_3,
                              size=10,
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

# TODO: MOVE COMBINE
from utils import is_pi
if is_pi():
    ephemeris = "/home/owen/astroflo/de440s.bsp"
else:
    ephemeris = 'de440s.bsp'
planets = load(ephemeris)
ts = load.timescale()

def calculate_arrow_params(center_ra, center_dec, target_ra, target_dec, fov_radius):
    dra = (target_ra - center_ra) * math.cos(math.radians(center_dec))
    ddec = target_dec - center_dec
    distance = math.sqrt(dra**2 + ddec**2)

    if distance == 0:
        return center_ra, center_dec, 0.1, 0

    unit_dra = dra / distance
    unit_ddec = ddec / distance

    min_dist = 0.8
    max_dist = 200

    norm = math.log10(max(distance, min_dist)) / math.log10(max_dist)
    norm = min(max(norm, 0), 1)

    max_arrow_length = fov_radius * 0.55
    min_arrow_length = 0.1

    arrow_length = max(norm * max_arrow_length, min_arrow_length)

    dx = unit_dra * arrow_length
    dy = unit_ddec * arrow_length

    print(f"[Arrow] Distance: {distance:.2f}, Scaled arrow length: {arrow_length:.4f}")

    return center_ra, center_dec, dx, dy

def add_off_field_arrow(plot, center_ra, center_dec, target_ra, target_dec, fov_radius,
                       color="#05ffff", label=None):
    x, y, dx, dy = calculate_arrow_params(center_ra, center_dec, target_ra, target_dec, fov_radius)
    
    # Draw line
    plot.line(
        coordinates=[(x, y), (x + dx, y + dy)],
        style={"color": color, "width": 3, "alpha": 0.5},
    )
    
    plot.marker(
        ra=x + dx,
        dec=y + dy,
        style={
            "marker": {
                "size": 8,
                "symbol": MarkerSymbolEnum.CIRCLE,
                "color": color,
                "alpha": 0.5
            },
        },
        label="",
    )

def add_target_indicator(plot, target_ra, target_dec, fov_radius, color="#05ffff"):
    center_ra, center_dec = plot.ra, plot.dec
    in_field = plot.in_bounds(target_ra, target_dec)
    
    if in_field:
        plot.marker(
            ra=target_ra,
            dec=target_dec,
            style={
                "marker": {
                    "size": 10,
                    "symbol": "circle",
                    "fill": "full",
                    "color": color,
                    "edge_color": "#e0c1e0",
                    "alpha": 0.2
                },
                "label": {
                    "font_size": 100,
                    "font_weight": "bold",
                    "font_color": "#ffffff",
                    "font_alpha": 1,
                    "font_family": "monospace",
                    "zorder": ZOrderEnum.LAYER_3,
                    "offset_x": "auto",
                    "offset_y": "auto",
                },
            }
        )
    else:
        add_off_field_arrow(plot, center_ra, center_dec, target_ra, target_dec, fov_radius, color)

def enhance_telescope_field(telescope, plot=None):
    if plot is None and telescope.get_position() != None:
        plot = create_telescope_field(telescope)
    
    if telescope.target_manager.target is not None:
        target = telescope.target_manager.target

        add_target_indicator(
            plot, 
            target.ra, 
            target.dec, 
            telescope.true_fov()
        )
    
    return plot

def create_telescope_field(telescope: Telescope, resolution=240):
    pos = telescope.get_position()
    ra, dec = pos[0], pos[1]

    plot = OpticPlot(
        ra=ra,
        dec=dec,
        lat=telescope.location.lat.degree,
        lon=telescope.location.lon.degree,
        dt=telescope.get_time().utc_datetime(),
        style=style,
        resolution=resolution,
        optic=telescope.optic(),
        ephemeris=ephemeris,
        raise_on_below_horizon=False,
    )

    lim = telescope.get_limiting_magnitude()

    plot.stars(
        where_labels=[_.magnitude < 2.5], #where=[_.magnitude < 9], 
        size_fn=lambda star: np.clip(5 * (lim - star.magnitude), 0 , 1000),
        alpha_fn=lambda star: np.clip(1 - (star.magnitude/lim), 0, 1),
        catalog='big-sky')

    plot.dsos(where=[_.magnitude < lim,])
    plot.moon()
    plot.planets()

    plot.rotate = telescope.viewing_angle
    
    return plot