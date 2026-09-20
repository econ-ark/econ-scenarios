"""Instrument 2: every number the paper publishes, at its printed rounding."""

import math
from collections import Counter
from dataclasses import replace

import pytest
from econ_scenarios import SUBSTANTIAL, Calibration, simulate
from econ_scenarios.paths import ScenarioPaths
from econ_scenarios.production import potential, tfp_base_weight
from validation.fragments import (
    FRAGMENTS,
    INVENTORY_ROWS,
    PUBLIC_DATA,
    bound_up,
    fragments,
    inventory,
    profit_share,
)
from validation.plants import planted
from validation.published import (
    ONE_MORE_DIGIT,
    PRINTED_INPUTS,
    Check,
    cached_runner,
    checks,
    output_misses,
    text_table_differences,
    transfer_bases,
)
from validation.resolution import other_quit_reading, quit_window

# The published numbers by source: Tables 3, 5, and 6, footnote 14, the steady state of Section
# 2.3.2, the text, Table B.1 with Appendix B.3 and the two mu-bar rules, the explorer page's text.
INVENTORY = Counter(
    {
        "Table 3": 60,
        "Table 5": 40,
        "Table 6": 49,
        "Footnote 14": 3,
        "Section 2.3.2": 11,
        "Table 1": 5,
        "Table A.2": 6,
        "Section 2.1.3": 3,
        "Section 4.2": 1,
        "Section 2.2.1": 1,
        "Section 4.3": 1,
        "Table B.1": 30,
        "Appendix B.3": 1,
        "Section 3.2": 1,
        "Explorer page": 14,
    },
)


def _prints_as(value: float, published: float, decimals: int) -> bool:
    return Check("", "", published, value, decimals).ok


def test_published_numbers_fragment_is_fresh() -> None:
    """The article's table of the 226 numbers by source is what the code computes now."""
    for name, text in fragments().items():
        assert (FRAGMENTS / name).read_text() == text, name


def test_every_published_number_is_reproduced() -> None:
    results = checks(cached_runner())
    missed = [
        f"{c.source}: {c.label}: published {c.published}, model {c.model:.4f}"
        for c in results
        if not c.ok
    ]
    # the inventory by source, so that a dropped check in one table cannot net out against an
    # added check in another; the total is 226
    assert Counter(c.source for c in results) == INVENTORY
    # Out of sample: the definition is fixed by the paper's text. Fitted: footnote 14 (3) and the page's
    # dollar GDP, worker split and typical-respondent numbers (12).
    assert sum(c.basis == "fitted" for c in results) == 15
    # Inputs the model takes as given: Table 1 (5), Table A.2 (6), Table B.1 and its example (31), the odds rule (1).
    assert sum(c.role == "input" for c in results) == 43
    assert not missed, "\n".join(missed)


def test_the_mid_2026_unemployment_sentence_dates_its_starting_rate_differently() -> (
    None
):
    """Section 4.2's "rises from 2.9 percent in mid-2026": the model gives 3.06 there, because the
    scenario mu applies from 2024, while its 2024 value (the steady state) prints as 2.9.
    """
    run = cached_runner()
    c = text_table_differences(run)[0]
    assert c.basis == "text_differs"
    assert not c.ok
    assert round(c.model, 2) == 3.06
    sim = run(SUBSTANTIAL)
    k0 = sim.index(Calibration().t0)
    at_t0 = 100 * sim["U_C"][k0] / (sim["U_C"][k0] + sim["ell_C"][k0])
    assert _prints_as(at_t0, 2.9, 1)
    assert text_table_differences(run)[0] not in checks(run)


def test_the_more_than_50_percent_rise_holds_only_from_2024() -> None:
    """Section 4.2's "more than a 50 percent increase" to 2030: 59 percent measured from the 2024
    rate (2.85), 48 percent from the mid-2026 rate (3.06) that the sentence names.
    """
    cal = Calibration()
    run = cached_runner()
    sim = run(SUBSTANTIAL)

    def rate(t):
        k = sim.index(t)
        return 100 * sim["U_C"][k] / (sim["U_C"][k] + sim["ell_C"][k])

    start, anchor, end = rate(cal.t0), rate(cal.t_anchor), rate(cal.t_read)
    assert (round(start, 2), round(anchor, 2), round(end, 2)) == (2.85, 3.06, 4.53)
    assert round(100 * (end / start - 1)) == 59
    assert round(100 * (end / anchor - 1)) == 48
    recorded = text_table_differences(run)[1]
    assert recorded.basis == "text_differs"
    assert recorded.model < 50.0 < 100 * (end / start - 1)


def test_section_2_1_3_mixes_the_ideas_channel() -> None:
    """The wage's 1.9 needs the ideas gain Delta ln A, the TFP gain's 0.029 needs it left out, and
    the rental rate prints as 4.6 either way.
    """
    cal = Calibration()
    sim = cached_runner()(SUBSTANTIAL)
    k = sim.index(cal.t_read)
    x = ScenarioPaths(SUBSTANTIAL, cal).at(cal.t_read)
    dlnA = sim["dlnA"][k]
    with_ideas, level_only = potential(x, dlnA, cal), potential(x, 0.0, cal)
    assert _prints_as(100 * math.expm1(with_ideas.lnW), 1.9, 1)
    assert not _prints_as(100 * math.expm1(level_only.lnW), 1.9, 1)
    assert _prints_as(tfp_base_weight(x, 0.0, cal), 0.029, 3)
    assert not _prints_as(tfp_base_weight(x, dlnA, cal), 0.029, 3)
    assert _prints_as(100 * math.expm1(with_ideas.dlnr), 4.6, 1)
    assert _prints_as(100 * math.expm1(level_only.dlnr), 4.6, 1)


def test_one_more_printed_digit_in_table_1_reproduces_the_tables() -> None:
    """Table 1's inputs as printed miss 20 of the 183 published outputs; printed to one more digit,
    they miss none, as the reproduction's inventory and its Conclusion say.
    """
    assert output_misses(**PRINTED_INPUTS) == 20
    assert output_misses(**ONE_MORE_DIGIT) == 0


def test_the_report_states_the_printed_input_misses_as_computed() -> None:
    """The abstract, keypoints, and introduction say Table 1 as printed reproduces 163 of the 183
    outputs, and the introduction says where the 20 misses fall: Tables 3, 5, and 6, the steady
    state of Section 2.3.2, and the explorer page, in the substantial and extreme scenarios and
    never the modest one. A perturbed count or a miss in the modest column fails.
    """
    text = ARTICLE.read_text()
    misses = output_misses(**PRINTED_INPUTS)
    assert text.count(f"{183 - misses} of the 183") >= 3
    assert f"{184 - misses} of the 183" not in text
    assert f"{182 - misses} of the 183" not in text

    def run(scenario, cal=None, **kw):
        return simulate(scenario, replace(cal or Calibration(), **PRINTED_INPUTS), **kw)

    missed = [c for c in checks(cached_runner(run)) if c.role == "output" and not c.ok]
    assert len(missed) == misses
    assert {c.source for c in missed} == {
        "Table 3",
        "Table 5",
        "Table 6",
        "Section 2.3.2",
        "Explorer page",
    }
    assert not any("modest" in c.label for c in missed)
    assert any("substantial" in c.label for c in missed)
    assert any("extreme" in c.label for c in missed)


def test_the_inventory_prints_what_the_code_computes() -> None:
    """The inventory table's numeric cells are the functions' values, and a perturbed count fails."""
    text = inventory()
    assert text.count(r" \\") == 1 + len(
        INVENTORY_ROWS,
    )  # the header row and twelve rows
    lo, hi = quit_window()
    for cell in (
        f"{output_misses(**PRINTED_INPUTS)} of 183",
        f"{other_quit_reading(share=6 / 11)[0]} published numbers",
        f"{lo:.4f} to {hi:.4f}",
        # Two decimals, not the paper's whole numbers: the row exists to show the base moves the
        # transfer, and 84 alone reads as the footnote's own figure recovered exactly.
        *(f"{base:.2f}" for base in transfer_bases(cached_runner())),
    ):
        assert cell in text, cell
    assert f"{output_misses(**PRINTED_INPUTS) + 1} of 183" not in text


ARTICLE = FRAGMENTS.parent / "reproduction.md"


def test_the_public_data_table_prints_the_recomputed_values() -> None:
    """The report's public-data table is MyST markdown, since its cells carry citations, so nothing
    regenerates it. Every recomputed cell it prints is pinned here, and a perturbed digit fails.
    """
    rows = {
        line.split("|")[1].strip(): line.split("|")[3].strip()
        for line in ARTICLE.read_text().splitlines()
        if line.startswith("| ") and line.count("|") == 6
    }
    for label, value in PUBLIC_DATA.items():
        assert rows.get(label) == value, f"{label}: {rows.get(label)!r}"


def test_the_printed_profit_bound_bounds_the_computed_share() -> None:
    """An upper bound has to round away from zero. Ordinary rounding printed 0.3074 as an "at most
    0.3", which the profit it reports exceeds; the second assertion fails if that trap ever goes.
    """
    share = profit_share(cached_runner())
    assert share <= bound_up(share, 2)
    assert round(share, 1) < share, (
        "the rounding trap this guards is gone; revisit the bound"
    )


def test_the_quit_window_refuses_to_run_under_a_plant() -> None:
    """A window computed under a plant would be memoized under the correct model's key, so the
    inventory would print it and the freshness test above would agree with it. It raises instead,
    and the correct window, which brackets the explorer's 6/11, survives the attempt.
    """
    with planted("quit-fraction", 1.0), pytest.raises(RuntimeError):
        quit_window()
    lo, hi = quit_window()
    assert lo < 6 / 11 < hi
