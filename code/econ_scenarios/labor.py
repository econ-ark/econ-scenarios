"""Labor-market block (Section 2.3): the matching function (Eq. 34) and the steady state (Eq. 38)."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

from .calibration import Calibration, rate_from_fraction
from .production import bisect

N_BISECT_STEADY = 200
N_BISECT_MU = 80


def hires(chi: float, search: float, openings: float, iota: float) -> float:
    """Den Haan-Ramey-Watson hires, chi S v / (S^iota + v^iota)^{1/iota} (Eq. 34)."""
    lo, hi = min(search, openings), max(search, openings)
    if lo <= 0.0:
        return 0.0
    return chi * lo / (1.0 + (lo / hi) ** iota) ** (1.0 / iota)


def filling_rate_at_rest(chi: float, hires_per_search: float, iota: float) -> float:
    """Normal filling rate pi-bar = chi [1 - (H/(chi S))^iota]^{1/iota}, the matching function inverted (Eq. 38)."""
    return chi * (1.0 - (hires_per_search / chi) ** iota) ** (1.0 / iota)


@dataclass(frozen=True)
class SteadyState:
    """Table A.1, panel E: the normal-times flow block, solved once at t0 at the normal-times discount mu-bar.

    ``q`` are the continuously compounded normal quit rates that Eqs. (36)-(37) apply per month.
    """

    ell0: tuple[float, float]
    U: tuple[float, float]
    q: tuple[float, float]
    H: tuple[float, float]
    S: tuple[float, float]
    f: tuple[float, float]
    pi_bar: tuple[float, float]
    chi: float
    chi_capped: bool

    @property
    def f_aggregate(self) -> float:
        """Aggregate finding rate of the pool, (H_C + H_N) / U-bar."""
        return (self.H[0] + self.H[1]) / (self.U[0] + self.U[1])


def _search(U: tuple[float, float], mu: float) -> tuple[float, float]:
    """Effective search directed at each group, Eq. (33)."""
    return U[0] + mu * U[1], mu * U[0] + U[1]


def _finding(
    H: tuple[float, float],
    S: tuple[float, float],
    mu: float,
) -> tuple[float, float]:
    """Finding rates by origin, Eq. (35)."""
    per_C = H[0] / S[0] if S[0] > 0.0 else 0.0
    per_N = H[1] / S[1] if S[1] > 0.0 else 0.0
    return per_C + mu * per_N, mu * per_C + per_N


def steady_state(cal: Calibration) -> SteadyState:
    """Solve Eq. (38): hires replace quits group by group, each origin's inflow equals its outflow,
    and chi sets the employment-weighted mean normal filling rate to ``pi_bar_mean``.
    """
    if not cal.mu_bar > 0.0:
        msg = "the steady-state pool split needs mu_bar > 0"
        raise ValueError(msg)
    w = (cal.share_C, 1.0 - cal.share_C)
    ell0 = (w[0] * (1.0 - cal.U_bar), w[1] * (1.0 - cal.U_bar))
    q_x, q_t = cal.quit_fractions
    q = (rate_from_fraction(q_x[0] + q_t[0]), rate_from_fraction(q_x[1] + q_t[1]))
    H = (q[0] * ell0[0], q[1] * ell0[1])

    def excess_outflow(share: float) -> float:
        pools = (share * cal.U_bar, (1.0 - share) * cal.U_bar)
        f = _finding(H, _search(pools, cal.mu_bar), cal.mu_bar)
        return f[0] * pools[0] - H[0]

    share_C = bisect(excess_outflow, 0.0, 1.0, N_BISECT_STEADY)
    U = (share_C * cal.U_bar, cal.U_bar - share_C * cal.U_bar)
    S = _search(U, cal.mu_bar)
    f = _finding(H, S, cal.mu_bar)
    per_search = (H[0] / S[0], H[1] / S[1])

    def mean_filling(chi: float) -> float:
        return sum(
            w_o * filling_rate_at_rest(chi, x_o, cal.iota)
            for w_o, x_o in zip(w, per_search, strict=False)
        )

    lo = max(per_search)
    hi = max(1.0, 2.0 * lo)
    while mean_filling(hi) < cal.pi_bar_mean:
        hi *= 2.0
    chi = bisect(lambda c: mean_filling(c) - cal.pi_bar_mean, lo, hi, N_BISECT_STEADY)
    chi_capped = chi > 1.0
    if chi_capped:
        chi = 1.0
    pi_bar = (
        filling_rate_at_rest(chi, per_search[0], cal.iota),
        filling_rate_at_rest(chi, per_search[1], cal.iota),
    )
    return SteadyState(
        ell0=ell0,
        U=U,
        q=q,
        H=H,
        S=S,
        f=f,
        pi_bar=pi_bar,
        chi=chi,
        chi_capped=chi_capped,
    )


def destination_shares(
    ss: SteadyState,
    mu: float,
) -> tuple[tuple[float, float], tuple[float, float]]:
    """Share of each origin's job-finders hired into each group, mu_oj (H_j / S_j) / f_o (Eq. 35)."""
    per = (ss.H[0] / ss.S[0], ss.H[1] / ss.S[1])
    weights = ((1.0, mu), (mu, 1.0))
    return tuple(
        tuple(weights[o][j] * per[j] / ss.f[o] for j in (0, 1)) for o in (0, 1)
    )  # type: ignore[return-value]


def pooled_switch_share(cal: Calibration) -> float:
    """Share of all job-finders in the steady state who change group, at the discount mu-bar."""
    ss = steady_state(cal)
    shares = destination_shares(ss, cal.mu_bar)
    return (ss.H[0] * shares[0][1] + ss.H[1] * shares[1][0]) / (ss.H[0] + ss.H[1])


def fit_mu_bar(cal: Calibration, pooled_share: float) -> float:
    """The normal-times discount at which the steady state's pooled switching share equals ``pooled_share``.

    Section 2.3.2 calibrates mu-bar so that one job-finder in seven changes group; the public
    explorer reports this fit (0.169 on the 2010-19 matrix) next to the rounded 0.17 it uses.
    """

    def excess(mu: float) -> float:
        return pooled_switch_share(replace(cal, mu_bar=mu)) - pooled_share

    if excess(1.0) < 0.0:
        return 1.0
    return bisect(excess, 1e-6, 1.0, N_BISECT_MU)


def mu_from_switching_odds(switch_share: tuple[float, float]) -> float:
    """Section 3.2: the product of the two origins' odds of switching is mu-bar squared.

    A cognitive job-finder is hired into the other group with odds mu-bar times that group's
    relative hiring rate, and an other-origin job-finder with odds mu-bar times its inverse.
    """
    odds = [s / (1.0 - s) for s in switch_share]
    return math.sqrt(odds[0] * odds[1])
