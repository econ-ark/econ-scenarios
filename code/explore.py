"""The interactive scenario explorer of the report's Explore page.

Sliders set a scenario's assumptions (Table 1, panels B and C) and two calibration numbers; the
page redraws the reproduction's paths to 2030 against the paper's three scenarios. Every number
comes from ``econ_scenarios.simulate``: this module maps controls to a ``Scenario`` and a
``Calibration`` and draws the result.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

import ipywidgets as widgets
import matplotlib.pyplot as plt
from econ_scenarios import (
    EXTREME,
    MODEST,
    SUBSTANTIAL,
    Calibration,
    Scenario,
    Simulation,
    readout,
    simulate,
)
from figures import (
    COLORS,
    DPI,
    END,
    INK,
    LABELS,
    NO_AI,
    START,
    Panel,
    figure_panels,
    frame,
)
from IPython.display import HTML, Image, display
from theme import LABEL, WIDE_WIDTH

if TYPE_CHECKING:
    import numpy as np

PRESETS = {s.name: s for s in (MODEST, SUBSTANTIAL, EXTREME)}


@dataclass(frozen=True)
class Control:
    field: str  # a field of Scenario, or of Calibration when ``calibration`` is set
    label: str
    lo: float
    hi: float
    step: float
    calibration: bool = False


CONTROLS = (
    Control("m_2030", "affected mass, 2030", 0.15, 0.60, 0.01),
    Control("d_2030", "diffusion share, 2030", 0.11, 0.95, 0.01),
    Control("a_anchor", "log gain per instance, mid-2026", 0.0, 1.0, 0.01),
    Control("g_a", "slope of the log gain, per year", 0.0, 0.2, 0.002),
    Control("psi", "automation share", 0.02, 0.98, 0.01),
    Control("rho", "reinstatement ratio", 0.0, 1.0, 0.01),
    Control("mu", "search discount on the path", 0.0, 1.0, 0.01),
    Control("theta_H", "posting speed, per month", 0.02, 1.0, 0.01),
    Control(
        "xi",
        "rigidity of the cognitive wage, per year",
        0.0,
        0.95,
        0.05,
        calibration=True,
    ),
    Control("eps", "elasticity of capital supply", 0.5, 10.0, 0.5, calibration=True),
)

# (readout key, row label) for the 2030 table under the figure
ROWS = (
    ("gdp", "GDP, pct. above no AI"),
    ("gdp_growth", "GDP growth, pct. a year"),
    ("wage_avg", "average wage, pct. above no AI"),
    ("wage_C", "cognitive wage, pct. above no AI"),
    ("labor_share", "labor share, pct."),
    ("employment_C", "cognitive employment, pct. since mid-2026"),
    ("unemployment_C", "cognitive unemployment rate, pct."),
    ("unemployment", "unemployment rate, pct."),
)


def values_of(scenario: Scenario, cal: Calibration) -> dict[str, float]:
    """The controls' settings that reproduce ``scenario`` under ``cal``."""
    return {
        c.field: getattr(cal if c.calibration else scenario, c.field) for c in CONTROLS
    }


def scenario_from(values: dict[str, float]) -> tuple[Scenario, Calibration]:
    """The scenario and calibration the controls describe, the rest at the paper's values."""
    scenario = replace(
        SUBSTANTIAL,
        name="yours",
        **{c.field: values[c.field] for c in CONTROLS if not c.calibration},
    )
    cal = replace(
        Calibration(),
        **{c.field: values[c.field] for c in CONTROLS if c.calibration},
    )
    return scenario, cal


def preset_runs() -> dict[str, Simulation]:
    """The paper's three scenarios at the paper's calibration."""
    return {name: simulate(s) for name, s in PRESETS.items()}


def _window(sim: Simulation, panel: Panel) -> tuple[np.ndarray, np.ndarray]:
    keep = (sim.t >= START - 1e-9) & (sim.t <= END + 1e-9)
    return sim.t[keep], panel.series(sim)[keep]


def draw(values: dict[str, float], presets: dict[str, Simulation]):
    """Three panels of Figures 2-4 in a row for the controls' scenario, GDP, the average wage, and
    unemployment, with the paper's scenarios behind it. Returns the figure and the scenario's 2030
    readout, which carries the series the row leaves out.
    """
    scenario, cal = scenario_from(values)
    yours = simulate(scenario, cal)
    panels = figure_panels(yours)
    chosen = (
        panels["figure-2"][0],
        panels["figure-3a"][0],
        panels["figure-4"][2],
    )
    fig, axes = plt.subplots(1, 3, figsize=(WIDE_WIDTH, 2.2), layout="constrained")
    fig.set_dpi(DPI)
    for ax, panel in zip(axes, chosen, strict=True):
        for name, sim in presets.items():
            ax.plot(
                *_window(sim, panel),
                color=COLORS[name],
                lw=1.0,
                alpha=0.6,
                label=f"{LABELS[name]} (paper)",
            )
        ax.plot(
            *_window(yours, panel),
            color=INK,
            lw=1.7,
            solid_capstyle="round",
            label="Your scenario",
        )
        ax.axhline(
            panel.no_ai,
            color=NO_AI,
            lw=1.0,
            ls=(0, (4, 3)),
            zorder=1,
            label="No AI",
        )
        frame(ax, panel)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="outside lower center",
        ncol=len(handles),
        frameon=False,
        fontsize=LABEL,
    )
    return fig, readout(yours)


def png(fig) -> Image:
    """The figure as a PNG, displayed the same way under every matplotlib backend."""
    buffer = io.BytesIO()
    fig.savefig(
        buffer,
        format="png",
        dpi=DPI,
        metadata={"Software": None},
        facecolor="white",
    )
    plt.close(fig)
    return Image(buffer.getvalue())


def table(rows: dict[str, float], presets: dict[str, Simulation]) -> HTML:
    """The scenario's 2030 values next to the paper's scenarios, as an HTML table."""
    reports = {name: readout(sim) for name, sim in presets.items()}
    head = "".join(f'<th class="num">{LABELS[name]}</th>' for name in reports)
    body = "".join(
        f'<tr><td>{label}</td><td class="num here">{rows[key]:.1f}</td>'
        + "".join(f'<td class="num">{rep[key]:.1f}</td>' for rep in reports.values())
        + "</tr>"
        for key, label in ROWS
    )
    return HTML(
        f'<table class="es-table"><tr><th>In 2030</th><th class="num">Yours</th>{head}</tr>{body}</table>',
    )


class Explorer:
    """Sliders, a row of starting points, and the redrawn figure and table."""

    def __init__(self, start: str = "substantial") -> None:
        self.presets = preset_runs()
        values = values_of(PRESETS[start], Calibration())
        style = {"description_width": "20em"}  # wide enough for the longest label
        layout = widgets.Layout(width="95%")
        self.sliders = {
            c.field: widgets.FloatSlider(
                value=values[c.field],
                min=c.lo,
                max=c.hi,
                step=c.step,
                description=c.label,
                readout_format=".3g",
                continuous_update=False,
                style=style,
                layout=layout,
            )
            for c in CONTROLS
        }
        self.start = widgets.ToggleButtons(
            options=list(PRESETS),
            value=start,
            description="Start from",
        )
        self.output = widgets.Output()
        self._loading = False
        for slider in self.sliders.values():
            slider.observe(self.refresh, "value")
        self.start.observe(self.load, "value")
        self.widget = widgets.VBox([self.start, *self.sliders.values(), self.output])
        self.refresh()

    def values(self) -> dict[str, float]:
        return {field: slider.value for field, slider in self.sliders.items()}

    def load(self, change=None) -> None:
        """Move every slider to the chosen scenario, then redraw once."""
        self._loading = True
        for field, value in values_of(PRESETS[self.start.value], Calibration()).items():
            self.sliders[field].value = value
        self._loading = False
        self.refresh()

    def refresh(self, change=None) -> None:
        if self._loading:
            return
        fig, rows = draw(self.values(), self.presets)
        with self.output:
            self.output.clear_output(wait=True)
            display(png(fig), table(rows, self.presets))


def still(start: str = "substantial") -> None:
    """What the explorer shows first, as a still image and table, for a page built without a browser."""
    presets = preset_runs()
    fig, rows = draw(values_of(PRESETS[start], Calibration()), presets)
    display(png(fig), table(rows, presets))
