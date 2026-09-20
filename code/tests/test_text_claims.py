"""Claims the paper states as bounds or comparisons, which a rounding check cannot express."""

import math
from dataclasses import replace

import numpy as np
import pytest
from econ_scenarios import EXTREME, MODEST, SUBSTANTIAL, Calibration, readout, simulate
from validation.published import cognitive_profit_share

SCENARIOS3 = (MODEST, SUBSTANTIAL, EXTREME)
CAL = Calibration()
# Every run behind Tables 3, 5 and 6.
TABLE_RUNS = [(s, CAL) for s in SCENARIOS3]
TABLE_RUNS += [
    (s, replace(CAL, eps=e))
    for s in (SUBSTANTIAL, EXTREME)
    for e in (1.0, 6.0, math.inf)
]
TABLE_RUNS += [(SUBSTANTIAL, replace(CAL, xi=x)) for x in (0.75, 0.9)]
TABLE_RUNS += [(EXTREME, replace(CAL, xi=x)) for x in (0.0, 0.75, 0.9)]


def ideas_closed_form(sim) -> float:
    """Eq. (43) at the last date, integrating the research uplift (the actual GDP gap) by the trapezoid rule."""
    cal = sim.calibration
    t = sim.t - cal.t0
    decay = cal.one_minus_phi_R * cal.g
    integrand = np.exp(-decay * (t[-1] - t)) * np.exp(cal.lam * sim["lnY"])
    integral = float(np.sum(0.5 * (integrand[1:] + integrand[:-1]) * np.diff(t)))
    return math.log(math.exp(-decay * t[-1]) + decay * integral) / cal.one_minus_phi_R


@pytest.mark.parametrize(
    ("scenario", "cal"),
    TABLE_RUNS,
    ids=lambda v: getattr(v, "name", None) or f"eps{v.eps}-xi{v.xi}",
)
def test_cognitive_firms_profit_is_at_most_half_a_percent_of_gdp(scenario, cal) -> None:
    """Table A.1, panel D: cognitive firms' profit (MPL_C - w_C) l_C is at most half a percent of GDP on the paths."""
    assert cognitive_profit_share(simulate(scenario, cal)) <= 0.5


def test_monthly_ideas_step_is_within_two_hundredths_of_a_point_of_the_closed_form() -> (
    None
):
    """Appendix A: on the extreme path the ideas update is within 0.02 percentage points of Eq. (43) in 2030."""
    sim = simulate(EXTREME)
    step = sim["dlnA"][-1]
    assert abs(step - ideas_closed_form(sim)) <= 0.0002
    assert (
        abs(step - ideas_closed_form(sim)) > 0.0
    )  # the monthly step differs from the closed form


@pytest.mark.parametrize("scenario", SCENARIOS3, ids=lambda s: s.name)
def test_gdp_gap_at_t0_is_at_most_a_quarter_of_a_percent(scenario) -> None:
    """Appendix A: at t0 the AI objects imply a GDP gap of at most a quarter of a percent."""
    assert abs(math.expm1(simulate(scenario)["lnY"][0])) <= 0.0025


def test_scenarios_coincide_at_mid_2026_and_differ_by_tenths_of_a_percent_before() -> (
    None
):
    """Section 3.3: the logistic paths coincide at mid-2026, and before it the scenarios are within a
    few tenths of a percent of GDP of one another. The gains, automation shares and reinstatement
    ratios differ by scenario at the anchor, so GDP does not coincide there: the spread grows from
    0.21 percent at t0 to 0.66 percent at the anchor, which the test reads as under one point.
    """
    sims = [simulate(s) for s in SCENARIOS3]
    k = sims[0].index(CAL.t_anchor)
    for name in ("m", "d"):
        assert np.ptp([s[name][k] for s in sims]) < 1e-13
    gdp = np.array([np.expm1(s["lnY"][: k + 1]) for s in sims])
    spread = gdp.max(axis=0) - gdp.min(axis=0)
    assert spread.max() < 0.01
    assert spread[0] < 0.0025


@pytest.mark.parametrize("scenario", SCENARIOS3, ids=lambda s: s.name)
def test_ideas_channel_adds_well_under_one_percent(scenario) -> None:
    """Introduction: labor productivity rises through the ideas channel by well under one percent by 2030."""
    assert math.expm1(simulate(scenario)["dlnA"][-1]) < 0.01


def test_abstract() -> None:
    """The abstract's statements about the three scenarios."""
    modest, substantial, extreme = (readout(simulate(s)) for s in SCENARIOS3)
    assert (
        modest["gdp_growth"] - 100 * (CAL.g + CAL.n) < 0.5
    )  # "adds less than half a point to GDP growth"
    assert (
        round(modest["unemployment"] - 100 * CAL.U_bar, 1) == 0.1
    )  # "raises unemployment by a tenth of a point"
    assert (
        round(extreme["gdp_growth"]) == 15
    )  # "GDP growth then rises to 15 percent per year"
    assert (
        round(extreme["labor_share"]) == 45
    )  # "the labor share of income falls from 60 to 45 percent"
    assert (
        17.0 < extreme["unemployment_C"] < 20.0
    )  # "nearly one in five cognitive workers is unemployed"
    assert round(substantial["gdp"]) == 8
    assert round(substantial["employment_C"]) == -4
