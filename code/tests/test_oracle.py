"""Instrument 1: full monthly paths against the authors' public explorer, at machine precision."""

import pytest
from econ_scenarios import simulate
from validation.cases import ORACLE_CASES, PATH_TOLERANCE
from validation.compare import path_differences, worst
from validation.oracle import run_explorer


@pytest.mark.parametrize("case", list(ORACLE_CASES))
def test_paths_match_explorer(case) -> None:
    scenario, cal, horizon, form, _label = ORACLE_CASES[case]
    sim = simulate(scenario, cal, horizon=horizon, level_form=form)
    raw = run_explorer(scenario, cal, horizon=horizon, level_form=form)
    assert not raw["diag"].get("stoppedAt"), raw["diag"]
    name, gap = worst(path_differences(sim, raw))
    assert gap < PATH_TOLERANCE, f"{case}: {name} differs by {gap:.3e}"
