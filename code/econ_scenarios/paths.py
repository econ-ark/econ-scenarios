"""Scenario paths (Section 2.1.2): logistic m_t and d_t through the mid-2026 anchors with slopes
from Eq. (8'), a linear gain a_t, and a logistic automation share psi_t (Table A.2).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .calibration import Calibration, Scenario


@dataclass(frozen=True)
class AIState:
    """The five scenario objects at one date."""

    m: float
    d: float
    a: float
    psi: float
    rho: float


@dataclass(frozen=True)
class Logistic:
    """Logistic path through ``anchor`` at ``t_anchor`` with slope ``kappa`` between ``floor`` and ``ceiling``.

    A path whose anchor is not strictly between floor and ceiling, or whose slope is zero, is
    constant at its anchor. The scenarios hold psi fixed with a ceiling equal to the anchor.
    """

    anchor: float
    ceiling: float
    kappa: float
    t_anchor: float
    floor: float = 0.0

    def __call__(self, t: float) -> float:
        if not (self.kappa > 0.0 and self.floor < self.anchor < self.ceiling):
            return self.anchor
        span = self.ceiling - self.floor
        midpoint = (
            self.t_anchor
            + math.log(span / (self.anchor - self.floor) - 1.0) / self.kappa
        )
        return self.floor + span / (1.0 + math.exp(-self.kappa * (t - midpoint)))


def logistic_slope(
    anchor: float,
    value_2030: float,
    ceiling: float,
    years: float,
    kappa_max: float | None = None,
) -> float:
    """Slope of the logistic path from ``anchor`` to ``value_2030`` over ``years``, Eq. (8').

    With ``kappa_max`` the slope is clamped to [0, kappa_max], a 2030 value at or below the
    anchor gives a constant path, and one at or above the ceiling gives ``kappa_max``.
    """
    if kappa_max is not None:
        if value_2030 <= anchor:
            return 0.0
        if value_2030 >= ceiling:
            return kappa_max
        return min(
            kappa_max,
            max(0.0, logistic_slope(anchor, value_2030, ceiling, years)),
        )
    if value_2030 == anchor:
        return 0.0
    if not (0.0 < anchor < value_2030 < ceiling):
        msg = f"a logistic path needs 0 < anchor < 2030 value < ceiling; got {anchor}, {value_2030}, {ceiling}"
        raise ValueError(
            msg,
        )
    return (
        math.log(((ceiling - anchor) / anchor) * (value_2030 / (ceiling - value_2030)))
        / years
    )


class ScenarioPaths:
    """The exogenous paths of one scenario under one calibration.

    The gain is the paper's unbounded line, a_t = a_anchor + g_a (t - t_anchor), unless the
    scenario sets ``a_ceiling``, in which case it is also kept at or above zero.
    """

    def __init__(self, scenario: Scenario, cal: Calibration) -> None:
        years = cal.t_read - cal.t_anchor
        kappa_m = logistic_slope(
            cal.m_anchor,
            scenario.m_2030,
            cal.m_bar,
            years,
            scenario.kappa_max,
        )
        kappa_d = logistic_slope(
            cal.d_anchor,
            scenario.d_2030,
            cal.d_ceiling,
            years,
            scenario.kappa_max,
        )
        psi_ceiling = (
            scenario.psi if scenario.psi_ceiling is None else scenario.psi_ceiling
        )
        self.m = Logistic(cal.m_anchor, cal.m_bar, kappa_m, cal.t_anchor)
        self.d = Logistic(cal.d_anchor, cal.d_ceiling, kappa_d, cal.t_anchor)
        self.psi = Logistic(
            scenario.psi,
            psi_ceiling,
            scenario.psi_kappa,
            cal.t_anchor,
            floor=scenario.psi_floor,
        )
        self.a_anchor = scenario.a_anchor
        self.g_a = scenario.g_a
        self.a_ceiling = scenario.a_ceiling
        self.t_anchor = cal.t_anchor
        self.rho = scenario.rho

    def a(self, t: float) -> float:
        """Log gain per AI-performed instance, Eq. (8)."""
        line = self.a_anchor + self.g_a * (t - self.t_anchor)
        if self.a_ceiling is None:
            return line
        return max(0.0, min(self.a_ceiling, line))

    def at(self, t: float) -> AIState:
        """All five scenario objects at date ``t``."""
        return AIState(
            m=self.m(t),
            d=self.d(t),
            a=self.a(t),
            psi=self.psi(t),
            rho=self.rho,
        )
