"""The Explore page's controls reproduce the paper's scenarios, and its figure lays out cleanly."""

import numpy as np
import pytest
from econ_scenarios import EXTREME, MODEST, SUBSTANTIAL, Calibration, simulate
from explore import (
    CONTROLS,
    PRESETS,
    Explorer,
    draw,
    preset_runs,
    scenario_from,
    values_of,
)
from figures import layout_overlaps


@pytest.mark.parametrize("preset", [MODEST, SUBSTANTIAL, EXTREME], ids=lambda s: s.name)
def test_controls_reproduce_each_preset(preset) -> None:
    values = values_of(preset, Calibration())
    for c in CONTROLS:
        v = values[c.field]
        assert c.lo <= v <= c.hi, f"{c.field} = {v} is outside its slider"
        steps = (v - c.lo) / c.step
        assert abs(steps - round(steps)) < 1e-9, (
            f"{c.field} = {v} is off its slider's steps"
        )
    scenario, cal = scenario_from(values)
    reference, sim = simulate(preset), simulate(scenario, cal)
    for name in reference.series:
        np.testing.assert_array_equal(sim[name], reference[name])


def test_calibration_controls_reach_the_simulation() -> None:
    values = values_of(SUBSTANTIAL, Calibration()) | {"xi": 0.0}
    scenario, cal = scenario_from(values)
    assert cal.xi == 0.0
    assert not np.array_equal(
        simulate(scenario, cal)["lnW_C"],
        simulate(SUBSTANTIAL)["lnW_C"],
    )


def test_figure_has_no_overlapping_text() -> None:
    fig, rows = draw(values_of(EXTREME, Calibration()), preset_runs())
    assert layout_overlaps(fig) == []
    assert len(fig.axes) == 3  # at most three panels to a figure, in one row
    assert set(rows) >= {"gdp", "unemployment"}


def test_choosing_a_starting_point_moves_every_slider() -> None:
    explorer = Explorer()
    explorer.start.value = "modest"
    assert explorer.values() == values_of(PRESETS["modest"], Calibration())
