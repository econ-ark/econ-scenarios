"""Runs compared with the explorer oracle: the calibration and points away from it."""

import math
from dataclasses import replace
from typing import NamedTuple

from econ_scenarios import (
    EXTREME,
    MODEST,
    SUBSTANTIAL,
    Answers,
    Calibration,
    Scenario,
    preset_answers,
)

CAL = Calibration()
OFF_A = Scenario(
    "off_a",
    m_2030=0.42,
    d_2030=0.55,
    a_anchor=0.40,
    g_a=0.07,
    psi=0.62,
    rho=0.10,
    mu=0.11,
    theta_H=0.37,
)
OFF_B = Scenario(
    "off_b",
    m_2030=0.35,
    d_2030=0.3,
    a_anchor=0.5,
    g_a=0.05,
    psi=0.5,
    rho=0.3,
    mu=0.25,
    theta_H=0.15,
    psi_ceiling=0.85,
    psi_kappa=0.6,
)


class Case(NamedTuple):
    """One run compared with the explorer, with the label the figures print for it."""

    scenario: Scenario
    cal: Calibration
    horizon: float
    form: str
    label: str


ORACLE_CASES = {
    "modest": Case(MODEST, CAL, 2030.0, "exact", "modest"),
    "substantial": Case(SUBSTANTIAL, CAL, 2030.0, "exact", "substantial"),
    "extreme": Case(EXTREME, CAL, 2030.0, "exact", "extreme"),
    "modest-first-order": Case(
        MODEST,
        CAL,
        2030.0,
        "first_order",
        "modest, first-order mode",
    ),
    "extreme-first-order": Case(
        EXTREME,
        CAL,
        2030.0,
        "first_order",
        "extreme, first-order mode",
    ),
    "extreme-eps1": Case(
        EXTREME,
        replace(CAL, eps=1.0),
        2030.0,
        "exact",
        "extreme, capital elasticity 1",
    ),
    "extreme-eps-inf": Case(
        EXTREME,
        replace(CAL, eps=math.inf),
        2030.0,
        "exact",
        "extreme, pegged rental rate",
    ),
    "extreme-xi0": Case(
        EXTREME,
        replace(CAL, xi=0.0),
        2030.0,
        "exact",
        "extreme, flexible wage",
    ),
    "substantial-xi0.9": Case(
        SUBSTANTIAL,
        replace(CAL, xi=0.9),
        2030.0,
        "exact",
        "substantial, wage rigidity 0.9",
    ),
    "off-a": Case(
        OFF_A,
        replace(
            CAL,
            eps=1.7,
            xi=0.3,
            sigma=0.35,
            mu_bar=0.21,
            U_bar=0.045,
            q_bar_annual=0.13,
            pi_bar_mean=0.6,
        ),
        2032.0,
        "exact",
        "off calibration A, to 2032",
    ),
    "off-b": Case(
        OFF_B,
        replace(CAL, eps=math.inf, xi=0.8, sigma=0.7),
        2035.0,
        "exact",
        "off calibration B, to 2035",
    ),
}

# Answers a visitor can give to the explorer's quiz, run to 2035 as the page runs them.
QUIZ = {
    "middling": Answers(capability=0.7, adoption=0.5, alone=0.6, gain=3.0, months=8.0),
    "all at the ceilings": Answers(
        capability=1.0,
        adoption=1.0,
        alone=0.99,
        gain=10.0,
        months=700.0,
    ),
    "all at the floors": Answers(
        capability=0.0,
        adoption=0.0,
        alone=0.0,
        gain=1.0,
        months=0.5,
    ),
    "survey medians": Answers(
        capability=0.44 / 0.6235,
        adoption=0.40,
        alone=0.47,
        gain=1.55,
        months=8.0,
    ),
    **{f"{s.name} preset": preset_answers(s) for s in (MODEST, SUBSTANTIAL, EXTREME)},
}

# The explorer's alternative data sources and reporting options.
DATA_OPTIONS = {
    "OEWS 2021 shares": Calibration(shares="OEWS 2021"),
    "hazards 2015-19 and 2022-24": Calibration(hazards="2015-19 and 2022-24"),
    "hazards 1994-2024": Calibration(hazards="1994-2024"),
    "common separation rates": Calibration(separations="common"),
    "dual TFP": Calibration(tfp_form="dual"),
}

# Machine precision for series of order one after 72-132 monthly steps and ~500 bisections.
PATH_TOLERANCE = 1e-12
