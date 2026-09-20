"""Public cross-references for the labor-flow inputs of Table 1, panel D.

The paper takes its flows from the IPUMS-CPS matched monthly files of 2010-19 and its switching
shares from the replication files of Carrillo-Tudela and Visschers (2023). The unrounded values the
calibration uses come from the explorer's record. This module recomputes each input, or its closest
public analogue, from files anyone can download without a microdata account, and logs the paper's
value beside the public one.

1. Aggregate flows. The BLS labor force status flows (research series, seasonally adjusted, ages 16
   and over) give the monthly U-to-E flow over the previous month's unemployment and the E-to-U flow
   over the previous month's employment, averaged over 2010-19. FRED's UNEMPLOY and UEMPLT5 give
   Shimer's finding probability from short-term unemployment.
2. Separations by group. BLS annual-average Table 32 (unemployed by occupation of last job and
   duration) and Table 11 (employed by occupation), 2011-19, give the unemployed for less than five
   weeks over employment, a monthly inflow rate by group. bls.gov refuses scripted clients, so the
   rows are extracted in a browser session with ``BLS_EXTRACTION_JS`` below and saved to
   ``OCCUPATION_CSV``.
3. Switching shares. The Carrillo-Tudela and Visschers package contains the IPUMS-CPS excerpt behind
   their CPS results (job finders 1976-2021, unemployed in one month and employed the next, with an
   unimputed occupation in both) and their SIPP estimate of the 22-occupation miscoding matrix.
   Tabulating the excerpt and removing coding errors as their code does gives the shares the paper
   quotes, up to the sample definition, which the paper does not state.

Run from ``code/`` with ``uv run python -m validation.upstream_flows``. It downloads any
scriptable file (BLS API, FRED, GitHub) it does not already have before computing.
"""

from __future__ import annotations

import csv
import functools
import json
import logging
import math
import sys
import urllib.parse
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from econ_scenarios.calibration import (
    IPUMS_EU_HAZARDS,
    SWITCHING,
    cognitive_share,
    separation_relatives,
)

from .download import TOOL_AGENT, fetch_to

log = logging.getLogger("upstream_flows")

REPO = Path(__file__).resolve().parents[2]
UPSTREAM = REPO / "sources" / "upstream"
FLOWS_DIR = UPSTREAM / "flows"
CTV_DIR = UPSTREAM / "ctv"
# Made by hand in a browser (bls.gov refuses scripted clients) and tracked, with its provenance,
# under code/validation/data; the scriptable downloads go under sources/upstream.
OCCUPATION_CSV = (
    REPO / "code" / "validation" / "data" / "bls_cps_occupation_duration.csv"
)
REGENERATE = "cd code && uv run python -m validation.upstream_flows"

# The explorer's calibration record (2026-09-10) for IPUMS-CPS 2010-19, as quoted in the reproduction
# brief: U-to-E hazards by group of origin and pooled, and the pooled E-to-U hazard. The by-group E-to-U
# hazards and the switching shares are in econ_scenarios.calibration.
EXPLORER_UE = {"cognitive": 0.2070, "other": 0.2292, "all": 0.2191}
EXPLORER_EU_ALL = 0.012203

# --- 1. BLS labor force status flows and FRED short-term unemployment --------------------------------

BLS_API = "https://api.bls.gov/publicAPI/v1/timeseries/data/"
# Levels and flows, thousands, seasonally adjusted. A flow XY is the number in status Y this month who
# were in status X last month (BLS research series, https://www.bls.gov/cps/cps_flows.htm).
FLOW_SERIES = {
    "E": "LNS12000000",
    "U": "LNS13000000",
    "EE": "LNS17000000",
    "UE": "LNS17100000",
    "EU": "LNS17400000",
    "UU": "LNS17500000",
    "EN": "LNS17800000",
    "UN": "LNS17900000",
}
# The keyless v1 API returns at most ten years per request.
BLS_FILES = (
    ("bls_api_2009_2018.json", 2009, 2018),
    ("bls_api_2019_2020.json", 2019, 2020),
)
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={}"
FRED_SERIES = ("UNEMPLOY", "UEMPLT5")

# --- 2. BLS annual-average tables by occupation ------------------------------------------------------

# Leaf rows of Tables 11 and 32 and the 2018 SOC major groups they cover. The two groups partition the
# occupations exactly: cognitive is SOC 11-29, 41 and 43, all other is SOC 31-39 and 45-53.
COGNITIVE_ROWS = (
    "mgmt_bus_fin",
    "professional",
    "sales",
    "office_admin",
)  # 11-13, 15-29, 41, 43
OTHER_ROWS = (
    "service",
    "farming",
    "construction",
    "install_repair",
    "production",
    "transportation",
)  # 31-39, 45, 47, 49, 51, 53
# Published subtotals, which must never be added to their own leaves.
SUBTOTALS = {
    "sub_mgmt_prof": ("mgmt_bus_fin", "professional"),
    "sub_sales_office": ("sales", "office_admin"),
    "sub_natres_constr_maint": ("farming", "construction", "install_repair"),
    "sub_prod_transp": ("production", "transportation"),
}
OCCUPATION_YEARS = tuple(range(2011, 2020))

# Pasted into the console of any www.bls.gov page, this prints the CSV body of OCCUPATION_CSV.
BLS_EXTRACTION_JS = r"""
(async()=>{const rows={'Total unemployed':'total','Total, 16 years and over':'total',
'No previous work experience':'no_previous_work',
'Management, professional, and related occupations':'sub_mgmt_prof',
'Management, business, and financial operations occupations':'mgmt_bus_fin',
'Professional and related occupations':'professional','Service occupations':'service',
'Sales and office occupations':'sub_sales_office','Sales and related occupations':'sales',
'Office and administrative support occupations':'office_admin',
'Natural resources, construction, and maintenance occupations':'sub_natres_constr_maint',
'Farming, fishing, and forestry occupations':'farming','Construction and extraction occupations':'construction',
'Installation, maintenance, and repair occupations':'install_repair',
'Production, transportation, and material moving occupations':'sub_prod_transp',
'Production occupations':'production','Transportation and material moving occupations':'transportation'};
const out=['year,table,row,value_total,value_lt5wk,url'];
for(const y of [2011,2012,2013,2014,2015,2016,2017,2018,2019,2025]){for(const tb of ['cpsaat32','cpsaat11']){
const url=y==2025?'/cps/'+tb+'.htm':'/cps/aa'+y+'/'+tb+'.htm';const r=await fetch(url);
const d=new DOMParser().parseFromString(await r.text(),'text/html');
const t=d.querySelector('table.regular')||d.querySelector('table');const seen={};
for(const tr of t.querySelectorAll('tr')){const c=[...tr.querySelectorAll('th,td')].map(x=>x.textContent.trim().replace(/\s+/g,' '));
const lab=c[0].replace(/\(\d+\)$/,'').trim();if(lab in rows&&!(lab in seen)){seen[lab]=1;
out.push([y,tb,rows[lab],c[1].replace(/,/g,''),tb=='cpsaat32'?c[2].replace(/,/g,''):'','https://www.bls.gov'+url].join(','))}}}}
return out.join('\n')})()
"""

# --- 3. Carrillo-Tudela and Visschers (2023) replication files ----------------------------------------

CTV_COMMIT = "f7b316440c548018f287d575756e03471472b88b"  # github.com/CTVproject/Replication, 2023-01-26
CTV_FILES = {
    "cps_excerpt_ctv.dta": "Package Full/CPS/cps_excerpt_ctv.dta",
    "Gammainv_mm_c_v2_REFERENCE.xlsx": "Package Full/SIPP 1. Miscoding/Gammainv_mm_c_v2_REFERENCE.xlsx",
    "Gammamat_mm_c_v2.xlsx": "Package Full/SIPP 1. Miscoding/Gammamat_mm_c_v2.xlsx",
}
# occ2010 ranges to 2000 SOC major groups, as in mmocc_exe of their cps_regressions_maintext.do. The
# ranges leave out a few residual codes (1980, 4965, 5940, 7630, 8965) and the military.
CTV_MAJOR_GROUPS = (
    (10, 430, 11),
    (500, 950, 13),
    (1000, 1240, 15),
    (1300, 1560, 17),
    (1600, 1960, 19),
    (2000, 2060, 21),
    (2100, 2150, 23),
    (2200, 2550, 25),
    (2600, 2960, 27),
    (3000, 3540, 29),
    (3600, 3650, 31),
    (3700, 3950, 33),
    (4000, 4160, 35),
    (4200, 4250, 37),
    (4300, 4650, 39),
    (4700, 4960, 41),
    (5000, 5930, 43),
    (6000, 6130, 45),
    (6200, 6940, 47),
    (7000, 7620, 49),
    (7700, 8960, 51),
    (9000, 9750, 53),
)
CTV_RESIDUAL_CODES = {1980: 19, 4965: 41, 5940: 43, 7630: 49, 8965: 51}
SOC_CODES = np.array([code for _, _, code in CTV_MAJOR_GROUPS])
COGNITIVE = np.isin(SOC_CODES, (11, 13, 15, 17, 19, 21, 23, 25, 27, 29, 41, 43))
FARMING = SOC_CODES == 45

_DTA_NUMERIC = {65526: "<f8", 65527: "<f4", 65528: "<i4", 65529: "<i2", 65530: "i1"}
# Stata stores missing values above these bounds.
_DTA_MISSING = {
    "<f8": 2.0**1023,
    "<f4": 2.0**127,
    "<i4": 2147483621,
    "<i2": 32741,
    "i1": 101,
}
_XLSX_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


# --- downloads ---------------------------------------------------------------------------------------


def _fetch(url: str, path: Path, payload: bytes | None = None) -> None:
    body = fetch_to(
        url,
        path,
        agent=TOOL_AGENT,
        timeout=120,
        payload=payload,
        content_type="application/json",
    )
    log.info("downloaded %s (%d bytes)", path.relative_to(REPO), len(body))


def download_missing() -> None:
    """Fetch every scriptable upstream file not already downloaded."""
    for name, start, end in BLS_FILES:
        path = FLOWS_DIR / name
        if not path.exists():
            query = {
                "seriesid": list(FLOW_SERIES.values()),
                "startyear": str(start),
                "endyear": str(end),
            }
            _fetch(BLS_API, path, json.dumps(query).encode())
            if json.loads(path.read_text())["status"] != "REQUEST_SUCCEEDED":
                path.unlink()
                msg = f"the BLS API refused the request for {start}-{end}"
                raise RuntimeError(msg)
    for series in FRED_SERIES:
        path = FLOWS_DIR / f"{series}.csv"
        if not path.exists():
            _fetch(FRED_CSV.format(series), path)
    for name, remote in CTV_FILES.items():
        path = CTV_DIR / name
        if not path.exists():
            url = f"https://raw.githubusercontent.com/CTVproject/Replication/{CTV_COMMIT}/{urllib.parse.quote(remote)}"
            _fetch(url, path)


def require(path: Path) -> Path:
    """Return ``path``, or raise with the command that recreates it."""
    if path.exists():
        return path
    if path == OCCUPATION_CSV:
        how = (
            "it is tracked under code/validation/data (see the README there); to remake it, "
            "open any www.bls.gov page in a browser, run BLS_EXTRACTION_JS of "
            "validation/upstream_flows.py in its console, and save the output there"
        )
    else:
        how = f"run `{REGENERATE}`"
    msg = f"{path} is missing: {how}"
    raise FileNotFoundError(msg)


# --- 1. aggregate flows ------------------------------------------------------------------------------


@functools.cache
def bls_series() -> dict[str, dict[tuple[int, int], float]]:
    """The BLS flow and level series by (year, month), thousands."""
    out: dict[str, dict[tuple[int, int], float]] = {}
    for name, _, _ in BLS_FILES:
        for series in json.loads(require(FLOWS_DIR / name).read_text())["Results"][
            "series"
        ]:
            values = out.setdefault(series["seriesID"], {})
            for obs in series["data"]:
                values[(int(obs["year"]), int(obs["period"][1:]))] = float(obs["value"])
    return out


@functools.cache
def fred_series(series: str) -> dict[tuple[int, int], float]:
    """A monthly FRED series by (year, month)."""
    with require(FLOWS_DIR / f"{series}.csv").open() as handle:
        rows = list(csv.reader(handle))[1:]
    return {
        (int(date[:4]), int(date[5:7])): float(value)
        for date, value in rows
        if value not in ("", ".")
    }


def months(start: int, end: int) -> list[tuple[int, int]]:
    return [(year, month) for year in range(start, end + 1) for month in range(1, 13)]


def previous(month: tuple[int, int]) -> tuple[int, int]:
    year, m = month
    return (year, m - 1) if m > 1 else (year - 1, 12)


@dataclass(frozen=True)
class AggregateFlows:
    """Monthly averages over a window of the BLS flow rates and the Shimer finding probability."""

    ue: float  # U-to-E flow over last month's unemployment level
    eu: float  # E-to-U flow over last month's employment level
    stock_gap: (
        float  # largest relative gap between a flow-implied and a published level
    )
    shimer: float  # 1 - (U_t - U<5wk_t)/U_{t-1}
    n_months: int


def aggregate_flows(start: int = 2010, end: int = 2019) -> AggregateFlows:
    """BLS flow rates and the Shimer finding probability, averaged over the months of ``start``-``end``.

    ``stock_gap`` checks the series identifiers: last month's employment must equal EE + EU + EN and
    last month's unemployment UE + UU + UN, up to the small margin BLS leaves for rotation and weights.
    """
    s = {key: bls_series()[sid] for key, sid in FLOW_SERIES.items()}
    window = months(start, end)
    e_prev = np.array([s["E"][previous(t)] for t in window])
    u_prev = np.array([s["U"][previous(t)] for t in window])
    flow = {
        key: np.array([s[key][t] for t in window])
        for key in ("EE", "UE", "EU", "UU", "EN", "UN")
    }
    implied_e = flow["EE"] + flow["EU"] + flow["EN"]
    implied_u = flow["UE"] + flow["UU"] + flow["UN"]
    gap = max(
        np.abs(implied_e / e_prev - 1).max(),
        np.abs(implied_u / u_prev - 1).max(),
    )
    unemployed, short = fred_series("UNEMPLOY"), fred_series("UEMPLT5")
    shimer = np.array(
        [1 - (unemployed[t] - short[t]) / unemployed[previous(t)] for t in window],
    )
    return AggregateFlows(
        ue=float(np.mean(flow["UE"] / u_prev)),
        eu=float(np.mean(flow["EU"] / e_prev)),
        stock_gap=float(gap),
        shimer=float(shimer.mean()),
        n_months=len(window),
    )


# --- 2. separations by group -------------------------------------------------------------------------


@functools.cache
def occupation_table() -> dict[tuple[int, str, str], tuple[float, float]]:
    """(year, table, row) to (total, less than five weeks), thousands, from the saved BLS rows."""
    out = {}
    with require(OCCUPATION_CSV).open() as handle:
        for row in csv.DictReader(line for line in handle if not line.startswith("#")):
            lt5 = float(row["value_lt5wk"]) if row["value_lt5wk"] else math.nan
            out[(int(row["year"]), row["table"], row["row"])] = (
                float(row["value_total"]),
                lt5,
            )
    return out


def group_sums(year: int) -> dict[str, tuple[float, float, float]]:
    """Employed, unemployed, and short-term unemployed of each group in ``year``, thousands."""
    t = occupation_table()
    out = {}
    for group, rows in (("cognitive", COGNITIVE_ROWS), ("other", OTHER_ROWS)):
        employed = sum(t[(year, "cpsaat11", r)][0] for r in rows)
        unemployed = sum(t[(year, "cpsaat32", r)][0] for r in rows)
        short = sum(t[(year, "cpsaat32", r)][1] for r in rows)
        out[group] = (employed, unemployed, short)
    return out


def subtotal_gap(years: tuple[int, ...] = (*OCCUPATION_YEARS, 2025)) -> float:
    """Largest gap, thousands, between a published subtotal and the sum of its leaf rows."""
    t = occupation_table()
    gaps = []
    for year in years:
        for table, column in (("cpsaat11", 0), ("cpsaat32", 0), ("cpsaat32", 1)):
            for sub, leaves in SUBTOTALS.items():
                gaps.append(
                    abs(
                        t[(year, table, sub)][column]
                        - sum(t[(year, table, r)][column] for r in leaves),
                    ),
                )
    return max(gaps)


@dataclass(frozen=True)
class GroupSeparations:
    """Monthly inflow rates into short-term unemployment by group of last job, pooled over years."""

    inflow: tuple[
        float,
        float,
    ]  # short-term unemployed over employed, (cognitive, other)
    ratio: float  # other over cognitive
    relatives: tuple[
        float,
        float,
    ]  # each group's rate over the employment-weighted mean
    finding_ratio: float  # short-term over all unemployed, other over cognitive


def group_separations(
    years: tuple[int, ...] = OCCUPATION_YEARS,
    share_C: float | None = None,
) -> GroupSeparations:
    """Separation proxies by group from the BLS occupation tables of ``years``.

    The relatives weight the two rates by ``share_C``, by default the CPS 2025 cognitive share the paper
    uses. ``finding_ratio`` is the steady-state finding rate (inflow over the unemployed stock) of the
    other group relative to the cognitive group.
    """
    share = cognitive_share() if share_C is None else share_C
    sums = {
        g: np.sum([group_sums(y)[g] for y in years], axis=0)
        for g in ("cognitive", "other")
    }
    inflow = (
        sums["cognitive"][2] / sums["cognitive"][0],
        sums["other"][2] / sums["other"][0],
    )
    finding = (
        sums["cognitive"][2] / sums["cognitive"][1],
        sums["other"][2] / sums["other"][1],
    )
    mean = share * inflow[0] + (1 - share) * inflow[1]
    return GroupSeparations(
        inflow=(float(inflow[0]), float(inflow[1])),
        ratio=float(inflow[1] / inflow[0]),
        relatives=(float(inflow[0] / mean), float(inflow[1] / mean)),
        finding_ratio=float(finding[1] / finding[0]),
    )


# --- 3. switching shares -----------------------------------------------------------------------------


def read_dta(path: Path) -> dict[str, np.ndarray]:
    """Read the columns of a little-endian Stata 118 file (numeric and fixed-width string types)."""
    raw = path.read_bytes()
    head = b"<stata_dta><header><release>118</release><byteorder>LSF</byteorder><K>"
    if not raw.startswith(head):
        msg = f"{path} is not a little-endian Stata 118 file"
        raise ValueError(msg)
    n_vars = int.from_bytes(raw[len(head) : len(head) + 2], "little")
    at = len(head) + 2 + len(b"</K><N>")
    n_obs = int.from_bytes(raw[at : at + 8], "little")
    map_at = raw.index(b"<map>", at) + len(b"<map>")
    offsets = [int(x) for x in np.frombuffer(raw, dtype="<u8", count=14, offset=map_at)]
    for index, tag in ((2, b"<variable_types>"), (3, b"<varnames>"), (9, b"<data>")):
        if raw[offsets[index] : offsets[index] + len(tag)] != tag:
            msg = f"{path}: map entry {index} does not point at {tag.decode()}"
            raise ValueError(
                msg,
            )
    codes = np.frombuffer(
        raw,
        dtype="<u2",
        count=n_vars,
        offset=offsets[2] + len(b"<variable_types>"),
    )
    names_at = offsets[3] + len(b"<varnames>")
    names = [
        raw[names_at + 129 * i : names_at + 129 * (i + 1)].split(b"\0", 1)[0].decode()
        for i in range(n_vars)
    ]
    fields = []
    for name, code in zip(names, codes.tolist(), strict=True):
        if code in _DTA_NUMERIC:
            fields.append((name, _DTA_NUMERIC[code]))
        elif 1 <= code <= 2045:
            fields.append((name, f"S{code}"))
        else:
            msg = f"{path}: variable {name} has unsupported Stata type {code}"
            raise ValueError(
                msg,
            )
    table = np.frombuffer(
        raw,
        dtype=np.dtype(fields),
        count=n_obs,
        offset=offsets[9] + len(b"<data>"),
    )
    return {name: table[name].copy() for name in names}


def stata_present(column: np.ndarray) -> np.ndarray:
    """True where a numeric Stata column holds a value rather than a missing code."""
    return column < _DTA_MISSING[column.dtype.str.replace("|", "")]


def read_xlsx_matrix(path: Path) -> np.ndarray:
    """The numeric cells of the first worksheet of an xlsx file, as a dense matrix."""
    with zipfile.ZipFile(path) as book:
        sheet = ET.fromstring(book.read("xl/worksheets/sheet1.xml"))
    cells = {}
    for cell in sheet.iterfind("m:sheetData/m:row/m:c", _XLSX_NS):
        if cell.get("t") not in (None, "n"):
            msg = f"{path}: cell {cell.get('r')} is not numeric"
            raise ValueError(msg)
        ref = cell.get("r")
        value = cell.find("m:v", _XLSX_NS)
        if ref is None or value is None or value.text is None:
            msg = f"{path}: a cell lacks its reference or value"
            raise ValueError(msg)
        letters = ref.rstrip("0123456789")
        column = 0
        for letter in letters:
            column = 26 * column + ord(letter) - ord("A") + 1
        cells[(int(ref[len(letters) :]) - 1, column - 1)] = float(value.text)
    out = np.full((max(r for r, _ in cells) + 1, max(c for _, c in cells) + 1), np.nan)
    for (r, c), value in cells.items():
        out[r, c] = value
    if np.isnan(out).any():
        msg = f"{path} has empty cells"
        raise ValueError(msg)
    return out


@functools.cache
def ctv_excerpt() -> dict[str, np.ndarray]:
    return read_dta(require(CTV_DIR / "cps_excerpt_ctv.dta"))


@functools.cache
def ctv_degarbling() -> np.ndarray:
    """Inverse of the 22-occupation miscoding matrix, the matrix their paper corrects mobility with."""
    return read_xlsx_matrix(require(CTV_DIR / "Gammainv_mm_c_v2_REFERENCE.xlsx"))


def major_group(occ2010: np.ndarray, map_residual: bool = False) -> np.ndarray:
    """Index into SOC_CODES of each occ2010 code, -1 where the CTV ranges assign none."""
    out = np.full(occ2010.shape, -1)
    for index, (low, high, _) in enumerate(CTV_MAJOR_GROUPS):
        out[(occ2010 >= low) & (occ2010 <= high)] = index
    if map_residual:
        for code, soc in CTV_RESIDUAL_CODES.items():
            out[occ2010 == code] = int(np.flatnonzero(soc == SOC_CODES)[0])
    return out


def ctv_flows(window: tuple[int, int], map_residual: bool = False) -> np.ndarray:
    """Weighted job-finder flows among the 22 major groups, origin in rows, for origin months in ``window``."""
    d = ctv_excerpt()
    origin = major_group(d["occ2010"], map_residual)
    destination = major_group(d["next_occ2010"], map_residual)
    weight = d["lnkfw1mwt"]
    keep = (
        (d["year"] >= window[0])
        & (d["year"] <= window[1])
        & (origin >= 0)
        & (destination >= 0)
        & stata_present(d["occ2010"])
        & stata_present(d["next_occ2010"])
        & stata_present(weight)
    )
    flows = np.zeros((SOC_CODES.size, SOC_CODES.size))
    np.add.at(flows, (origin[keep], destination[keep]), weight[keep])
    return flows


def switching_shares(
    flows: np.ndarray,
    keep: np.ndarray | None = None,
) -> tuple[float, float, float]:
    """Shares of job finders who change group: from cognitive, from other, and pooled."""
    k = np.ones(SOC_CODES.size, dtype=bool) if keep is None else keep
    c, n = COGNITIVE & k, ~COGNITIVE & k
    cc, cn = flows[np.ix_(c, c)].sum(), flows[np.ix_(c, n)].sum()
    nc, nn = flows[np.ix_(n, c)].sum(), flows[np.ix_(n, n)].sum()
    return (
        float(cn / (cc + cn)),
        float(nc / (nc + nn)),
        float((cn + nc) / (cc + cn + nc + nn)),
    )


def ctv_switching(
    window: tuple[int, int] = (2010, 2019),
    *,
    correct: bool = True,
    drop_farming: bool = True,
    map_residual: bool = False,
) -> tuple[float, float, float]:
    """Group-switching shares of CPS job finders, corrected for occupation coding errors as CTV do.

    Their code observes the flow matrix M garbled at both ends, as G' M G, and recovers it as
    Ginv' (G' M G) Ginv (Supplementary Appendix A; ``corr_mat`` in step2_2 of their package). With
    ``drop_farming`` the sample and the corrected matrix exclude farming, fishing and forestry, the
    condition their CPS code maintains (``occ00!=45 & next_occ00!=45``).
    """
    flows = ctv_flows(window, map_residual)
    keep = ~FARMING if drop_farming else None
    if drop_farming:
        flows[FARMING, :] = 0.0
        flows[:, FARMING] = 0.0
    if correct:
        g_inv = ctv_degarbling()
        flows = g_inv.T @ flows @ g_inv
    return switching_shares(flows, keep)


def search_discount(cognitive_out: float, other_out: float) -> float:
    """mu-bar from Equation (35), the square root of the product of the two switching odds."""
    return math.sqrt(cognitive_out / (1 - cognitive_out) * other_out / (1 - other_out))


# --- report ------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Row:
    task: str
    quantity: str
    paper: float
    public: float
    source: str


def comparisons() -> list[Row]:
    """Every paper value beside its public cross-reference."""
    agg = aggregate_flows()
    eu_c, eu_n = IPUMS_EU_HAZARDS["2010-19"]
    share = cognitive_share()
    paper_rel = separation_relatives(share)
    sep = group_separations()
    sw = SWITCHING["CPS 2010-19"]["switch_share"], SWITCHING["CPS 2010-19"]["pooled"]
    sw_long = (
        SWITCHING["CPS 1976-2021"]["switch_share"],
        SWITCHING["CPS 1976-2021"]["pooled"],
    )
    ctv = ctv_switching()
    ctv_long = ctv_switching((1976, 2021))
    ctv_resid = ctv_switching(map_residual=True)
    ctv_raw = ctv_switching(correct=False)
    bls = "BLS flows 2010-19"
    occ = "BLS Tables 32/11, 2011-19"
    cps = "CTV CPS excerpt, corrected"
    return [
        Row("1", "U-to-E rate, monthly", EXPLORER_UE["all"], agg.ue, bls),
        Row("1", "E-to-U rate, monthly, pct", 100 * EXPLORER_EU_ALL, 100 * agg.eu, bls),
        Row(
            "1",
            "Shimer finding probability",
            EXPLORER_UE["all"],
            agg.shimer,
            "FRED UNEMPLOY, UEMPLT5 2010-19",
        ),
        Row(
            "2",
            "separation, cognitive, pct",
            100 * eu_c,
            100 * sep.inflow[0],
            occ + " (<5 wk / E)",
        ),
        Row(
            "2",
            "separation, other, pct",
            100 * eu_n,
            100 * sep.inflow[1],
            occ + " (<5 wk / E)",
        ),
        Row("2", "separation ratio, other/cognitive", eu_n / eu_c, sep.ratio, occ),
        Row(
            "2",
            "relative separation, cognitive",
            paper_rel[0],
            sep.relatives[0],
            occ + ", CPS 2025 weights",
        ),
        Row(
            "2",
            "relative separation, other",
            paper_rel[1],
            sep.relatives[1],
            occ + ", CPS 2025 weights",
        ),
        Row(
            "2",
            "U-to-E ratio, other/cognitive",
            EXPLORER_UE["other"] / EXPLORER_UE["cognitive"],
            sep.finding_ratio,
            occ + " (<5 wk / U)",
        ),
        Row(
            "3",
            "switch share from cognitive, pct",
            100 * sw[0][0],
            100 * ctv[0],
            cps + " 2010-19",
        ),
        Row(
            "3",
            "switch share from other, pct",
            100 * sw[0][1],
            100 * ctv[1],
            cps + " 2010-19",
        ),
        Row(
            "3",
            "switch share pooled, pct",
            100 * sw[1],
            100 * ctv[2],
            cps + " 2010-19",
        ),
        Row(
            "3",
            "search discount mu-bar",
            search_discount(*sw[0]),
            search_discount(ctv[0], ctv[1]),
            cps + " 2010-19",
        ),
        Row(
            "3",
            "pooled, residual codes mapped, pct",
            100 * sw[1],
            100 * ctv_resid[2],
            cps + " 2010-19",
        ),
        Row(
            "3",
            "pooled, uncorrected, pct",
            100 * sw[1],
            100 * ctv_raw[2],
            "CTV CPS excerpt, raw 2010-19",
        ),
        Row(
            "3",
            "switch share from cognitive, pct",
            100 * sw_long[0][0],
            100 * ctv_long[0],
            cps + " 1976-2021",
        ),
        Row(
            "3",
            "switch share from other, pct",
            100 * sw_long[0][1],
            100 * ctv_long[1],
            cps + " 1976-2021",
        ),
        Row(
            "3",
            "switch share pooled, pct",
            100 * sw_long[1],
            100 * ctv_long[2],
            cps + " 1976-2021",
        ),
    ]


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    download_missing()
    require(OCCUPATION_CSV)
    agg = aggregate_flows()
    log.info(
        "BLS flows: %d months, flow-implied levels within %.3f%% of published levels",
        agg.n_months,
        100 * agg.stock_gap,
    )
    log.info(
        "BLS occupation rows: subtotals within %.0f thousand of their leaves",
        subtotal_gap(),
    )
    log.info("")
    log.info(
        "%-4s %-38s %10s %10s %8s  %s",
        "task",
        "quantity",
        "paper",
        "public",
        "gap",
        "public source",
    )
    for row in comparisons():
        log.info(
            "%-4s %-38s %10.4f %10.4f %+8.4f  %s",
            row.task,
            row.quantity,
            row.paper,
            row.public,
            row.public - row.paper,
            row.source,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
