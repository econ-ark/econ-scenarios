"""Calibration of Korinek, Jones, Sacher, Cotter and McCrory (2026), Table 1.

Table 1 of the paper prints rounded values (cognitive share 0.624, pool 3.8 percent, separation
relatives 0.69 and 1.52, responsive quit share 0.55). The simulations behind its tables use the
unrounded CPS and IPUMS values those entries round, so the defaults below are built from the
underlying counts and hazards. Every rounded entry of Table 1 is reproduced by them.

The alternative data sources offered by the authors' public scenario explorer (OEWS 2021
employment shares, two other IPUMS windows, equal separation rates by group) are available
through the ``shares``, ``hazards`` and ``separations`` fields.

Units: head counts are shares of the labor force; rates are per month unless named ``*_annual``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

# CPS 2025 annual averages, thousands (BLS Household Data tables 11 and 25, the sums of their SOC major
# group rows, checked 2026-09-10): cognitive occupations (SOC 11-29, 41, 43) and all others; unemployed
# by occupation of last job. BLS computes the 2025 averages over 11 months, since October was not collected.
CPS2025_EMPLOYED = (101942.0, 61551.0)
CPS2025_UNEMPLOYED = (3158.0, 3372.0)

# OEWS May 2021 employment summed to the same two groups, an alternative source of the shares.
OEWS2021_EMPLOYED = (78174350.0, 49172300.0)
EMPLOYMENT = {"CPS 2025": CPS2025_EMPLOYED, "OEWS 2021": OEWS2021_EMPLOYED}

# IPUMS-CPS monthly E-to-U hazards by group, unrounded (the paper quotes 0.84 and 1.84 percent for
# 2010-19). Taken from the calibration record of the authors' public explorer (2026-09-10), since
# recomputing them needs microdata.
IPUMS_EU_HAZARDS = {
    "2010-19": (0.008358559570558328, 0.01837914561784245),
    "2015-19 and 2022-24": (0.007109456015492585, 0.014811664367271786),
    "1994-2024": (0.00866689626181951, 0.019396558653508825),
}
IPUMS_EU_HAZARD = IPUMS_EU_HAZARDS["2010-19"]

# Unemployed job-finders who take a job in the other group, by origin (cognitive, other), from
# the coding-error corrected CPS destination matrix of Carrillo-Tudela and Visschers (2023),
# and the pooled share over both origins. Same source as the hazards.
SWITCHING = {
    "CPS 2010-19": {
        "switch_share": (0.1872637013795866, 0.11248052749549695),
        "pooled": 0.14288027376236828,
    },
    "CPS 1976-2021": {
        "switch_share": (0.19643260694302203, 0.10745739547084392),
        "pooled": 0.14024015531588008,
    },
}


def cognitive_share(shares: str = "CPS 2025") -> float:
    """Cognitive occupations' share of employment, s_C/s_L (Table 1: 0.624)."""
    e_c, e_n = EMPLOYMENT[shares]
    return e_c / (e_c + e_n)


def normal_pool() -> float:
    """Unemployed with a previous job as a share of the labor force, U-bar (Table 1: 0.038)."""
    employed = sum(CPS2025_EMPLOYED)
    unemployed = sum(CPS2025_UNEMPLOYED)
    return unemployed / (employed + unemployed)


def separation_relatives(
    share_C: float,
    hazards: str = "2010-19",
    separations: str = "by group",
) -> tuple[float, float]:
    """Each group's E-to-U hazard relative to the employment-weighted mean (Table 1: 0.69; 1.52).

    ``separations="common"`` gives both groups the economy-wide rate.
    """
    if separations == "common":
        return (1.0, 1.0)
    if separations != "by group":
        msg = f"separations must be 'by group' or 'common', got {separations!r}"
        raise ValueError(
            msg,
        )
    eu = IPUMS_EU_HAZARDS[hazards]
    mean = share_C * eu[0] + (1.0 - share_C) * eu[1]
    return (eu[0] / mean, eu[1] / mean)


@dataclass(frozen=True)
class Calibration:
    """Parameters common to the scenarios (Table 1, panels A, B and D; Table A.2).

    ``eps`` and ``xi`` are common to the three scenarios in Table 1 and varied in Tables 5 and 6;
    ``eps = math.inf`` pegs the rental rate at r-bar. ``share_C`` and ``sep_rel`` are the values
    the data sources named by ``shares``, ``hazards`` and ``separations`` imply, unless set
    through ``share_C_override`` and ``sep_rel_override``.
    ``tfp_form="dual"`` reports measured TFP as s_L Delta ln w + s_K Delta ln r in place of the
    base-price index of Eq. (45).
    ``quit_order`` places Appendix A's conversion q = -ln(1 - q-hat) in Eq. (27). The default,
    "split_then_convert", applies Eq. (27) to the monthly fractions and converts the sum each
    month, as the explorer does; "convert_then_split" converts each group's normal fraction once
    and applies Eq. (27) linearly in the rate. The two agree whenever f_o,t-1 = f-bar_o.
    """

    sigma: float = 0.5
    s_L: float = 0.6
    shares: str = "CPS 2025"
    hazards: str = "2010-19"
    separations: str = "by group"
    share_C_override: float | None = None
    sep_rel_override: tuple[float, float] | None = None
    eps: float = 3.0
    r_bar: float = 0.115
    delta: float = 0.05
    t0: float = 2024.0
    t_anchor: float = 2026.5
    t_read: float = 2030.0
    months_per_year: int = 12
    lam: float = 1.0
    one_minus_phi: float = 3.1
    g_A: float = 0.01
    n: float = 0.0033
    iota_R: float = 0.035
    iota: float = 1.27
    pi_bar_mean: float = 0.65
    q_bar_annual: float = 0.11
    q_T_share: float = 0.06 / 0.11
    quit_order: str = "split_then_convert"
    U_bar: float = field(default_factory=normal_pool)
    mu_bar: float = 0.17
    xi: float = 0.5
    m_anchor: float = 0.14
    d_anchor: float = 0.10
    m_ceiling: float | None = None
    d_ceiling: float = 1.0
    tfp_form: str = "base_weight"

    def __post_init__(self) -> None:
        if self.tfp_form not in ("base_weight", "dual"):
            msg = f"tfp_form must be 'base_weight' or 'dual', got {self.tfp_form!r}"
            raise ValueError(
                msg,
            )
        if self.quit_order not in ("split_then_convert", "convert_then_split"):
            msg = f"quit_order must be 'split_then_convert' or 'convert_then_split', got {self.quit_order!r}"
            raise ValueError(
                msg,
            )

    @property
    def share_C(self) -> float:
        """Cognitive share of employment, s_C/s_L: from ``shares`` unless overridden."""
        return (
            cognitive_share(self.shares)
            if self.share_C_override is None
            else self.share_C_override
        )

    @property
    def sep_rel(self) -> tuple[float, float]:
        """Separation relatives by group: from ``hazards`` and ``separations`` unless overridden."""
        if self.sep_rel_override is not None:
            return self.sep_rel_override
        return separation_relatives(self.share_C, self.hazards, self.separations)

    @property
    def h(self) -> float:
        """Period length in years."""
        return 1.0 / self.months_per_year

    @property
    def s_K(self) -> float:
        """Base-period capital share."""
        return 1.0 - self.s_L

    @property
    def m_bar(self) -> float:
        """Ceiling of the affected mass: all cognitive work unless set explicitly."""
        return self.share_C if self.m_ceiling is None else self.m_ceiling

    @property
    def g(self) -> float:
        """No-AI growth of the labor-augmenting ideas stock, g = g_A / s_L."""
        return self.g_A / self.s_L

    @property
    def one_minus_phi_R(self) -> float:
        """Fishing out in labor-augmenting units with research input in goods, Eq. (40)."""
        return self.s_L * self.one_minus_phi + self.lam

    @property
    def quit_fractions(self) -> tuple[tuple[float, float], tuple[float, float]]:
        """Monthly quit fractions (q^X_o, q^T_o) by group, before conversion to rates.

        The economy-wide 0.11 a year is split by the groups' separation relatives and into the
        part that responds to the finding rate (q^T) and the part that does not (q^X).
        """
        monthly = self.q_bar_annual / self.months_per_year
        rel_c, rel_n = self.sep_rel
        q_x = (
            (1.0 - self.q_T_share) * monthly * rel_c,
            (1.0 - self.q_T_share) * monthly * rel_n,
        )
        q_t = (self.q_T_share * monthly * rel_c, self.q_T_share * monthly * rel_n)
        return q_x, q_t


def rate_from_fraction(fraction: float) -> float:
    """Continuously compounded rate of a per-period fraction, q = -ln(1 - q-hat) (Appendix A)."""
    return -math.log1p(-fraction)


def monthly_growth(cal: Calibration) -> float:
    """Gross monthly growth of the no-AI wage, exp(g / 12).

    It lives here, beside the ``g`` it reads, rather than with the households that mostly call it:
    it is a function of the calibration alone, and putting it here is what lets a paper's tests
    ask for the growth rate without importing a household.
    """
    return math.exp(cal.g / 12)


@dataclass(frozen=True)
class Scenario:
    """One AI scenario (Table 1, panels B and C).

    ``a_anchor`` is the gain at the mid-2026 anchor and ``g_a`` its linear slope per year. The
    automation share is a logistic path from ``psi`` at the anchor toward ``psi_ceiling`` at slope
    ``psi_kappa`` (Table A.2); the scenarios hold it constant, ``psi_ceiling = psi``.

    Two options reproduce guards of the public explorer that the paper does not have, both
    inactive by default: ``a_ceiling`` caps the gain (the explorer uses ln 30), and ``kappa_max``
    clamps the logistic slopes of Eq. (8') to [0, kappa_max], also covering a 2030 value at or
    beyond the ceiling (the explorer uses 3).
    """

    name: str
    m_2030: float
    d_2030: float
    a_anchor: float
    g_a: float
    psi: float
    rho: float
    mu: float
    theta_H: float
    psi_ceiling: float | None = None
    psi_floor: float = 0.0
    psi_kappa: float = 0.0
    a_ceiling: float | None = None
    kappa_max: float | None = None


MODEST = Scenario(
    "modest",
    m_2030=0.2,
    d_2030=0.2,
    a_anchor=0.30,
    g_a=0.0,
    psi=0.50,
    rho=0.50,
    mu=0.17,
    theta_H=0.10,
)
SUBSTANTIAL = Scenario(
    "substantial",
    m_2030=0.3,
    d_2030=0.4,
    a_anchor=0.35,
    g_a=0.028,
    psi=0.75,
    rho=0.25,
    mu=0.08,
    theta_H=0.25,
)
EXTREME = Scenario(
    "extreme",
    m_2030=0.5,
    d_2030=0.6,
    a_anchor=0.45,
    g_a=0.10,
    psi=0.90,
    rho=0.0,
    mu=0.04,
    theta_H=0.50,
)
SCENARIOS = {s.name: s for s in (MODEST, SUBSTANTIAL, EXTREME)}
