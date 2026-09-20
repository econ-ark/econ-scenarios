"""Production block: Proposition 1 (Eqs. 14-18), its first-order rows (Eqs. 11, 19, 26, 44),
measured TFP (Eq. 45), and system (39) at given employment.

Every function here is pure: it takes the scenario objects at one date (``AIState``), the ideas
gap Delta ln A_t and a ``Calibration`` and returns log gaps against the no-AI path. Wages are
labor-augmenting, so they enter the price index deflated by A_t.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from .calibration import Calibration
    from .paths import AIState

# Bracket for the rental-rate gap Delta ln r: the rental rate between e^-4 and e^4 times r-bar.
# The lower end leaves room for the capital deepening of a long transition (a stock 2.5 log
# points above the no-AI path clears at about e^-2.3); the paper's runs stay within e^-1.
RENTAL_BRACKET = (-4.0, 4.0)
N_BISECT = 100


def bisect(
    f: Callable[[float], float],
    lo: float,
    hi: float,
    n_iter: int = N_BISECT,
) -> float:
    """Root of a function that changes sign once on [lo, hi], by ``n_iter`` halvings.

    ``f`` may return ``-inf`` where its argument leaves the economic domain (a labor share at or
    below zero); that side of the root is where capital demanded falls short of supply. A
    function with the same sign at both ends has no root in the bracket, and the market it
    stands for cannot clear there, so that raises instead of returning an end of the bracket.
    """
    f_lo = f(lo)
    if (f_lo > 0.0) == (f(hi) > 0.0):
        msg = f"no sign change on [{lo}, {hi}]: the capital market does not clear in the bracket"
        raise ArithmeticError(
            msg,
        )
    for _ in range(n_iter):
        mid = 0.5 * (lo + hi)
        f_mid = f(mid)
        if (f_mid > 0.0) == (f_lo > 0.0):
            lo, f_lo = mid, f_mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def displaced_mass(x: AIState, sigma: float) -> float:
    """M d [1 - rho psi - (1 - psi) e^{-(1-sigma) a}], the labor-task mass that leaves the cognitive group."""
    return (
        x.m
        * x.d
        * (1.0 - x.rho * x.psi - (1.0 - x.psi) * math.exp(-(1.0 - sigma) * x.a))
    )


def capital_mass(x: AIState, cal: Calibration) -> float:
    """B_t: capital instances at base prices, s_K + s_L psi m d (e^{-(1-sigma) a} - rho).

    The capital share is s_K,t = B_t e^{(1-sigma) Delta ln r_t} (Proposition 1, Eq. 14).
    """
    return cal.s_K + cal.s_L * x.psi * x.m * x.d * (
        math.exp(-(1.0 - cal.sigma) * x.a) - x.rho
    )


def surviving_cognitive_mass(x: AIState, cal: Calibration) -> float:
    """Lambda_C,t = s_C/s_L - m d [...], the surviving mass of cognitive instances (system 39)."""
    return cal.share_C - displaced_mass(x, cal.sigma)


@dataclass(frozen=True)
class Potential:
    """The full-employment economy of Section 2.1 at one date (Table A.1, panel B)."""

    dlnr: float
    lnSL: float
    lN: float
    lnW: float
    lnYL: float
    lnK: float
    lnTFP: float


def closed_form(x: AIState, dlnA: float, dlnr: float, cal: Calibration) -> Potential:
    """Proposition 1 at a given rental-rate gap: Eqs. (14)-(17) with the ideas stock (Appendix C.3)."""
    one_s = 1.0 - cal.sigma
    s_K_t = capital_mass(x, cal) * math.exp(one_s * dlnr)
    s_L_t = 1.0 - s_K_t
    if s_L_t <= 0.0:
        return Potential(
            dlnr,
            -math.inf,
            math.nan,
            math.nan,
            math.nan,
            -math.inf,
            math.nan,
        )
    lnSL = math.log(s_L_t / cal.s_L)
    lN = -math.log(1.0 - displaced_mass(x, cal.sigma))
    lnW = (lnSL + lN) / one_s + dlnA
    lnYL = lnW - lnSL
    lnK = math.log(s_K_t / cal.s_K) + lnYL - dlnr
    return Potential(dlnr, lnSL, lN, lnW, lnYL, lnK, math.nan)


def capital_supply(dlnr: float, assets: float, cal: Calibration) -> float:
    """Log gap of the capital supplied at rental gap ``dlnr``: the paper's schedule e^{eps dlnr}
    (Eq. 18) plus ``assets``, workers' extra assets over the no-AI capital stock, which is zero in
    the paper. At eps = inf the rental rate is pegged and the supply is whatever is demanded. Where
    negative extra assets exceed the schedule, at a rental rate far below the no-AI one, nothing
    is supplied and the log gap is minus infinity; the market clears at a higher rate.
    """
    level = math.exp(cal.eps * dlnr) + assets
    return math.log(level) if level > 0.0 else -math.inf


def rental_gap(x: AIState, dlnA: float, cal: Calibration, assets: float = 0.0) -> float:
    """The unique root of the capital market, capital supplied = Delta ln K (Eq. 18); zero at eps = inf."""
    if math.isinf(cal.eps):
        return 0.0
    return bisect(
        lambda r: closed_form(x, dlnA, r, cal).lnK - capital_supply(r, assets, cal),
        *RENTAL_BRACKET,
    )


def tfp_base_weight(x: AIState, dlnA: float, cal: Calibration) -> float:
    """Measured TFP gap, the CES price index over all tasks at base factor prices, Eq. (45)."""
    one_s = 1.0 - cal.sigma
    labor = 1.0 - x.m * x.d * (1.0 - math.exp(-one_s * x.a))
    return -math.log(cal.s_K + cal.s_L * labor * math.exp(-one_s * dlnA)) / one_s


def shift_N(x: AIState, cal: Calibration, form: str = "exact") -> float:
    """Shift of the all-other group's demand, l-tilde_N: Eq. (15) exact or Eq. (19) first order."""
    if form == "exact":
        return -math.log(1.0 - displaced_mass(x, cal.sigma))
    md = x.m * x.d
    return (1.0 - x.rho) * x.psi * md + (1.0 - cal.sigma) * (1.0 - x.psi) * md * x.a


def potential(
    x: AIState,
    dlnA: float,
    cal: Calibration,
    form: str = "exact",
    assets: float = 0.0,
) -> Potential:
    """Panel B of Table A.1: the exact rows (Proposition 1) or the first-order rows. ``assets``
    shifts the capital supply (``capital_supply``) and needs the exact rows.
    """
    if assets != 0.0 and form != "exact":
        msg = "workers' assets shift the capital supply only in the exact rows"
        raise ValueError(
            msg,
        )
    if form == "exact":
        dlnr = rental_gap(x, dlnA, cal, assets)
        cf = closed_form(x, dlnA, dlnr, cal)
        if cal.tfp_form == "dual":
            lnTFP = cal.s_L * cf.lnW + cal.s_K * dlnr
        else:
            lnTFP = tfp_base_weight(x, dlnA, cal)
        return Potential(cf.dlnr, cf.lnSL, cf.lN, cf.lnW, cf.lnYL, cf.lnK, lnTFP)
    if form != "first_order":
        msg = f"form must be 'exact' or 'first_order', got {form!r}"
        raise ValueError(msg)
    sigma, s_L, s_K = cal.sigma, cal.s_L, cal.s_K
    md = x.m * x.d
    mda = md * x.a
    if math.isinf(cal.eps):
        dlnr = 0.0
    else:
        dlnr = (
            mda + ((1.0 - x.rho) - (1.0 - sigma) * x.a) * x.psi * md / s_K + dlnA
        ) / (cal.eps + sigma / s_L)
    lnW = mda + dlnA - (s_K / s_L) * dlnr
    lnSL = (
        -(1.0 - x.rho) * x.psi * md
        + (1.0 - sigma) * x.psi * mda
        - (1.0 - sigma) * (s_K / s_L) * dlnr
    )
    lnYL = lnW - lnSL
    lnK = -(s_L / s_K) * lnSL + lnYL - dlnr
    lnTFP = s_L * (dlnA + mda)
    return Potential(dlnr, lnSL, shift_N(x, cal, "first_order"), lnW, lnYL, lnK, lnTFP)


@dataclass(frozen=True)
class Actual:
    """System (39) solved at given employment: the actual economy, or one of its two uses in Step 4."""

    lnW_C: float
    lnW_N: float
    dlnr: float
    lnY: float
    lnK: float
    lnSL: float
    ell_C: float


def _capital_root(objective: Callable[[float], float], cal: Calibration) -> float:
    if math.isinf(cal.eps):
        return 0.0
    return bisect(objective, *RENTAL_BRACKET)


def actual_economy(
    x: AIState,
    dlnA: float,
    ell: tuple[float, float],
    ell0: tuple[float, float],
    cal: Calibration,
    assets: float = 0.0,
) -> Actual:
    """System (39) at employment ``ell``: the price index, both groups' labor demands, the capital
    market, whose supply ``assets`` shifts (``capital_supply``).

    Each group is paid its marginal product. Output in efficiency units, y-hat = Delta ln Y -
    Delta ln A, and the deflated wages omega_o = Delta ln w_o - Delta ln A satisfy
    ln(l_C/l_C0) = ln(Lambda_C/(s_C/s_L)) + y-hat - sigma omega_C, ln(l_N/l_N0) = y-hat - sigma omega_N,
    and s_L Lambda_C e^{(1-sigma) omega_C} + s_N e^{(1-sigma) omega_N} = 1 - B_t e^{(1-sigma) Delta ln r}.
    """
    sigma = cal.sigma
    one_s = 1.0 - sigma
    lam_C = surviving_cognitive_mass(x, cal)
    B = capital_mass(x, cal)
    s_N = cal.s_L * (1.0 - cal.share_C)
    base_C = (math.log(lam_C / cal.share_C) - math.log(ell[0] / ell0[0])) / sigma
    base_N = -math.log(ell[1] / ell0[1]) / sigma
    weight = cal.s_L * lam_C * math.exp(one_s * base_C) + s_N * math.exp(one_s * base_N)

    def solve(dlnr: float) -> tuple[float, float, float]:
        s_L_t = 1.0 - B * math.exp(one_s * dlnr)
        if s_L_t <= 0.0:
            return -math.inf, math.nan, s_L_t
        y_hat = sigma / one_s * math.log(s_L_t / weight)
        lnY = y_hat + dlnA
        return math.log((1.0 - s_L_t) / cal.s_K) + lnY - dlnr, y_hat, s_L_t

    dlnr = _capital_root(lambda r: solve(r)[0] - capital_supply(r, assets, cal), cal)
    lnK, y_hat, s_L_t = solve(dlnr)
    return Actual(
        lnW_C=y_hat / sigma + base_C + dlnA,
        lnW_N=y_hat / sigma + base_N + dlnA,
        dlnr=dlnr,
        lnY=y_hat + dlnA,
        lnK=lnK,
        lnSL=math.log(s_L_t / cal.s_L),
        ell_C=ell[0],
    )


def demand_given_wage(
    x: AIState,
    dlnA: float,
    lnW_C: float,
    ell_N: float,
    ell0: tuple[float, float],
    cal: Calibration,
    assets: float = 0.0,
) -> Actual:
    """System (39) solved for cognitive employment at the cognitive wage ``lnW_C`` and all-other
    employment ``ell_N``, with the capital supply shifted by ``assets``.
    """
    sigma = cal.sigma
    one_s = 1.0 - sigma
    lam_C = surviving_cognitive_mass(x, cal)
    B = capital_mass(x, cal)
    s_N = cal.s_L * (1.0 - cal.share_C)
    omega_C = lnW_C - dlnA
    term_C = cal.s_L * lam_C * math.exp(one_s * omega_C)
    ln_rel_N = math.log(ell_N / ell0[1])

    def solve(dlnr: float) -> tuple[float, float, float, float]:
        s_L_t = 1.0 - B * math.exp(one_s * dlnr)
        rest = s_L_t - term_C
        if rest <= 0.0:
            return -math.inf, math.nan, math.nan, s_L_t
        omega_N = math.log(rest / s_N) / one_s
        y_hat = sigma * omega_N + ln_rel_N
        lnY = y_hat + dlnA
        return math.log((1.0 - s_L_t) / cal.s_K) + lnY - dlnr, omega_N, y_hat, s_L_t

    dlnr = _capital_root(lambda r: solve(r)[0] - capital_supply(r, assets, cal), cal)
    lnK, omega_N, y_hat, s_L_t = solve(dlnr)
    ell_C = ell0[0] * (lam_C / cal.share_C) * math.exp(y_hat - sigma * omega_C)
    return Actual(
        lnW_C=lnW_C,
        lnW_N=omega_N + dlnA,
        dlnr=dlnr,
        lnY=y_hat + dlnA,
        lnK=lnK,
        lnSL=math.log(s_L_t / cal.s_L),
        ell_C=ell_C,
    )
