"""The monthly recursion of Appendix A (steps 1-9) over the 44 equations of Table A.1.

``simulate`` returns a ``Simulation``: one row per month from t0 = 2024.0 through ``horizon``,
each row holding the stocks at the start of the month, the flows during it, and the potential and
actual economies at that date. Log gaps are against the no-AI path; head counts are shares of
the labor force; rates are per month.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from .calibration import Calibration, Scenario, rate_from_fraction
from .labor import SteadyState, hires, steady_state
from .paths import AIState, ScenarioPaths
from .production import actual_economy, demand_given_wage, potential, shift_N

if TYPE_CHECKING:
    from collections.abc import Callable

# name: (meaning, unit). Every series has one value per month.
SERIES: dict[str, tuple[str, str]] = {
    "month": ("month index k from t0 = 2024.0", "months"),
    "t": ("date, t0 + k/12", "year"),
    "m": ("affected mass m_t", "fraction"),
    "d": ("diffusion share d_t", "fraction"),
    "a": ("log gain per AI-performed instance a_t", "log points"),
    "psi": ("automation share psi_t", "fraction"),
    "dlnA": ("ideas stock gap Delta ln A_t (predetermined)", "log gap"),
    "dg": ("growth-rate gap of the ideas stock Delta g_t, Eq. (42)", "per year"),
    "pot_dlnr": ("potential rental-rate gap, Eq. (18)", "log gap"),
    "pot_lnW": ("potential common wage, Proposition 1", "log gap"),
    "pot_lnSL": ("potential labor share, Eq. (14)", "log gap"),
    "pot_lnYL": ("potential output per worker, Eq. (5)", "log gap"),
    "pot_lnK": ("potential capital stock, Eq. (17)", "log gap"),
    "lnTFP": ("measured TFP, Eq. (45)", "log gap"),
    "shift_N": ("shift of the all-other group's demand l-tilde_N, Eq. (15)", "log"),
    "target_C": ("target cognitive employment l*_C,t, Eq. (13)", "share of L"),
    "target_N": ("target all-other employment l*_N,t, Eq. (13)", "share of L"),
    "target_C_next": ("target l*_C,t+1", "share of L"),
    "target_N_next": ("target l*_N,t+1", "share of L"),
    "ell_C": ("cognitive employment l_C,t (start of month)", "share of L"),
    "ell_N": ("all-other employment l_N,t (start of month)", "share of L"),
    "U_C": ("pool of cognitive origin U_C,t (start of month)", "share of L"),
    "U_N": ("pool of all-other origin U_N,t (start of month)", "share of L"),
    "overhang_C": ("cognitive overhang G_C,t, Eq. (28)", "log gap"),
    "overhang_N": (
        "all-other overhang G_N,t, Eq. (28); zero on the scenario paths",
        "log gap",
    ),
    "shortfall_N": ("all-other shortfall B_N,t, Eq. (28)", "log gap"),
    "q_C": (
        "cognitive quit rate q_C,t applied in Eqs. (36)-(37), = -ln(1 - q-hat), Eq. (27)",
        "per month",
    ),
    "q_N": (
        "all-other quit rate q_N,t applied in Eqs. (36)-(37), = -ln(1 - q-hat), Eq. (27)",
        "per month",
    ),
    "N_C": ("attached cognitive force N_C,t, Eq. (29)", "share of L"),
    "lnW_C_clear": ("wage clearing N_C,t, w^c_C,t by system (39)", "log gap"),
    "wage_gap": ("sticky cognitive discount ln(w_C,t / w_t), Eq. (30)", "log"),
    "lnW_C": ("cognitive wage paid w_C,t, Eq. (30)", "log gap"),
    "ell_C_demand": (
        "cognitive labor demand at w_C,t, l^d_C,t by system (39)",
        "share of L",
    ),
    "excess_C": ("excess cognitive employment E_t", "share of L"),
    "demand_gap_C": ("cognitive demand beyond employment Z_t", "share of L"),
    "D_C": ("cognitive layoffs D_C,t, Eq. (31)", "share of L per month"),
    "v_C": ("cognitive openings v_C,t, Eq. (32)", "share of L per month"),
    "v_N": ("all-other openings v_N,t, Eq. (32)", "share of L per month"),
    "S_C": ("effective search directed at C, Eq. (33)", "share of L"),
    "S_N": ("effective search directed at N, Eq. (33)", "share of L"),
    "H_C": ("hires into C, Eq. (34)", "share of L per month"),
    "H_N": ("hires into N, Eq. (34)", "share of L per month"),
    "f_C": ("finding rate of cognitive origin, Eq. (35)", "fraction per month"),
    "f_N": ("finding rate of all-other origin, Eq. (35)", "fraction per month"),
    "lnY": ("actual GDP, system (39) at realized employment", "log gap"),
    "lnW_N": ("all-other wage w_N,t, actual economy", "log gap"),
    "lnMPL_C": ("cognitive marginal product at realized employment", "log gap"),
    "lnW_avg": ("average wage of the employed", "log gap"),
    "dlnr": ("actual rental-rate gap", "log gap"),
    "lnK": ("actual capital stock", "log gap"),
    "lnSL": ("actual labor share", "log gap"),
    "net_return": ("net return to capital r_t - delta", "per year"),
    "U_total": ("total pool U_C + U_N", "share of L"),
    "u_excess": ("pool above its normal level, u^x_t", "share of L"),
    "reallocation": ("reallocation flow X_t", "share of L per month"),
    "overhang_agg": ("aggregate overhang G_t = sum of G_o,t l_o,t", "share of L"),
    "worker_assets": (
        "workers' extra assets added to the capital supply, over the no-AI capital stock",
        "ratio",
    ),
}


def _per_searcher(hires: np.ndarray, searchers: np.ndarray) -> np.ndarray:
    """Hires per searcher, zero in the months where nobody searches. The denominator is replaced
    before the divide rather than after, which keeps a month with no searchers quiet and finite.
    """
    return np.where(
        searchers > 0,
        hires / np.where(searchers > 0, searchers, 1.0),
        0.0,
    )


@dataclass
class Simulation:
    """Monthly paths of one run, with the calibration, scenario, and steady state that produced them."""

    calibration: Calibration
    scenario: Scenario
    steady: SteadyState
    level_form: str
    series: dict[str, np.ndarray] = field(default_factory=dict)

    def __getitem__(self, name: str) -> np.ndarray:
        return self.series[name]

    @property
    def t(self) -> np.ndarray:
        return self.series["t"]

    def index(self, t: float) -> int:
        """Row of date ``t``, which must lie on the monthly grid."""
        k = round((t - self.calibration.t0) * self.calibration.months_per_year)
        if not (0 <= k < len(self.t)) or abs(self.t[k] - t) > 1e-9:
            msg = f"t = {t} is not a simulated month"
            raise KeyError(msg)
        return k

    def markov_matrices(self) -> np.ndarray:
        """Monthly transition matrices over (E_C, E_N, U_C, U_N), rows summing to one.

        ``M[k]`` maps the shares at month k into month k + 1 exactly as Eqs. (36)-(37) do:
        p_{k+1} = p_k M[k], with the quit rate q_o,t applied as a monthly fraction.
        """
        s = self.series
        mu = self.scenario.mu
        n = len(self.t)
        M = np.zeros((n, 4, 4))
        per_C = _per_searcher(s["H_C"], s["S_C"])
        per_N = _per_searcher(s["H_N"], s["S_N"])
        layoff = np.where(s["ell_C"] > 0, s["D_C"] / s["ell_C"], 0.0)
        M[:, 0, 2] = s["q_C"] + layoff
        M[:, 0, 0] = 1.0 - M[:, 0, 2]
        M[:, 1, 3] = s["q_N"]
        M[:, 1, 1] = 1.0 - s["q_N"]
        M[:, 2, 0] = per_C
        M[:, 2, 1] = mu * per_N
        M[:, 2, 2] = 1.0 - per_C - mu * per_N
        M[:, 3, 0] = mu * per_C
        M[:, 3, 1] = per_N
        M[:, 3, 3] = 1.0 - mu * per_C - per_N
        return M

    def write_csv(self, path: str | Path) -> None:
        """Write every series, one row per month, with a two-line header of meanings and units."""
        names = list(self.series)
        with Path(path).open("w", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(names)
            writer.writerow([f"{SERIES[k][0]} [{SERIES[k][1]}]" for k in names])
            for row in zip(*(self.series[k] for k in names), strict=False):
                writer.writerow([repr(float(v)) for v in row])


def _targets(
    x: AIState,
    ell0: tuple[float, float],
    cal: Calibration,
    form: str,
) -> tuple[float, float, float]:
    """The two employment targets by Eq. (13), and the shift l-tilde_N behind them."""
    shift = shift_N(x, cal, form)
    target_N = ell0[1] * math.exp(shift)
    return ell0[0] + ell0[1] - target_N, target_N, shift


def simulate(
    scenario: Scenario,
    cal: Calibration | None = None,
    horizon: float = 2030.0,
    level_form: str = "exact",
    worker_assets: np.ndarray
    | Callable[[int, dict[str, list[float]], Callable[[float], float]], float]
    | None = None,
    freeze_after: float | None = None,
) -> Simulation:
    """Run the monthly system of Table A.1 from t0 through ``horizon``.

    ``level_form="first_order"`` uses the first-order rows of panel B for the reported potential
    economy and the employment targets. The sticky-wage block and the actual economy read the
    exact rows either way, as system (39) is written in exact form.

    ``worker_assets``, one value per month, adds workers' extra assets (over the no-AI capital
    stock) to the capital supplied in every capital market of that month, potential and actual
    alike; the paper's households hold none, so the default is zero everywhere. It may instead be
    a function of the month index, of the series computed so far (lists, one entry per month
    already run), and of the month's own clearing, a function from the assets supplied to the
    net return they would clear at, for a supply that depends on the run's own past or on the
    month's own price, such as an owner of capital who saves out of last month's return or one
    whose stock adjusts within the month.

    ``freeze_after`` holds the technology at its value on that date: the scenario objects stop
    moving and the ideas gap stops growing, so that in the months after it only the stocks of
    workers and whatever capital is supplied still move. The paper's runs end in 2030 and use
    no freeze.
    """
    cal = Calibration() if cal is None else cal
    ss = steady_state(cal)
    paths = ScenarioPaths(scenario, cal)
    h = cal.h
    n_months = round((horizon - cal.t0) * cal.months_per_year)
    supply = worker_assets if callable(worker_assets) else None
    supplied = (
        np.zeros(n_months + 1)
        if worker_assets is None or supply is not None
        else np.asarray(worker_assets, dtype=float)
    )
    if len(supplied) != n_months + 1:
        msg = f"worker_assets needs one value per month, {n_months + 1}, got {len(supplied)}"
        raise ValueError(
            msg,
        )
    if level_form != "exact" and (supply is not None or np.any(supplied != 0.0)):
        msg = "worker_assets shift the capital supply only in the exact rows"
        raise ValueError(
            msg,
        )
    frozen_at = math.inf if freeze_after is None else freeze_after
    q_x, q_t = cal.quit_fractions
    xi_m = cal.xi**h
    mu = scenario.mu
    theta = scenario.theta_H
    one_minus_phi_R = cal.one_minus_phi_R

    ell = list(ss.ell0)
    U = list(ss.U)
    f_prev = list(ss.f)
    wage_gap = 0.0
    dlnA = 0.0
    out: dict[str, list[float]] = {k: [] for k in SERIES}

    for k in range(n_months + 1):
        # Step 1: paths at t and t + 1; the ideas gap is predetermined.
        t = cal.t0 + k * h
        x = paths.at(min(t, frozen_at))
        x_next = paths.at(min(cal.t0 + (k + 1) * h, frozen_at))
        # Steps 2-3: capital market, wage, shares and targets.
        if supply is not None:
            # The month's net return at any supplied assets: the actual economy at this month's
            # employment, which step 8 below reads at the assets finally supplied.
            def rental(a: float, x=x, dlnA=dlnA, ell_now=(ell[0], ell[1])) -> float:
                return (
                    cal.r_bar
                    * math.exp(actual_economy(x, dlnA, ell_now, ss.ell0, cal, a).dlnr)
                    - cal.delta
                )

            assets = float(supply(k, out, rental))
        else:
            assets = float(supplied[k])
        pot = potential(x, dlnA, cal, level_form, assets)
        pot_exact = (
            pot if level_form == "exact" else potential(x, dlnA, cal, "exact", assets)
        )
        target_C, target_N, shift = _targets(x, ss.ell0, cal, level_form)
        target_C_next, target_N_next, _ = _targets(x_next, ss.ell0, cal, level_form)
        # Step 4: gaps, the clearing and the sticky cognitive wage, cognitive demand.
        overhang_C = max(0.0, math.log(ell[0]) - math.log(target_C_next))
        overhang_N = max(0.0, math.log(ell[1]) - math.log(target_N_next))
        shortfall_N = max(0.0, math.log(target_N_next) - math.log(ell[1]))
        N_C = ell[0] + max(0.0, U[0] - ss.U[0])
        clear = actual_economy(x, dlnA, (N_C, ell[1]), ss.ell0, cal, assets)
        wage_gap = xi_m * wage_gap + (1.0 - xi_m) * (clear.lnW_C - pot_exact.lnW)
        lnW_C = pot_exact.lnW + wage_gap
        demand = demand_given_wage(x, dlnA, lnW_C, ell[1], ss.ell0, cal, assets)
        if not demand.ell_C >= 0.0:
            msg = f"cognitive demand is infeasible at t = {t}"
            raise ArithmeticError(msg)
        excess = max(0.0, ell[0] - demand.ell_C)
        demand_gap = max(0.0, demand.ell_C - ell[0])
        # Step 5: separations and openings.
        if cal.quit_order == "split_then_convert":
            q = [
                rate_from_fraction(q_x[o] + q_t[o] * f_prev[o] / ss.f[o])
                for o in (0, 1)
            ]
        else:
            q = [
                (1.0 - cal.q_T_share) * ss.q[o]
                + cal.q_T_share * ss.q[o] * f_prev[o] / ss.f[o]
                for o in (0, 1)
            ]
        D_C = max(0.0, excess - q[0] * ell[0])
        v_C = (max(0.0, q[0] * ell[0] - excess) + theta * demand_gap) / ss.pi_bar[0]
        v_N = (q[1] + theta * shortfall_N) * ell[1] / ss.pi_bar[1]
        # Step 6: matching.
        S_C = U[0] + mu * U[1]
        S_N = mu * U[0] + U[1]
        H_C = hires(ss.chi, S_C, v_C, cal.iota)
        H_N = hires(ss.chi, S_N, v_N, cal.iota)
        per_C = H_C / S_C if S_C > 0.0 else 0.0
        per_N = H_N / S_N if S_N > 0.0 else 0.0
        f = [per_C + mu * per_N, mu * per_C + per_N]
        # Step 8: the actual economy at realized employment.
        act = actual_economy(x, dlnA, (ell[0], ell[1]), ss.ell0, cal, assets)
        lnW_avg = math.log(
            (math.exp(lnW_C) * ell[0] + math.exp(act.lnW_N) * ell[1])
            / (ell[0] + ell[1]),
        )
        # Step 9: ideas, Eq. (42), from the actual economy's GDP gap (Eq. 22); frozen with the technology.
        dg = (
            0.0
            if t >= frozen_at
            else cal.g * (math.exp(cal.lam * act.lnY - one_minus_phi_R * dlnA) - 1.0)
        )
        # Step 7: stocks, Eqs. (36)-(37).
        ell_next = [(1.0 - q[0]) * ell[0] - D_C + H_C, (1.0 - q[1]) * ell[1] + H_N]
        U_next = [
            U[0] + q[0] * ell[0] + D_C - f[0] * U[0],
            U[1] + q[1] * ell[1] - f[1] * U[1],
        ]
        if min(ell_next + U_next) < 0.0:
            msg = f"a stock turns negative after t = {t}"
            raise ArithmeticError(msg)

        row = {
            "month": k,
            "t": t,
            "m": x.m,
            "d": x.d,
            "a": x.a,
            "psi": x.psi,
            "dlnA": dlnA,
            "dg": dg,
            "pot_dlnr": pot.dlnr,
            "pot_lnW": pot.lnW,
            "pot_lnSL": pot.lnSL,
            "pot_lnYL": pot.lnYL,
            "pot_lnK": pot.lnK,
            "lnTFP": pot.lnTFP,
            "shift_N": shift,
            "target_C": target_C,
            "target_N": target_N,
            "target_C_next": target_C_next,
            "target_N_next": target_N_next,
            "ell_C": ell[0],
            "ell_N": ell[1],
            "U_C": U[0],
            "U_N": U[1],
            "overhang_C": overhang_C,
            "overhang_N": overhang_N,
            "shortfall_N": shortfall_N,
            "q_C": q[0],
            "q_N": q[1],
            "N_C": N_C,
            "lnW_C_clear": clear.lnW_C,
            "wage_gap": wage_gap,
            "lnW_C": lnW_C,
            "ell_C_demand": demand.ell_C,
            "excess_C": excess,
            "demand_gap_C": demand_gap,
            "D_C": D_C,
            "v_C": v_C,
            "v_N": v_N,
            "S_C": S_C,
            "S_N": S_N,
            "H_C": H_C,
            "H_N": H_N,
            "f_C": f[0],
            "f_N": f[1],
            "lnY": act.lnY,
            "lnW_N": act.lnW_N,
            "lnMPL_C": act.lnW_C,
            "lnW_avg": lnW_avg,
            "dlnr": act.dlnr,
            "lnK": act.lnK,
            "lnSL": act.lnSL,
            "net_return": cal.r_bar * math.exp(act.dlnr) - cal.delta,
            "U_total": U[0] + U[1],
            "u_excess": U[0] + U[1] - cal.U_bar,
            "reallocation": 0.5
            * (abs(ell_next[0] - ell[0]) + abs(ell_next[1] - ell[1])),
            "overhang_agg": overhang_C * ell[0] + overhang_N * ell[1],
            "worker_assets": assets,
        }
        for key, value in row.items():
            out[key].append(value)

        ell, U, f_prev = ell_next, U_next, f
        dlnA += h * dg

    return Simulation(
        calibration=cal,
        scenario=scenario,
        steady=ss,
        level_form=level_form,
        series={key: np.asarray(values) for key, values in out.items()},
    )
