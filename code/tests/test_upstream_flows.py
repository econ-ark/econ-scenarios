"""Public cross-references for the flow inputs of Table 1, panel D (validation/upstream_flows.py).

Each public estimate uses an estimator that differs from the paper's IPUMS matched-file tabulation,
so every tolerance is a band sized to that documented gap, and every band comes with a rejection
check: a nearby wrong value it must exclude. A data file not yet downloaded fails its test with
the command that fetches it.
"""

import numpy as np
import pytest
from econ_scenarios.calibration import (
    CPS2025_EMPLOYED,
    CPS2025_UNEMPLOYED,
    IPUMS_EU_HAZARDS,
    SWITCHING,
    cognitive_share,
    separation_relatives,
)
from validation import upstream_flows as uf
from validation.fragments import PUBLIC_DATA


def need(*paths) -> None:
    for path in paths:
        try:
            uf.require(path)
        except FileNotFoundError as error:
            pytest.fail(str(error))


@pytest.fixture(scope="module")
def flows():
    need(
        *(uf.FLOWS_DIR / name for name, _, _ in uf.BLS_FILES),
        *(uf.FLOWS_DIR / f"{s}.csv" for s in uf.FRED_SERIES),
    )
    return uf.aggregate_flows()


@pytest.fixture(scope="module")
def occupations():
    need(uf.OCCUPATION_CSV)
    return uf.group_separations()


@pytest.fixture(scope="module")
def ctv() -> None:
    need(*(uf.CTV_DIR / name for name in uf.CTV_FILES))


def test_flow_series_identifiers(flows) -> None:
    """Last month's levels equal the sums of the flows out of them, which pins down every series ID."""
    assert flows.n_months == 120
    assert flows.stock_gap < 0.005
    s = {key: uf.bls_series()[sid] for key, sid in uf.FLOW_SERIES.items()}
    swapped = max(
        abs((s["EE"][t] + s["EU"][t] + s["UN"][t]) / s["E"][uf.previous(t)] - 1)
        for t in uf.months(2010, 2019)
    )
    assert swapped > 0.01, "the identity check cannot tell E-to-N from U-to-N"


def test_aggregate_rates_match_bls_flows(flows) -> None:
    """BLS flows land within 5 percent of the IPUMS hazards (gaps 2.4 and 2.8 percent in 2010-19)."""
    assert flows.ue == pytest.approx(uf.EXPLORER_UE["all"], rel=0.05)
    assert flows.eu == pytest.approx(uf.EXPLORER_EU_ALL, rel=0.05)
    assert flows.shimer != pytest.approx(uf.EXPLORER_UE["all"], rel=0.05), (
        "the band admits the Shimer rate"
    )


def test_occupation_rows_partition_the_groups() -> None:
    """Subtotals equal their leaves, and the 2025 group sums reproduce the calibration's CPS 2025 counts."""
    need(uf.OCCUPATION_CSV)
    assert uf.subtotal_gap() <= 2
    sums = uf.group_sums(2025)
    for index, group in enumerate(("cognitive", "other")):
        employed, unemployed, _ = sums[group]
        assert abs(employed - CPS2025_EMPLOYED[index]) <= 3
        assert abs(unemployed - CPS2025_UNEMPLOYED[index]) <= 3


def test_separation_ratio_by_group(occupations) -> None:
    """Short-term unemployment by last occupation puts the other group's rate near 2.1 times the cognitive rate.

    The IPUMS hazards give 2.20. The band of 10 percent covers the estimator gap (reentrants from
    nonparticipation, duration misreporting) and still rejects the explorer's equal-separations option.
    """
    eu_c, eu_n = IPUMS_EU_HAZARDS["2010-19"]
    assert occupations.ratio == pytest.approx(eu_n / eu_c, rel=0.10)
    assert pytest.approx(eu_n / eu_c, rel=0.10) != 1.0
    paper = separation_relatives(cognitive_share())
    for public, target in zip(occupations.relatives, paper, strict=True):
        assert public == pytest.approx(target, abs=0.05)
    assert all(abs(1.0 - target) > 0.05 for target in paper), (
        "the band admits equal separations"
    )


def test_finding_ratio_by_group(occupations) -> None:
    """The steady-state finding rates of the two groups stand in the ratio the IPUMS hazards give (1.107)."""
    target = uf.EXPLORER_UE["other"] / uf.EXPLORER_UE["cognitive"]
    assert occupations.finding_ratio == pytest.approx(target, abs=0.03)
    assert abs(1.0 - target) > 0.03, "the band admits equal finding rates"


def test_ctv_readers(ctv) -> None:
    """The numpy Stata and xlsx readers recover the excerpt and a de-garbling matrix that inverts Gamma."""
    d = uf.ctv_excerpt()
    assert d["year"].size == 311847
    assert (int(d["year"].min()), int(d["year"].max())) == (1976, 2021)
    gamma = uf.read_xlsx_matrix(uf.CTV_DIR / "Gammamat_mm_c_v2.xlsx")
    assert abs(gamma.sum(axis=1) - 1).max() < 1e-12
    assert abs(uf.ctv_degarbling() @ gamma - np.eye(22)).max() < 1e-12


@pytest.mark.parametrize(
    ("window", "label"),
    [((2010, 2019), "CPS 2010-19"), ((1976, 2021), "CPS 1976-2021")],
)
def test_ctv_switching_shares(ctv, window, label) -> None:
    """Corrected CTV job-finder flows reproduce the explorer's switching shares.

    The pooled share lands within 0.06 points and the by-origin shares within 0.42 points. The paper
    does not state its sample, so the remaining gap is the sample definition. The raw shares, and the
    correction applied in the transposed orientation, both fall outside the pooled band.
    """
    target = SWITCHING[label]
    public = uf.ctv_switching(window)
    assert public[2] == pytest.approx(target["pooled"], abs=0.0015)
    for share, goal in zip(public[:2], target["switch_share"], strict=True):
        assert share == pytest.approx(goal, abs=0.005)
    assert uf.search_discount(*public[:2]) == pytest.approx(
        uf.search_discount(*target["switch_share"]),
        abs=0.005,
    )
    raw = uf.ctv_switching(window, correct=False)
    assert raw[2] != pytest.approx(target["pooled"], abs=0.0015), (
        "the band admits uncorrected flows"
    )
    flows = uf.ctv_flows(window)
    flows[uf.FARMING, :] = 0.0
    flows[:, uf.FARMING] = 0.0
    g_inv = uf.ctv_degarbling()
    transposed = uf.switching_shares(g_inv @ flows @ g_inv.T, ~uf.FARMING)
    assert transposed[2] != pytest.approx(target["pooled"], abs=0.0015), (
        "the band admits the wrong orientation"
    )


def test_the_articles_public_data_table_matches_the_flows_recomputation(
    flows,
    occupations,
) -> None:
    """The report prints these three cells at one more digit than the paper does. Nothing
    regenerates that table, so this ties the pinned strings to the data they were read from.
    """
    assert PUBLIC_DATA["Job finding from unemployment, per month"] == f"{flows.ue:.4f}"
    assert (
        PUBLIC_DATA["Job loss from employment, per month"]
        == f"{100 * flows.eu:.4f} percent"
    )
    assert (
        PUBLIC_DATA["Separation rate, other relative to cognitive"]
        == f"{occupations.ratio:.4f}"
    )
