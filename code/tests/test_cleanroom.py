"""The PDF-only implementation differs from this reproduction by one reading, the quit order. The
explorer's paths decide that reading; the published tables agree only at the explorer's quit share.
"""

from dataclasses import replace

import pytest
from econ_scenarios import Calibration, simulate
from validation.cleanroom import PDF_ONLY, QUIT_ORDER_ALIGNED, path_gaps
from validation.published import cached_runner, checks, failures


@pytest.fixture(scope="module")
def gaps():
    return path_gaps(PDF_ONLY), path_gaps(QUIT_ORDER_ALIGNED)


def test_the_pdf_only_readings_sit_a_few_ten_thousandths_away(gaps) -> None:
    pdf_only, _ = gaps
    assert min(gap for gap, _ in pdf_only.values()) > 5e-5
    assert 3e-4 < max(gap for gap, _ in pdf_only.values()) < 5e-4


def test_aligning_the_quit_order_leaves_only_roundoff(gaps) -> None:
    _, aligned = gaps
    assert max(gap for gap, _ in aligned.values()) < 1e-12


def test_the_tables_reject_the_other_quit_order() -> None:
    """Six of the published numbers leave their rounding when quits are converted before splitting."""

    def other_order(scenario, cal=None, **kw):
        return simulate(
            scenario,
            replace(cal or Calibration(), quit_order="convert_then_split"),
            **kw,
        )

    missed = failures(cached_runner(other_order))
    assert len(missed) == 6
    assert not failures(cached_runner())
    assert len(checks(cached_runner(other_order))) == len(
        checks(cached_runner()),
    )  # the same inventory under either order


def _misses(quit_order: str, share: float) -> int:
    """Published numbers outside their rounding under one order and responsive quit share."""

    def run(scenario, cal=None, **kw):
        return simulate(
            scenario,
            replace(cal or Calibration(), quit_order=quit_order, q_T_share=share),
            **kw,
        )

    return len(failures(cached_runner(run)))


def test_the_tables_identify_the_order_only_jointly_with_the_quit_share() -> None:
    """At the paper's quit rate of 0.11, each order reproduces every published number over its own
    window of shares, the windows item 2 of the notes quotes (edges on a grid of 0.0005): splitting
    first from 0.5435 to 0.547, around the explorer's 6/11, and converting first from 0.552 to
    0.5545, which Table 1 also prints as 0.55. At exactly 0.55 neither order reproduces them. At
    0.545, the share printed to one more digit, only splitting first does, as the section on the
    paper's open choices says.
    """
    split, convert = "split_then_convert", "convert_then_split"
    for share in (0.5435, 0.5450, 0.5470, 6.0 / 11.0):
        assert _misses(split, share) == 0, share
    for share in (0.5430, 0.5475):
        assert _misses(split, share) > 0, share
    for share in (0.5520, 0.5545):
        assert _misses(convert, share) == 0, share
    for share in (0.5450, 0.5515, 0.5550, 6.0 / 11.0):
        assert _misses(convert, share) > 0, share
    assert _misses(split, 0.55) == 7
    assert _misses(convert, 0.55) == 4
