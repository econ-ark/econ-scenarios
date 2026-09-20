"""Five quiz answers turned into a scenario, as the public explorer does it.

The scenario explorer at https://www.anthropic.com/institute/econ-scenarios asks a visitor five
questions, the same five the paper's survey asks (Section 3.5), and runs the model at the implied
parameters. This module reproduces that mapping, so a visitor's scenario can be rerun here. The
parameters the quiz does not ask about (reinstatement, posting speed, rigidity, capital supply)
come from the substantial scenario, as in the paper's survey runs (Table 4 note).

Where the explorer goes beyond the paper, the choice is named: the gain is capped at ln 30 and
the logistic slopes are clamped to [0, 3], so that answers at the ceilings are well defined.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .calibration import EXTREME, MODEST, SUBSTANTIAL, Calibration, Scenario

GAIN_CEILING = math.log(30.0)
KAPPA_MAX = 3.0
MAX_GAIN = 10.0
NEVER_MONTHS = 600.0
PSI_RANGE = (0.02, 0.98)
PRESETS = (MODEST, SUBSTANTIAL, EXTREME)


@dataclass(frozen=True)
class Answers:
    """A visitor's five answers.

    ``capability``: share of knowledge-work tasks AI can do by 2030. ``adoption``: share of those
    it is used for at work in 2030. ``alone``: share of AI-performed tasks done with nobody in the
    loop. ``gain``: time without AI over time with AI, a multiple of at least one. ``months``: time
    for a worker displaced by AI to find a job in a new occupation; ``NEVER_MONTHS`` or more
    means never.
    """

    capability: float
    adoption: float
    alone: float
    gain: float
    months: float


def _unit(x: float) -> float:
    return max(0.0, min(1.0, x))


def _gain_path(a_2030: float, cal: Calibration) -> tuple[float, float]:
    """Anchor and slope of the gain line reaching ``a_2030`` in 2030.

    A preset's own 2030 value keeps the preset's line. Otherwise a gain at or below the
    substantial anchor holds flat from mid-2026, and a larger one rises in a line from it.
    """
    years = cal.t_read - cal.t_anchor
    for preset in PRESETS:
        if abs(preset.a_anchor + preset.g_a * years - a_2030) < 1e-12:
            return preset.a_anchor, preset.g_a
    if a_2030 <= SUBSTANTIAL.a_anchor:
        return a_2030, 0.0
    return SUBSTANTIAL.a_anchor, (a_2030 - SUBSTANTIAL.a_anchor) / years


def mu_from_months(months: float, cal: Calibration) -> float:
    """Search discount of an answer in months: mu-bar scaled by three months over the answer (Appendix B)."""
    if months >= NEVER_MONTHS:
        return 0.0
    return min(1.0, (3.0 / max(1.0, months)) * cal.mu_bar)


def answers_to_scenario(
    answers: Answers,
    cal: Calibration | None = None,
    base: Scenario = SUBSTANTIAL,
) -> Scenario:
    """The scenario the explorer runs for ``answers``; reinstatement and posting speed from ``base``."""
    cal = Calibration() if cal is None else cal
    m_2030 = min(max(_unit(answers.capability) * cal.share_C, cal.m_anchor), cal.m_bar)
    d_2030 = min(max(_unit(answers.adoption), cal.d_anchor), cal.d_ceiling)
    a_anchor, g_a = _gain_path(math.log(min(MAX_GAIN, max(1.0, answers.gain))), cal)
    psi = max(PSI_RANGE[0], min(PSI_RANGE[1], answers.alone))
    return Scenario(
        "quiz",
        m_2030=m_2030,
        d_2030=d_2030,
        a_anchor=a_anchor,
        g_a=g_a,
        psi=psi,
        rho=base.rho,
        mu=mu_from_months(answers.months, cal),
        theta_H=base.theta_H,
        a_ceiling=GAIN_CEILING,
        kappa_max=KAPPA_MAX,
    )


def preset_answers(scenario: Scenario, cal: Calibration | None = None) -> Answers:
    """The answers that reproduce one of the paper's scenarios."""
    cal = Calibration() if cal is None else cal
    a_2030 = scenario.a_anchor + scenario.g_a * (cal.t_read - cal.t_anchor)
    return Answers(
        capability=scenario.m_2030 / cal.share_C,
        adoption=scenario.d_2030,
        alone=scenario.psi,
        gain=math.exp(a_2030),
        months=3.0 * cal.mu_bar / scenario.mu if scenario.mu > 0 else NEVER_MONTHS,
    )
