"""The explorer's other features against the explorer: the quiz, its data options, longer horizons, the mu-bar fit."""

import numpy as np
import pytest
from econ_scenarios import (
    EXTREME,
    MODEST,
    SUBSTANTIAL,
    SWITCHING,
    Calibration,
    answers_to_scenario,
    fit_mu_bar,
    mu_from_switching_odds,
    preset_answers,
    simulate,
)
from validation.cases import DATA_OPTIONS, PATH_TOLERANCE, QUIZ
from validation.compare import path_differences, worst
from validation.oracle import run_explorer, run_explorer_quiz


@pytest.mark.parametrize("case", list(QUIZ))
def test_quiz_paths_match_explorer(case) -> None:
    answers = QUIZ[case]
    sim = simulate(answers_to_scenario(answers), horizon=2035.0)
    name, gap = worst(path_differences(sim, run_explorer_quiz(answers)))
    assert gap < PATH_TOLERANCE, f"{case}: {name} differs by {gap:.3e}"


@pytest.mark.parametrize(
    "scenario",
    [MODEST, SUBSTANTIAL, EXTREME],
    ids=lambda s: s.name,
)
def test_preset_answers_reproduce_the_preset(scenario) -> None:
    """The quiz asks five things; reinstatement and posting speed come from the base scenario."""
    quiz = simulate(answers_to_scenario(preset_answers(scenario), base=scenario))
    paper = simulate(scenario)
    for name in ("lnY", "lnW_C", "lnW_N", "U_C", "U_N", "net_return"):
        np.testing.assert_allclose(quiz[name], paper[name], rtol=0, atol=PATH_TOLERANCE)


@pytest.mark.parametrize("option", list(DATA_OPTIONS))
def test_data_options_match_explorer(option) -> None:
    cal = DATA_OPTIONS[option]
    sim = simulate(EXTREME, cal)
    name, gap = worst(path_differences(sim, run_explorer(EXTREME, cal)))
    assert gap < PATH_TOLERANCE, f"{option}: {name} differs by {gap:.3e}"


@pytest.mark.parametrize("scenario", [MODEST, EXTREME], ids=lambda s: s.name)
def test_horizon_2040_matches_explorer(scenario) -> None:
    sim = simulate(scenario, horizon=2040.0)
    name, gap = worst(path_differences(sim, run_explorer(scenario, horizon=2040.0)))
    assert (
        len(sim.t)
        == round((2040.0 - sim.calibration.t0) * sim.calibration.months_per_year) + 1
    )
    assert gap < PATH_TOLERANCE, f"{scenario.name}: {name} differs by {gap:.3e}"


@pytest.mark.parametrize("matrix", list(SWITCHING))
def test_fitted_mu_bar_matches_explorer(matrix) -> None:
    raw = run_explorer(SUBSTANTIAL, matrix=matrix)
    assert (
        abs(fit_mu_bar(Calibration(), SWITCHING[matrix]["pooled"]) - raw["muFitted"])
        < 1e-12
    )


def test_odds_rule_on_the_corrected_matrix() -> None:
    """Section 3.2's odds-product rule on the unrounded 2010-19 switching shares (explorer record: 0.17088411761765862)."""
    assert (
        abs(
            mu_from_switching_odds(SWITCHING["CPS 2010-19"]["switch_share"])
            - 0.17088411761765862,
        )
        < 1e-15
    )
