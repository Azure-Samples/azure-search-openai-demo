from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.patches import RegularPolygon
from matplotlib.path import Path as MatPath
from matplotlib.projections import register_projection
from matplotlib.projections.polar import PolarAxes
from matplotlib.spines import Spine
from matplotlib.transforms import Affine2D


def save_figure(output_path: Path, format: str = "pdf"):
    """Save the current figure to the provided output path."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, bbox_inches="tight", format=format)


def plot_bar_charts(
    layout: Tuple[int, int],
    data: List[Dict[str, any]],
    titles: List[str],
    y_labels: List[str],
    output_path: Path,
    y_max_lim: List[float] = None,
    width: float = 0.4,
):
    """Plot bar charts for the provided data."""
    if layout[0] * layout[1] != len(data):
        raise ValueError("Number of data points must match the layout")

    font = {"weight": "normal", "size": 9}

    matplotlib.rc("font", **font)

    fig, axs = plt.subplots(layout[0], layout[1], figsize=(layout[1] * 5, layout[0] * 4))
    fig.tight_layout(pad=3.0)

    if axs is not np.ndarray:
        axs = np.array([axs])

    for i, ax in enumerate(axs.flat):
        x_data = list(data[i].keys())
        y_data = list(data[i].values())
        name = titles[i]
        colors = plt.cm.tab20.colors[: len(x_data)]

        ax.bar(x_data, y_data, width=width, label=name, color=colors)
        ax.set_title(name, pad=20)
        if y_max_lim is not None and len(y_max_lim) > i and y_max_lim[i] is not None:
            ax.set_ylim(0, max(y_max_lim[i], max(y_data)))
        else:
            ax.set_ylim(0, np.ceil(max(y_data)) * 1.2)

        ax.set_ylabel(y_labels[i])

        for j, v in enumerate(y_data):
            ax.text(j, v * 1.02, str(round(v, 2)), ha="center")

    save_figure(output_path)
    plt.close(fig)


def plot_box_charts_grid(
    layout: Tuple[int, int], data: List[List[float]], titles: List[str], y_labels: List[str], output_path: Path
):
    """Plot box charts for the provided data in a single figure."""
    if layout[0] * layout[1] != len(data):
        raise ValueError("Number of data points must match the layout")

    fig, axs = plt.subplots(layout[0], layout[1], figsize=(layout[1] * 5, layout[0] * 4))
    fig.tight_layout(pad=3.0)

    if axs is not np.ndarray:
        axs = np.array([axs])

    for i, ax in enumerate(axs.flat):
        ax.boxplot(data[i])
        ax.set_title(titles[i])
        ax.set_ylabel(y_labels[i])

    save_figure(output_path)
    plt.close(fig)


def plot_box_chart(
    data: List[float],
    title: str,
    x_labels: List[str],
    y_label: str,
    output_path: Path,
    y_lim: Tuple[float, float] = None,
):
    """Plot a box chart for the provided data."""
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.boxplot(data, patch_artist=True, tick_labels=x_labels)
    fig.tight_layout(pad=3.0)
    ax.set_title(title)
    ax.set_ylabel(y_label)
    if y_lim is not None:
        ax.set_ylim(y_lim[0], y_lim[1])
    save_figure(output_path)
    plt.close(fig)


def plot_radar_chart(metric_label_list: List[str], data: List, title: str, _range: int, output_path: Path):
    theta = radar_factory(num_vars=len(metric_label_list))
    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(projection="radar"))
    fig.subplots_adjust(wspace=0.5, hspace=0.20, top=0.85, bottom=0.05)

    color = "c"  # Cyan

    ax.set_title(title, weight="bold", size="large", horizontalalignment="center", verticalalignment="center", pad=20)
    ax.plot(theta, data, color=color)
    ax.fill(theta, data, facecolor=color, alpha=0.25, label="_nolegend_")
    ax.tick_params(pad=15)
    ax.set_rgrids(range(_range + 1), angle=10)
    ax.set_varlabels(metric_label_list)

    save_figure(output_path)
    plt.close(fig)


# The following code is adapted from the Matplotlib documentation:
# https://matplotlib.org/stable/gallery/specialty_plots/radar_chart.html


def radar_factory(num_vars):
    """
    Create a radar chart with `num_vars` Axes.
    This function creates a RadarAxes projection and registers it.

    Parameters
    ----------
    num_vars : int
        Number of variables for radar chart.
    """
    # calculate evenly-spaced axis angles
    theta = np.linspace(0, 2 * np.pi, num_vars, endpoint=False)

    class RadarTransform(PolarAxes.PolarTransform):

        def transform_path_non_affine(self, path):
            # Paths with non-unit interpolation steps correspond to gridlines,
            # in which case we force interpolation (to defeat PolarTransform's
            # autoconversion to circular arcs).
            if path._interpolation_steps > 1:
                path = path.interpolated(num_vars)
            return MatPath(self.transform(path.vertices), path.codes)

    class RadarAxes(PolarAxes):

        name = "radar"
        PolarTransform = RadarTransform

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # rotate plot such that the first axis is at the top
            self.set_theta_zero_location("N")

        def fill(self, *args, closed=True, **kwargs):
            """Override fill so that line is closed by default"""
            return super().fill(closed=closed, *args, **kwargs)

        def plot(self, *args, **kwargs):
            """Override plot so that line is closed by default"""
            lines = super().plot(*args, **kwargs)
            for line in lines:
                self._close_line(line)

        def _close_line(self, line):
            x, y = line.get_data()
            # FIXME: markers at x[0], y[0] get doubled-up
            if x[0] != x[-1]:
                x = np.append(x, x[0])
                y = np.append(y, y[0])
                line.set_data(x, y)

        def set_varlabels(self, labels):
            self.set_thetagrids(np.degrees(theta), labels)
            self.xaxis.set_tick_params(pad=15)

        def _gen_axes_patch(self):
            # The Axes patch must be centered at (0.5, 0.5) and of radius 0.5
            # in axes coordinates.
            return RegularPolygon((0.5, 0.5), num_vars, radius=0.5, edgecolor="k")

        def _gen_axes_spines(self):
            # spine_type must be 'left'/'right'/'top'/'bottom'/'circle'.
            spine = Spine(axes=self, spine_type="circle", path=MatPath.unit_regular_polygon(num_vars))
            # unit_regular_polygon gives a polygon of radius 1 centered at
            # (0, 0) but we want a polygon of radius 0.5 centered at (0.5,
            # 0.5) in axes coordinates.
            spine.set_transform(Affine2D().scale(0.5).translate(0.5, 0.5) + self.transAxes)
            return {"polar": spine}

    register_projection(RadarAxes)
    return theta
