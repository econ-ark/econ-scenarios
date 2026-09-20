"""A numpy reproduction of Korinek, Jones, Sacher, Cotter, and McCrory (2026), "Economic Scenarios
for Transformative AI", The Anthropic Institute Working Paper No. 2026-02.

This is an independent reimplementation from the paper's Tables A.1, A.2 and 1. It is not an
Anthropic product and carries no endorsement by the authors.
"""

from . import survey
from .calibration import (
    EXTREME,
    IPUMS_EU_HAZARDS,
    MODEST,
    SCENARIOS,
    SUBSTANTIAL,
    SWITCHING,
    Calibration,
    Scenario,
    monthly_growth,
    rate_from_fraction,
)
from .labor import (
    SteadyState,
    destination_shares,
    fit_mu_bar,
    hires,
    mu_from_switching_odds,
    pooled_switch_share,
    steady_state,
)
from .paths import AIState, ScenarioPaths
from .production import (
    Actual,
    Potential,
    actual_economy,
    capital_supply,
    closed_form,
    demand_given_wage,
    potential,
    rental_gap,
    shift_N,
    tfp_base_weight,
)
from .quiz import Answers, answers_to_scenario, preset_answers
from .report import readout
from .simulate import SERIES, Simulation, simulate

__all__ = [
    "EXTREME",
    "IPUMS_EU_HAZARDS",
    "MODEST",
    "SCENARIOS",
    "SERIES",
    "SUBSTANTIAL",
    "SWITCHING",
    "AIState",
    "Actual",
    "Answers",
    "Calibration",
    "Potential",
    "Scenario",
    "ScenarioPaths",
    "Simulation",
    "SteadyState",
    "actual_economy",
    "answers_to_scenario",
    "capital_supply",
    "closed_form",
    "demand_given_wage",
    "destination_shares",
    "fit_mu_bar",
    "hires",
    "monthly_growth",
    "mu_from_switching_odds",
    "pooled_switch_share",
    "potential",
    "preset_answers",
    "rate_from_fraction",
    "readout",
    "rental_gap",
    "shift_N",
    "simulate",
    "steady_state",
    "survey",
    "tfp_base_weight",
]
