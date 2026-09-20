"""Upstream AI-usage calibration inputs (Section 3.1, 3.3, 3.4) against the numbers Korinek et
al. (2026) publish.

Two of the four targets are pure quotes from a stable, checked-in-nowhere-else PDF (Appel et al.,
2025; Bonney et al., 2026): they need no download and always run. The other two need data files
that validation.upstream_usage fetches on first use, including one file bls.gov refuses to serve
to a script. When that file is missing those tests fail with
instructions for fetching it: a check that cannot run is reported, never skipped.
"""

import re

import pytest
from validation.upstream_usage import (
    CPS_TABLE11_PATH,
    automation_share_appel2025,
    census_btos_ai_use_2026,
    cognitive_employment_share,
    observed_exposure_m,
)


@pytest.fixture
def cps_cache() -> None:
    if not CPS_TABLE11_PATH.exists():
        pytest.fail(
            f"{CPS_TABLE11_PATH} is missing. bls.gov refuses scripted downloads: open "
            "https://www.bls.gov/cps/cpsaat11.htm in a headless browser, extract the table text, and save it there.",
        )


def test_automation_share_matches_appel_2025() -> None:
    """Section 3.4: 'about half of use on Claude.ai and about three quarters on the API'."""
    result = automation_share_appel2025()
    assert result["claude_ai_automation_share"] == pytest.approx(0.50, abs=0.05)
    assert result["api_automation_share"] == pytest.approx(0.75, abs=0.05)


def test_census_btos_matches_bonney_2026() -> None:
    """Section 3.3: '18 percent of firms used AI (32 percent employment-weighted), and in 23
    percent of firms workers used generative AI in their own tasks'.
    """
    result = census_btos_ai_use_2026()
    # the fields are transcribed from the quoted abstract, so the check reads the percentages out
    # of the quote itself, in order, and compares; a slip between sentence and field fails here
    quoted_shares = [int(x) / 100 for x in re.findall(r"(\d+)%", str(result["quote"]))]
    assert quoted_shares[:4] == [
        result["firm_ai_use_share"],
        result["firm_ai_use_share_employment_weighted"],
        result["worker_genai_task_use_share"],
        result["worker_genai_task_use_share_employment_weighted"],
    ]
    assert result["firm_ai_use_share"] == pytest.approx(
        0.18,
    )  # the paper's Section 3.3 sentence


def test_cognitive_employment_share_matches_table1(cps_cache) -> None:
    """Table 1: 'cognitive share of employment... CPS 2025... SOC major groups 11-29, 41, 43' = 0.624."""
    assert round(cognitive_employment_share(), 3) == pytest.approx(0.624, abs=0.001)


def test_observed_exposure_is_concentrated_in_the_cognitive_group(cps_cache) -> None:
    """Section 3.3: 'It averages 0.22 in the cognitive group, 0.01 in the other, and 0.14
    overall.' The full recomputation needs the Anthropic dataset, the CPS cache, and the SOC
    crosswalk (all fetched on demand); this checks the qualitative finding the paper states,
    with a wide band around the printed numbers rather than exact equality, since our
    aggregation of Massenkoff-McCrory's SOC-detail scores onto CPS Table 11's occupation lines
    (unweighted within combined lines, for lack of published sub-weights) does not reproduce the
    published anchor to the last digit.
    """
    result = observed_exposure_m()
    assert result["m_other"] == pytest.approx(0.01, abs=0.01)
    assert result["m_cognitive"] == pytest.approx(0.22, abs=0.05)
    assert result["m_overall"] == pytest.approx(0.14, abs=0.03)
    assert result["m_cognitive"] > 10 * result["m_other"]
    assert result["coverage_share"] > 0.9
