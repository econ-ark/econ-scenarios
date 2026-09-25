"""Path-level agreement between this package and the explorer oracle."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from econ_scenarios import simulate

from .oracle import ROW_MAP, explorer_series, run_explorer

if TYPE_CHECKING:
    from econ_scenarios import Simulation

    from .cases import Case


def path_differences(sim: Simulation, raw: dict) -> dict[str, float]:
    """Largest absolute difference, over all months, of every series both sides report."""
    theirs = explorer_series(raw)
    if len(theirs["t"]) != len(sim.t):
        msg = f"row counts differ: explorer {len(theirs['t'])}, package {len(sim.t)}"
        raise ValueError(
            msg,
        )
    return {name: float(np.max(np.abs(sim[name] - theirs[name]))) for name in ROW_MAP}


def worst(differences: dict[str, float]) -> tuple[str, float]:
    """The series with the largest difference."""
    name = max(differences, key=differences.__getitem__)
    return name, differences[name]


def case_gap(spec: Case) -> tuple[Simulation, str, float]:
    """The reproduction's run of one oracle case, and the series farthest from the explorer's
    run of it with that distance.
    """
    sim = simulate(spec.scenario, spec.cal, horizon=spec.horizon, level_form=spec.form)
    raw = run_explorer(
        spec.scenario,
        spec.cal,
        horizon=spec.horizon,
        level_form=spec.form,
    )
    return sim, *worst(path_differences(sim, raw))
