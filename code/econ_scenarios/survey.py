"""Appendix B: how each survey answer is coded into a model parameter (Table B.1).

The respondent-level survey data are not public, so Tables 2 and 4 cannot be recomputed. The
coding itself is fully specified, and this module reproduces it.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from .calibration import Calibration

if TYPE_CHECKING:
    from collections.abc import Iterable

N_TASKS = 8
IN_PERSON_DISCOUNT = 0.95  # a fraction of knowledge work continues to be done in person

# Adoption: bin midpoints (Table B.1).
ADOPTION = {
    "less than 10%": 0.05,
    "10-24%": 0.17,
    "25-49%": 0.37,
    "50-74%": 0.62,
    "more than 75%": 0.87,
}

# Automation: what each answer counts toward psi; None drops the task from both numerator and denominator.
AUTOMATION = {
    "AI does it alone": 1.0,
    "AI does most of it, with workers checking": 0.5,
    "workers do most of it, with AI helping": 0.0,
    "workers do it alone": None,
}

# Productivity gain: each option read as a time ratio; taking longer counts as no gain.
TIME_RATIO = {
    "it takes longer": 1.0,
    "about the same time": 1.0,
    "a little less time": 0.8,
    "about half the time": 0.5,
    "about a quarter of the time": 0.25,
    "about a tenth of the time or less": 0.1,
}

# Re-employment: each bin's midpoint in months; None is "more than 3 years, or never".
MONTHS = {
    "less than 1 month": 0.5,
    "1-2 months": 1.5,
    "3-4 months": 3.5,
    "5-6 months": 5.5,
    "7-12 months": 9.5,
    "13-24 months": 18.5,
    "2-3 years": 30.0,
    "more than 3 years, or never": None,
}


def knowledge_work_share(n_by_2030: int, n_answered: int = N_TASKS) -> float:
    """Place on the knowledge-work scale: tasks expected by 2030 over rows answered, times 0.95."""
    return n_by_2030 / n_answered * IN_PERSON_DISCOUNT


def capability_m(
    n_by_2030: int,
    n_answered: int = N_TASKS,
    cal: Calibration | None = None,
) -> float:
    """m_2030: the knowledge-work share times the cognitive share of the wage bill, s_C/s_L."""
    cal = Calibration() if cal is None else cal
    return knowledge_work_share(n_by_2030, n_answered) * cal.share_C


def adoption_d(answer: str) -> float:
    """d_2030 of an adoption answer."""
    return ADOPTION[answer]


def automation_psi(answers: Iterable[str]) -> float:
    """psi: the counts of the tasks AI performs over their number."""
    counts = [AUTOMATION[a] for a in answers if AUTOMATION[a] is not None]
    if not counts:
        msg = "psi is undefined when no listed task is performed by AI"
        raise ValueError(msg)
    return sum(counts) / len(counts)


def gain_a(answer: str) -> float:
    """a_2030: the log of the speed-up, ln(1 / time ratio)."""
    return math.log(1.0 / TIME_RATIO[answer])


def reemployment_mu(answer: str, cal: Calibration | None = None) -> float:
    """mu: mu-bar times three months over the answer's midpoint, capped at one; zero for never."""
    cal = Calibration() if cal is None else cal
    months = MONTHS[answer]
    if months is None:
        return 0.0
    return min(1.0, cal.mu_bar * 3.0 / months)
