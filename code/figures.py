"""Reproduce Figures 2-4 of Korinek et al. (2026): the three scenarios, January 2025 to January 2030.

Usage (repository root): ``uv run --group docs python code/figures.py``. Writes
``content/figures/figure-{2,3,4}.png``. Each line ends in a marker at its January 2030 value,
labeled with that value; the dashed line is the economy without AI.
"""

from __future__ import annotations

import logging
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")

from typing import TYPE_CHECKING

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.text
import numpy as np
import theme
from econ_scenarios import EXTREME, MODEST, SUBSTANTIAL, Simulation, simulate
from theme import (
    ANCHOR_LINE,
    DATUM,
    GRID,
    INK,
    LABEL,
    MUTED,
    SCENARIO_COLORS,
    TEXT_WIDTH,
    TITLE,
    TITLE_WEIGHT,
    WIDE_WIDTH,
)

if TYPE_CHECKING:
    from collections.abc import Callable

log = logging.getLogger("figures")
OUT = Path(__file__).resolve().parents[1] / "content" / "figures"

COLORS = SCENARIO_COLORS
LABELS = {"modest": "Modest", "substantial": "Substantial", "extreme": "Extreme"}
NO_AI = DATUM
START, END = 2025.0, 2030.0
ANCHOR = 2026.5  # the scenarios' paths coincide until their mid-2026 anchor
DPI = 300  # figures are laid out, checked and saved at this resolution, at their printed width
MAX_PANELS = 3  # house rule: at most three panels to a figure, side by side

theme.apply()


@dataclass(frozen=True)
class Panel:
    title: str
    subtitle: str
    series: Callable[[Simulation], np.ndarray]  # plotted values, one per month
    no_ai: float
    # a part of ``series`` drawn dotted under it, which the subtitle names
    part: Callable[[Simulation], np.ndarray] | None = None


def _gdp(sim: Simulation) -> np.ndarray:
    return 100 * np.expm1(sim["lnY"])


def _gdp_growth(sim: Simulation) -> np.ndarray:
    cal = sim.calibration
    lnY = sim["lnY"]
    growth = np.full_like(lnY, np.nan)
    growth[12:] = 100 * (cal.g + cal.n + lnY[12:] - lnY[:-12])
    return growth


def _employment_C(sim: Simulation) -> np.ndarray:
    return 100 * (sim["ell_C"] / sim["ell_C"][sim.index(sim.calibration.t_anchor)] - 1)


def _unemployment_C(sim: Simulation) -> np.ndarray:
    return 100 * sim["U_C"] / (sim["U_C"] + sim["ell_C"])


def figure_panels(sim: Simulation) -> dict[str, list[Panel]]:
    """The panels of Figures 2-4 and the no-AI value of each."""
    cal = sim.calibration
    ss = sim.steady
    return {
        "figure-2": [
            Panel("GDP", "percent above the no-AI path", _gdp, 0.0),
            Panel(
                "GDP Growth",
                "percent per year; 2 percent a year without AI",
                _gdp_growth,
                100 * (cal.g + cal.n),
            ),
        ],
        # The paper's Figure 3 has four panels; a figure here has at most three, in one row, so
        # it is drawn as two figures of two.
        "figure-3a": [
            Panel(
                "Average Wage",
                "percent above the no-AI path",
                lambda s: 100 * np.expm1(s["lnW_avg"]),
                0.0,
            ),
            Panel(
                "Cognitive Wage",
                "percent above the no-AI path",
                lambda s: 100 * np.expm1(s["lnW_C"]),
                0.0,
            ),
        ],
        "figure-3b": [
            Panel(
                "Net Return to Capital",
                "percent per year; 6.5 without AI",
                lambda s: 100 * s["net_return"],
                100 * (cal.r_bar - cal.delta),
            ),
            Panel(
                "Labor Share",
                "percent of income; 60 without AI",
                lambda s: 100 * cal.s_L * np.exp(s["lnSL"]),
                100 * cal.s_L,
            ),
        ],
        "figure-4": [
            Panel(
                "Cognitive Employment",
                "percent change since mid-2026",
                _employment_C,
                0.0,
            ),
            Panel(
                "Unemployment Rate, Cognitive",
                "percent of the group's labor force",
                _unemployment_C,
                100 * ss.U[0] / (ss.U[0] + ss.ell0[0]),
            ),
            Panel(
                "Unemployment Rate, All Workers",
                "percent of the labor force",
                lambda s: 100 * s["U_total"],
                100 * cal.U_bar,
            ),
        ],
    }


def _place(values: list[float], gap: float) -> list[float]:
    """Label heights: each value nudged apart so neighbors sit at least ``gap`` from one another."""
    order = sorted(range(len(values)), key=values.__getitem__)
    placed = [0.0] * len(values)
    floor = -math.inf
    for i in order:
        placed[i] = max(values[i], floor + gap)
        floor = placed[i]
    return placed


def chrome(ax, grid_axis: str = "y") -> None:
    """Spines, grid, and tick length, the same on every axes this repository draws."""
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(axis=grid_axis, color=GRID, lw=0.5)
    ax.set_axisbelow(True)
    ax.tick_params(length=2)


def panel_title(ax, title: str) -> None:
    """A panel's title, left-aligned in the house weight and colour."""
    ax.set_title(
        title,
        loc="left",
        fontsize=TITLE,
        fontweight=TITLE_WEIGHT,
        color=INK,
        # Room for the subtitle frame() draws under the title. A face with a taller ascent or
        # line gap needs more; layout_overlaps fails the render when this is short.
        pad=14,
    )


def frame(
    ax,
    panel: Panel,
    right: float = END,
    start: float = START,
    anchor: bool = True,
) -> None:
    """The panel's axes, grid, title, and subtitle, shared by these figures, the Explore page, and
    every figure a paper here draws.
    """
    ax.set_xlim(start, right)
    years = range(int(start), 2031)
    # at printed width a panel holds six year labels; a longer run is labeled every other year
    ax.set_xticks(years if len(years) <= 6 else years[::2])
    if anchor:
        ax.axvline(ANCHOR, color=ANCHOR_LINE, lw=0.8, zorder=0, label="mid-2026 anchor")
    chrome(ax)
    panel_title(ax, panel.title)
    ax.text(
        0,
        1.025,
        panel.subtitle,
        transform=ax.transAxes,
        fontsize=LABEL,
        color=MUTED,
        va="bottom",
    )


def draw_panel(ax, panel: Panel, sims: dict[str, Simulation]) -> None:
    ends = []
    for name, sim in sims.items():
        t = sim.t
        keep = (t >= START - 1e-9) & (t <= END + 1e-9)
        y = panel.series(sim)[keep]
        if panel.part is not None:
            ax.plot(
                t[keep],
                panel.part(sim)[keep],
                color=COLORS[name],
                lw=1.0,
                ls=(0, (1.2, 1.6)),
                zorder=2,
            )
        ax.plot(
            t[keep],
            y,
            color=COLORS[name],
            lw=1.5,
            solid_capstyle="round",
            label=LABELS[name],
        )
        ax.plot(
            [t[keep][-1]],
            [y[-1]],
            "o",
            ms=3.2,
            color=COLORS[name],
            mec="white",
            mew=0.6,
            zorder=4,
        )
        # the value alone, in the line's color; the scenario is in the legend below
        ends.append((f"{y[-1]:.1f}", y[-1], COLORS[name]))
    ax.axhline(
        panel.no_ai,
        color=NO_AI,
        lw=0.9,
        ls=(0, (4, 3)),
        zorder=1,
        label="No AI",
    )
    ends.append((f"{panel.no_ai:.1f}", panel.no_ai, MUTED))
    frame(ax, panel, right=END + 0.05)
    label_ends(ax, ends)


def label_ends(ax, ends: list[tuple[str, float, str]], gap: float = 0.11) -> None:
    """Label each line at its right end, value first, nudging labels apart by ``gap`` of the y-span
    and joining a moved label to its line with a short leader.

    ``gap`` is a fraction of the y-span. At the one figure height these panels are drawn at, that
    fraction is the room a label's cap height takes, so the value depends on the face in
    ``theme.FAMILY``: 0.095 was enough for Libre Franklin, 0.105 for Roboto, and Fira Sans clears
    at the 0.11 set here. ``layout_overlaps`` is what checks it, and fails the render when a face
    needs more room than the value allows.
    """
    lo, hi = ax.get_ylim()
    span = hi - lo
    heights = _place([v for _, v, _ in ends], gap=gap * span)
    top = max(heights) + 0.04 * span
    if top > hi:
        ax.set_ylim(lo, top)
    for (text, value, color), height in zip(ends, heights, strict=False):
        if abs(height - value) > 0.01 * span:
            ax.plot(
                [END + 0.05, END + 0.2],
                [value, height],
                color=GRID,
                lw=0.5,
                clip_on=False,
            )
        ax.text(
            END + 0.25,
            height,
            text,
            ha="left",
            va="center",
            fontsize=LABEL,
            color=color,
            clip_on=False,
        )


def build(panels: list[Panel], sims: dict[str, Simulation]):
    """Lay at most three panels out in one row, with a shared legend below."""
    if len(panels) > MAX_PANELS:
        msg = (
            f"a figure takes at most {MAX_PANELS} panels, in one row; got {len(panels)}"
        )
        raise ValueError(msg)
    fig, axes = plt.subplots(1, len(panels))
    axes = np.atleast_1d(axes).ravel()
    fig.set_size_inches(WIDE_WIDTH if len(panels) == MAX_PANELS else TEXT_WIDTH, 2.2)
    fig.set_dpi(DPI)
    for ax, panel in zip(axes, panels, strict=False):
        draw_panel(ax, panel, sims)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="lower center",
        ncol=len(handles),
        frameon=False,
        fontsize=LABEL,
        handlelength=1.6,
        columnspacing=1.2,
        bbox_to_anchor=(0.5, 0.0),
    )
    fig.tight_layout(rect=(0, 0.09, 1, 1), w_pad=2.2)
    return fig


def render(name: str, panels: list[Panel], sims: dict[str, Simulation]) -> Path:
    fig = build(panels, sims)
    path = OUT / f"{name}.png"
    fig.savefig(path, dpi=DPI, metadata={"Software": None}, facecolor="white")
    overlaps = layout_overlaps(fig)
    plt.close(fig)
    if overlaps:
        msg = f"{name}: overlapping text: {overlaps}"
        raise RuntimeError(msg)
    return path


def layout_overlaps(fig) -> list[tuple[str, str]]:
    """Visible text boxes that overlap each other, a spine they do not belong to, or leave the figure."""
    renderer = fig.canvas.get_renderer()
    fig.draw(renderer)
    ticks = {
        id(t.label1): t
        for ax in fig.axes
        for axis in (ax.xaxis, ax.yaxis)
        for t in axis.get_major_ticks()
    }
    drawn = set()
    for ax in fig.axes:
        for axis in (ax.xaxis, ax.yaxis):
            lo, hi = sorted(axis.get_view_interval())
            drawn |= {
                id(t.label1)
                for t in axis.get_major_ticks()
                if lo - 1e-9 <= t.get_loc() <= hi + 1e-9
            }
    texts = [
        (t, t.get_window_extent(renderer))
        for t in fig.findobj(mpl.text.Text)
        if t.get_text().strip()
        and t.get_visible()
        and (id(t) not in ticks or id(t) in drawn)
    ]
    own = set(ticks)
    spines = [
        s.get_window_extent(renderer)
        for ax in fig.axes
        for s in ax.spines.values()
        if s.get_visible()
    ]
    found = []
    for i, (a, box_a) in enumerate(texts):
        if not fig.bbox.contains(box_a.x0, box_a.y0) or not fig.bbox.contains(
            box_a.x1,
            box_a.y1,
        ):
            found.append((a.get_text(), "outside the figure"))
        for b, box_b in texts[i + 1 :]:
            if box_a.overlaps(box_b):
                found.append((a.get_text(), b.get_text()))
        if id(a) not in own and any(box_a.overlaps(s) for s in spines):
            found.append((a.get_text(), "a spine"))
    return found


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    OUT.mkdir(parents=True, exist_ok=True)
    sims = {s.name: simulate(s) for s in (MODEST, SUBSTANTIAL, EXTREME)}
    for name, panels in figure_panels(sims["modest"]).items():
        log.info("wrote %s", render(name, panels, sims))
    return 0


if __name__ == "__main__":
    sys.exit(main())
