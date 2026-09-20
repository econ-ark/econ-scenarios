"""Path-level agreement between this package and the explorer oracle."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from .oracle import ROW_MAP, explorer_series

if TYPE_CHECKING:
    from econ_scenarios import Simulation


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
