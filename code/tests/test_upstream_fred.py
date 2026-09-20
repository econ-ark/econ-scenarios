"""Calibration inputs of Section 3.2 and footnote 9, recomputed from public BLS data.

Each test asserts a published number at the precision the paper prints it, and where a
plausible wrong specification exists, a companion test checks that it misses the number, so
the assertion is shown to have power. The data are the FRED series the paper cites, or their
BLS originals when FRED refuses scripted access (see ``validation.upstream_fred``).
"""

import pytest
from validation.upstream_fred import (
    SHIMER_REDESIGN,
    QuitSpec,
    dfh_filling,
    dfh_steady_state,
    implied_quit_rate,
    quit_elasticity,
    rounds_to,
)


@pytest.fixture(scope="module", params=["layoffs", "zero"])
def dfh(request):
    return dfh_filling(request.param)


def test_quit_rate_arithmetic() -> None:
    """Section 3.2: 0.219 x 3.84/96.16 = 0.875 percent a month, or 0.105 a year."""
    monthly = implied_quit_rate()
    assert rounds_to(monthly, 0.875, 3)
    assert rounds_to(12 * monthly / 100, 0.105, 3)


def test_quit_rate_arithmetic_rejects_rounded_pool() -> None:
    """The rounded pool of 3.8 and 96.2 would print 0.865, so the check sees the third decimal."""
    assert not rounds_to(implied_quit_rate(pool=3.8, employed=96.2), 0.875, 3)


def test_dfh_footnote9(dfh) -> None:
    """Footnote 9: 4.0 percent a working day, 26 working days, 0.65 filled within the month."""
    assert rounds_to(dfh["fill_rate_pct"], 4.0, 1)
    assert rounds_to(dfh["duration_days"], 26, 0)
    assert rounds_to(dfh["share_within_month"], 0.65, 2)


def test_dfh_duration_needs_monthly_durations(dfh) -> None:
    """Inverting the mean filling rate gives 25 days, so the 26 is the mean of monthly durations."""
    assert not rounds_to(dfh["duration_of_mean_rate"], 26, 0)


def test_dfh_steady_state_misses_footnote9() -> None:
    """The steady-state shortcut on 2010-19 means gives 3.8 percent and 0.63.

    Its duration, 26.50 days, sits on the rounding boundary of 26, so it is left unasserted.
    """
    s = dfh_steady_state()
    assert not rounds_to(s["fill_rate_pct"], 4.0, 1)
    assert not rounds_to(s["share_within_month"], 0.65, 2)


@pytest.mark.parametrize(
    "spec",
    [QuitSpec(dating="backward"), QuitSpec(short_scale=SHIMER_REDESIGN)],
    ids=lambda s: s.label,
)
def test_quit_elasticity_reaches_053(spec) -> None:
    """Section 3.2: 0.53, reached by two monthly log-log hazard specifications over 2001-19.

    These were found by searching a grid (``quit_grid``), so they show that 0.53 is within the
    range of natural specifications without identifying the one the paper used.
    """
    assert rounds_to(quit_elasticity(spec), 0.53, 2)


@pytest.mark.parametrize(
    "spec",
    [QuitSpec(), QuitSpec(rate="probability"), QuitSpec(freq="A")],
    ids=lambda s: s.label,
)
def test_quit_elasticity_other_specs_miss_053(spec) -> None:
    """Shimer's own dating without the redesign scaling gives 0.54; probabilities or annual means move further."""
    assert not rounds_to(quit_elasticity(spec), 0.53, 2)
