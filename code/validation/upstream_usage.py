"""Upstream data behind the AI-usage calibration inputs of Korinek et al. (2026).

Section 3.3 sets the mid-2026 affected-mass anchor from the observed-exposure measure of
Massenkoff and McCrory (2026): "It averages 0.22 in the cognitive group, 0.01 in the other, and
0.14 overall, so m = 0.14." Section 3.1 defines the cognitive group as 2018 SOC major groups
11, 13, 15, 17, 19, 21, 23, 25, 27, 29, 41, 43 and states that group's CPS 2025 employment share
as 0.624 (Table 1). Section 3.4 states the automation share psi = 0.5 is "similar to current
automation-like share of use (Appel et al., 2025)": "about half of use on Claude.ai and about
three quarters on the API looks like automation." Section 3.3 sets the diffusion anchor d = 0.10
from the Census Bureau's Business Trends and Outlook Survey: "In late 2025, 18 percent of firms
used AI (32 percent employment-weighted), and in 23 percent of firms workers used generative AI
in their own tasks (Bonney et al., 2026)." Table 1 also cites Eloundou et al. (2024) task
feasibility as the basis for the 0.2-0.5 range of 2030 affected-mass scenarios.

This module downloads each source's public data on first use, recomputes what can be recomputed from it, and reports the recomputed value against the
paper's printed number. Two of the four targets (the Anthropic and Census report statistics) are
report-stated figures with no public record-level data behind them; those are recorded as
verified quotes from the primary source PDF, not recomputations, and are marked accordingly.

Data sources:
    - Massenkoff, Maxim and Peter McCrory, "Labor market impacts of AI: A new measure and early
      evidence," Anthropic research note, March 2026. Occupation-level data:
      https://huggingface.co/datasets/Anthropic/EconomicIndex, labor_market_impacts/job_exposure.csv.
    - U.S. Bureau of Labor Statistics, Current Population Survey, Household Data, Annual Averages
      2025, Table 11: https://www.bls.gov/cps/cpsaat11.htm. bls.gov blocks scripted downloads, so
      this file must be fetched once with a browser and saved to ``CPS_TABLE11_PATH``.
    - U.S. Census Bureau / BLS, "2018 Census Occupation Code List with Crosswalk to 2018 SOC
      Codes": https://www2.census.gov/programs-surveys/demo/guidance/industry-occupation/
      2018-occupation-code-list-and-crosswalk.xlsx. Used to aggregate Massenkoff-McCrory's
      6-digit SOC detailed occupations up to the (coarser) occupation lines CPS Table 11 reports
      employment for.
    - Appel, Ruth, Peter McCrory, and Alex Tamkin, "The Anthropic Economic Index report: Uneven
      geographic and enterprise AI adoption," September 15, 2025, arXiv:2511.15080.
    - Bonney, Kathryn, Cory Breaux, Emin Dinlersoz, Lucia Foster, John Haltiwanger, and Aditya
      Pande, "The Microstructure of AI Diffusion: Evidence from Firms, Business Functions, and
      Worker Tasks," Working Paper CES-WP-26-25, U.S. Census Bureau, April 2026.
    - Eloundou, Tyna, Sam Manning, Pamela Mishkin, and Daniel Rock, "GPTs are GPTs: Labor market
      impact potential of LLMs," Science, 2024. Occupation-level data:
      https://github.com/openai/GPTs-are-GPTs, data/occ_level.csv.

Run from ``code/``: ``uv run python -m validation.upstream_usage``.
"""

from __future__ import annotations

import csv
import logging
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections import defaultdict
from pathlib import Path

import numpy as np

from .download import BROWSER_AGENT, fetch_to

log = logging.getLogger("upstream_usage")

REPO_ROOT = Path(__file__).resolve().parents[2]
UPSTREAM = REPO_ROOT / "sources" / "upstream"
AEI_DIR = UPSTREAM / "aei"
BLS_DIR = UPSTREAM / "bls"
ELOUNDOU_DIR = UPSTREAM / "eloundou"

JOB_EXPOSURE_URL = (
    "https://huggingface.co/datasets/Anthropic/EconomicIndex/resolve/main/"
    "labor_market_impacts/job_exposure.csv"
)
CROSSWALK_URL = (
    "https://www2.census.gov/programs-surveys/demo/guidance/industry-occupation/"
    "2018-occupation-code-list-and-crosswalk.xlsx"
)
ELOUNDOU_URL = (
    "https://raw.githubusercontent.com/openai/GPTs-are-GPTs/main/data/occ_level.csv"
)
# Made by hand in a browser (bls.gov blocks scripted downloads) and tracked, with its provenance
# in its header, under code/validation/data.
CPS_TABLE11_PATH = REPO_ROOT / "code" / "validation" / "data" / "cpsaat11_2025.txt"
CPS_TABLE11_SOURCE = "https://www.bls.gov/cps/cpsaat11.htm"

# 2018 SOC major groups the paper (Section 3.1, footnote 10) calls "cognitive": management,
# professional, sales, and office work.
COGNITIVE_MAJOR_GROUPS = frozenset(
    {"11", "13", "15", "17", "19", "21", "23", "25", "27", "29", "41", "43"},
)

XLSX_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
XLSX_REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


def _normalize_title(title: str) -> str:
    """Lowercase, collapse whitespace, and fold the Oxford comma so titles compare equal."""
    t = re.sub(r"\s+", " ", title.strip().lower())
    return t.replace(", and", " and")


def _download(url: str, dest: Path) -> None:
    """Fetch ``url`` to ``dest`` if it is not already cached."""
    if dest.exists():
        return
    log.info("downloading %s -> %s", url, dest)
    fetch_to(url, dest, agent=BROWSER_AGENT, timeout=60)


def _read_xlsx_sheet(path: Path, sheet_name: str) -> list[dict[str, str]]:
    """A minimal stdlib-only .xlsx reader: one named sheet, cells keyed by column letter.

    Written to avoid an openpyxl/pandas dependency for a single crosswalk file. Handles shared
    strings and inline numeric/text cells, which is all this workbook uses.
    """
    with zipfile.ZipFile(path) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        rid_to_target = {rel.get("Id"): rel.get("Target") for rel in rels}
        sheet_rid = next(
            sheet.get(f"{XLSX_REL_NS}id")
            for sheet in workbook.find("m:sheets", XLSX_NS)
            if sheet.get("name") == sheet_name
        )
        target = rid_to_target[sheet_rid]
        sheet_path = (
            "xl/" + target.lstrip("/") if not target.startswith("xl/") else target
        )
        try:
            shared_xml = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = [
                "".join(t.text or "" for t in si.findall(".//m:t", XLSX_NS))
                for si in shared_xml.findall("m:si", XLSX_NS)
            ]
        except KeyError:
            shared = []
        sheet = ET.fromstring(archive.read(sheet_path))
        rows = []
        for row in sheet.find("m:sheetData", XLSX_NS):
            cells: dict[str, str] = {}
            for cell in row:
                col = "".join(ch for ch in cell.get("r") for ch in [ch] if ch.isalpha())
                value = cell.find("m:v", XLSX_NS)
                if value is None:
                    cells[col] = ""
                elif cell.get("t") == "s":
                    cells[col] = shared[int(value.text)]
                else:
                    cells[col] = value.text
            rows.append(cells)
        return rows


def load_job_exposure() -> dict[str, tuple[str, float]]:
    """Massenkoff and McCrory (2026) observed exposure, one row per 6-digit 2018 SOC occupation.

    Returns ``{occ_code: (title, observed_exposure)}``. 756 of the roughly 793 non-military 2018
    SOC detailed occupations are covered; the rest are simply absent from the published file.
    """
    dest = AEI_DIR / "job_exposure.csv"
    _download(JOB_EXPOSURE_URL, dest)
    out = {}
    with dest.open() as f:
        for row in csv.DictReader(f):
            out[row["occ_code"]] = (row["title"], float(row["observed_exposure"]))
    return out


def load_cps_employment_detailed() -> dict[str, float]:
    """CPS 2025 Table 11: total employed (thousands) by title, normalized occupation-line title.

    bls.gov blocks scripted downloads (curl/wget/urllib all return non-content or are refused),
    so this file cannot be fetched here. It must be cached once at ``CPS_TABLE11_PATH`` using a
    browser (e.g. the Chrome MCP tool: navigate to CPS_TABLE11_SOURCE, then extract as text).
    """
    if not CPS_TABLE11_PATH.exists():
        msg = (
            f"{CPS_TABLE11_PATH} is missing; it is tracked under code/validation/data (see the "
            f"README there). bls.gov blocks scripted downloads of {CPS_TABLE11_SOURCE}; to "
            "remake it, fetch it with a browser and save the 'title<TAB>thousands' lines "
            "(starting at 'Total, 16 years and over') to this path."
        )
        raise FileNotFoundError(
            msg,
        )
    lines = CPS_TABLE11_PATH.read_text().splitlines()
    start = next(
        i for i, line in enumerate(lines) if line.startswith("Total, 16 years and over")
    )
    out = {}
    for line in lines[start:]:
        if not line.strip():
            continue
        parts = line.rsplit("\t", 1)
        if len(parts) != 2:
            continue
        title, value = parts
        try:
            out[_normalize_title(title)] = float(value)
        except ValueError:
            continue
    return out


def load_census_soc_crosswalk() -> list[tuple[str, str, str]]:
    """The 2018 Census occupation code list, as ``(title, census_code, soc_code)`` triples.

    ``soc_code`` is a 2018 SOC code, sometimes with trailing '0' or 'X' characters standing for
    "every finer code under this branch" (Census aggregates several SOC detailed occupations into
    one line for some categories, e.g. catch-all "Other ..." lines).
    """
    dest = BLS_DIR / "census_soc_crosswalk.xlsx"
    _download(CROSSWALK_URL, dest)
    rows = _read_xlsx_sheet(dest, "2018 Census Occ Code List")
    soc_pattern = re.compile(r"^\d\d-[0-9X]{4}$")
    out = []
    for row in rows:
        title, code, soc = row.get("B", ""), row.get("C", ""), row.get("D", "")
        if (
            not title
            or not code
            or not soc.strip()
            or not soc_pattern.match(soc.strip())
        ):
            continue  # blank rows, the header row itself, "none" (military), and group headers
        out.append((title.strip(), code.strip(), soc.strip()))
    return out


def _soc_specificity(soc_detail: str) -> int:
    """How many of the 4 digits after the major-group dash carry meaning.

    Trailing '0' and 'X' stand for "any digit here"; the return value is the length of the
    remaining, literal prefix (0 means the code matches an entire major group).
    """
    n = len(soc_detail)
    while n > 0 and soc_detail[n - 1] in "0X":
        n -= 1
    return n


def assign_census_lines(
    job_codes: dict[str, tuple[str, float]],
    crosswalk: list[tuple[str, str, str]],
) -> dict[str, str]:
    """Map each 6-digit SOC ``occ_code`` to the census occupation line title that reports it.

    Some census lines are catch-alls with a wildcard suffix (e.g. '15-124X' covers every SOC code
    starting '15-124' not claimed by a more specific line); ties are resolved in favor of the
    census line with the longest literal (most specific) prefix match.
    """
    by_major: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for title, _census_code, soc in crosswalk:
        major, detail = soc.split("-")
        by_major[major].append((title, detail))
    assignment = {}
    for occ_code in job_codes:
        major, detail = occ_code.split("-")
        best_title, best_specificity = None, -1
        for title, cand_detail in by_major.get(major, []):
            s = _soc_specificity(cand_detail)
            if detail[:s] == cand_detail[:s] and s > best_specificity:
                best_title, best_specificity = title, s
        if best_title is None:
            msg = f"no census line covers SOC code {occ_code}"
            raise ValueError(msg)
        assignment[occ_code] = best_title
    return assignment


def aggregate_observed_exposure_to_census_lines(
    job_exposure: dict[str, tuple[str, float]],
    crosswalk: list[tuple[str, str, str]],
) -> dict[str, tuple[float, str]]:
    """Unweighted mean of ``observed_exposure`` across SOC codes sharing a census line.

    No sub-line employment split is published, so occupations combined onto one census line are
    averaged without weights; the whole line is then weighted by its own CPS employment total.
    Returns ``{normalized_title: (average_exposure, soc_major_group)}``.
    """
    assignment = assign_census_lines(job_exposure, crosswalk)
    soc_major_of_title = {title: soc.split("-")[0] for title, _code, soc in crosswalk}
    grouped: dict[str, list[float]] = defaultdict(list)
    for occ_code, (_title, exposure) in job_exposure.items():
        grouped[assignment[occ_code]].append(exposure)
    out = {}
    for title, values in grouped.items():
        out[_normalize_title(title)] = (
            float(np.mean(values)),
            soc_major_of_title[title],
        )
    return out


def observed_exposure_m(
    job_exposure: dict[str, tuple[str, float]] | None = None,
    crosswalk: list[tuple[str, str, str]] | None = None,
    cps_employment: dict[str, float] | None = None,
) -> dict[str, float]:
    """Employment-weighted observed exposure for the cognitive group, the other group, and overall.

    Reproduces the recipe behind Section 3.3's "It averages 0.22 in the cognitive group, 0.01 in
    the other, and 0.14 overall": Massenkoff-McCrory occupation scores, aggregated to CPS Table
    11's occupation lines via the SOC crosswalk, weighted by each line's 2025 CPS employment.
    """
    job_exposure = job_exposure if job_exposure is not None else load_job_exposure()
    crosswalk = crosswalk if crosswalk is not None else load_census_soc_crosswalk()
    cps_employment = (
        cps_employment if cps_employment is not None else load_cps_employment_detailed()
    )
    census_lines = aggregate_observed_exposure_to_census_lines(job_exposure, crosswalk)

    titles, exposures, majors = [], [], []
    covered_employment = 0.0
    for title, (exposure, major) in census_lines.items():
        employment = cps_employment.get(title)
        if employment is None:
            continue
        titles.append(title)
        exposures.append(exposure)
        majors.append(major)
        covered_employment += employment
    employment = np.array([cps_employment[t] for t in titles])
    exposure = np.array(exposures)
    is_cognitive = np.array([m in COGNITIVE_MAJOR_GROUPS for m in majors])

    total_employment = sum(cps_employment_by_major_group_total(cps_employment).values())
    return {
        "m_cognitive": float(
            np.average(exposure[is_cognitive], weights=employment[is_cognitive]),
        ),
        "m_other": float(
            np.average(exposure[~is_cognitive], weights=employment[~is_cognitive]),
        ),
        "m_overall": float(np.average(exposure, weights=employment)),
        "n_occupations_matched": len(titles),
        "n_occupations_published": len(job_exposure),
        "employment_covered_thousands": covered_employment,
        "employment_total_thousands": total_employment,
        "coverage_share": covered_employment / total_employment,
    }


# CPS Table 11's minor/broad-group headers are direct SOC major-group totals, so Table 1's
# 0.624 cognitive employment share is checkable from these alone, without occupation-level
# matching.
SOC_MAJOR_GROUP_TITLES = {
    "11": "management occupations",
    "13": "business and financial operations occupations",
    "15": "computer and mathematical occupations",
    "17": "architecture and engineering occupations",
    "19": "life, physical, and social science occupations",
    "21": "community and social service occupations",
    "23": "legal occupations",
    "25": "education, training, and library occupations",
    "27": "arts, design, entertainment, sports, and media occupations",
    "29": "healthcare practitioners and technical occupations",
    "31": "healthcare support occupations",
    "33": "protective service occupations",
    "35": "food preparation and serving related occupations",
    "37": "building and grounds cleaning and maintenance occupations",
    "39": "personal care and service occupations",
    "41": "sales and related occupations",
    "43": "office and administrative support occupations",
    "45": "farming, fishing, and forestry occupations",
    "47": "construction and extraction occupations",
    "49": "installation, maintenance, and repair occupations",
    "51": "production occupations",
    "53": "transportation and material moving occupations",
}


def cps_employment_by_major_group_total(
    cps_employment: dict[str, float] | None = None,
) -> dict[str, float]:
    """CPS 2025 Table 11 total employed (thousands), keyed by 2018 SOC major-group code."""
    cps_employment = (
        cps_employment if cps_employment is not None else load_cps_employment_detailed()
    )
    return {
        code: cps_employment[_normalize_title(title)]
        for code, title in SOC_MAJOR_GROUP_TITLES.items()
    }


def cognitive_employment_share(cps_employment: dict[str, float] | None = None) -> float:
    """Table 1's "cognitive share of employment... CPS 2025... SOC major groups 11-29, 41, 43" (0.624)."""
    by_major = cps_employment_by_major_group_total(cps_employment)
    cognitive = sum(v for k, v in by_major.items() if k in COGNITIVE_MAJOR_GROUPS)
    return cognitive / sum(by_major.values())


def automation_share_appel2025() -> dict[str, object]:
    """Section 3.4's psi = 0.5 basis, quoted from Appel et al. (2025), p.5 (arXiv:2511.15080).

    Not a recomputation: Anthropic classifies automation/augmentation from raw conversation text
    via an internal classifier, and the report does not publish the underlying per-conversation
    labels, only the aggregate shares below. This function records the verified quote.
    """
    return {
        "claude_ai_automation_share": 0.50,
        "api_automation_share": 0.77,
        "quote": (
            "1P API usage is automation dominant. 77% of business uses involve automation usage "
            "patterns, compared to about 50% for Claude.ai users. This reflects the programmatic "
            "nature of API usage."
        ),
        "source": "Appel, McCrory, Tamkin et al. (2025), 'Uneven geographic and enterprise AI "
        "adoption,' arXiv:2511.15080, p.5 (Anthropic Economic Index report, published 2025-09-15).",
    }


def census_btos_ai_use_2026() -> dict[str, object]:
    """Section 3.3's d = 0.10 basis, quoted from Bonney et al. (2026), CES-WP-26-25 abstract.

    Not a recomputation: BTOS microdata are confidential Census Bureau data; the paper and this
    check both rely on the published aggregate shares.
    """
    return {
        "firm_ai_use_share": 0.18,
        "firm_ai_use_share_employment_weighted": 0.32,
        "worker_genai_task_use_share": 0.23,
        "worker_genai_task_use_share_employment_weighted": 0.41,
        "reference_period": "Nov 2025 - Jan 2026",
        "quote": (
            "During the supplement reference period (Nov 2025-Jan 2026), 18% of firms used AI in "
            "a business function, rising to 32% on an employment-weighted basis... In 23% (41%, "
            "employment-weighted) of firms, workers use AI in work-related tasks."
        ),
        "source": "Bonney, Breaux, Dinlersoz, Foster, Haltiwanger, and Pande (2026), 'The "
        "Microstructure of AI Diffusion,' CES-WP-26-25, U.S. Census Bureau, abstract.",
    }


def load_eloundou_occ_level(rating: str = "human_rating_beta") -> dict[str, float]:
    """Eloundou et al. (2024) task-feasibility ratings, aggregated from O*NET-SOC to 6-digit SOC.

    ``occ_level.csv`` rates O*NET-SOC occupations (e.g. '11-1011.00', '11-1011.03'); this collapses
    them to the 6-digit SOC code (unweighted mean) so they can be joined the same way as the
    Massenkoff-McCrory data. ``rating`` selects one of the six published columns; 'beta' is
    Eloundou et al.'s LLM-plus-software exposure measure, the one closest to what Table 1 calls
    "rated feasibility."
    """
    dest = ELOUNDOU_DIR / "occ_level.csv"
    _download(ELOUNDOU_URL, dest)
    by_soc6: dict[str, list[float]] = defaultdict(list)
    with dest.open() as f:
        for row in csv.DictReader(f):
            soc6 = row["O*NET-SOC Code"].split(".")[0]
            by_soc6[soc6].append(float(row[rating]))
    return {soc6: float(np.mean(v)) for soc6, v in by_soc6.items()}


def eloundou_cognitive_average(
    crosswalk: list[tuple[str, str, str]] | None = None,
    cps_employment: dict[str, float] | None = None,
    rating: str = "human_rating_beta",
) -> dict[str, float]:
    """Employment-weighted Eloundou et al. (2024) exposure for the cognitive group.

    Optional check (Table 1): the paper's 2030 affected-mass scenarios span "the low end, middle,
    and near the high end of rated feasibility (Eloundou et al., 2024)," 0.2-0.5. This asks
    whether the cognitive group's employment-weighted average of the public GPTs-are-GPTs
    occupation exposure data falls in that range.
    """
    crosswalk = crosswalk if crosswalk is not None else load_census_soc_crosswalk()
    cps_employment = (
        cps_employment if cps_employment is not None else load_cps_employment_detailed()
    )
    ratings = load_eloundou_occ_level(rating)
    job_exposure_shaped = {code: ("", value) for code, value in ratings.items()}
    census_lines = aggregate_observed_exposure_to_census_lines(
        job_exposure_shaped,
        crosswalk,
    )

    titles, values, majors = [], [], []
    for title, (value, major) in census_lines.items():
        if title in cps_employment:
            titles.append(title)
            values.append(value)
            majors.append(major)
    employment = np.array([cps_employment[t] for t in titles])
    value_arr = np.array(values)
    is_cognitive = np.array([m in COGNITIVE_MAJOR_GROUPS for m in majors])
    return {
        "rating": rating,
        "cognitive_average": float(
            np.average(value_arr[is_cognitive], weights=employment[is_cognitive]),
        ),
        "n_occupations": len(titles),
    }


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)

    log.info(
        "=== Target 1: observed exposure, Massenkoff and McCrory (2026), Section 3.3 ===",
    )
    try:
        result = observed_exposure_m()
        log.info("  published:   cognitive 0.22, other 0.01, overall 0.14 (m = 0.14)")
        log.info(
            "  recomputed:  cognitive %.4f, other %.4f, overall %.4f",
            result["m_cognitive"],
            result["m_other"],
            result["m_overall"],
        )
        log.info(
            "  coverage: %d of %d published occupations matched a CPS 2025 occupation line "
            "(%.1f%% of CPS employment, %.0fk of %.0fk thousand workers)",
            result["n_occupations_matched"],
            result["n_occupations_published"],
            100 * result["coverage_share"],
            result["employment_covered_thousands"],
            result["employment_total_thousands"],
        )
        log.info(
            "  cognitive employment share (Table 1: 0.624): %.4f",
            cognitive_employment_share(),
        )
    except FileNotFoundError as exc:
        log.warning("  SKIPPED: %s", exc)

    log.info("=== Target 2: automation share, Appel et al. (2025), Section 3.4 ===")
    appel = automation_share_appel2025()
    log.info(
        "  published: 'about half of use on Claude.ai and about three quarters on the API'",
    )
    log.info(
        "  verified quote: Claude.ai %.0f%%, API %.0f%% (%s)",
        100 * appel["claude_ai_automation_share"],
        100 * appel["api_automation_share"],
        appel["source"],
    )

    log.info(
        "=== Target 3: diffusion inputs, Bonney et al. (2026) / Census BTOS, Section 3.3 ===",
    )
    btos = census_btos_ai_use_2026()
    log.info(
        "  published: 18 pct. of firms used AI (32 pct. employment-weighted); 23 pct. worker task use",
    )
    log.info(
        "  verified quote: %.0f%% (%.0f%% ew) firm use; %.0f%% (%.0f%% ew) worker task use (%s)",
        100 * btos["firm_ai_use_share"],
        100 * btos["firm_ai_use_share_employment_weighted"],
        100 * btos["worker_genai_task_use_share"],
        100 * btos["worker_genai_task_use_share_employment_weighted"],
        btos["source"],
    )

    log.info(
        "=== Target 4 (optional): Eloundou et al. (2024) task feasibility, Table 1 ===",
    )
    try:
        eloundou = eloundou_cognitive_average()
        log.info(
            "  published range for 2030 affected mass: 0.2 to 0.5 (low to near-high feasibility)",
        )
        log.info(
            "  recomputed cognitive-group employment-weighted %s: %.4f (n=%d occupations)",
            eloundou["rating"],
            eloundou["cognitive_average"],
            eloundou["n_occupations"],
        )
    except FileNotFoundError as exc:
        log.warning("  SKIPPED: %s", exc)

    return 0


if __name__ == "__main__":
    sys.exit(main())
