"""Recompute three calibration inputs of Korinek et al. (2026) from public BLS data.

Section 3.2 of the paper takes three numbers from U.S. labor-market data. The first is the
elasticity of the JOLTS quits rate to the CPS job-finding rate over 2001-19, printed as 0.53
and rounded to 0.55 for the calibration. The second is the monthly job-finding rate of
22 percent, which comes from IPUMS-CPS matched files for 2010-19 and enters the quit-rate
arithmetic 0.219 x 3.84/96.16 = 0.875 percent. The third, in footnote 9, is the vacancy
filling rate: the daily model of Davis, Faberman and Haltiwanger (2013) applied to JOLTS hires
and openings of 2010-19 gives 4.0 percent per working day, a mean duration of 26 working days,
and a share of 0.65 filled within the month.

The paper cites the FRED copies of the series (JTSQUR, UNEMPLOY, UEMPLT5), retrieved on
19 August 2026. FRED republishes the BLS series one for one, so this module first tries the
FRED CSV endpoint and, when that endpoint refuses scripted access, falls back to the public
BLS API (version 1, no key) for the same series. Each download is kept after first use.

IPUMS microdata are not available here, so the 22 percent is cross-checked against the
duration-based finding rate of Shimer (2012) built from UNEMPLOY and UEMPLT5. That is a
different estimator: it counts every exit from unemployment, including exits from the labor
force, where the matched files count transitions into employment only, so it is expected to
lie above 0.22.

Run from ``code/`` with ``uv run python -m validation.upstream_fred``.
"""

from __future__ import annotations

import datetime
import functools
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .download import fetch

log = logging.getLogger("upstream_fred")

ROOT = Path(__file__).resolve().parents[2]
FRED_DIR = ROOT / "sources" / "upstream" / "fred"
BLS_DIR = ROOT / "sources" / "upstream" / "bls"

FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={}"
BLS_URL = "https://api.bls.gov/publicAPI/v1/timeseries/data/"
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
FRED_TIMEOUT = 20.0
BLS_TIMEOUT = 60.0
# The BLS version-1 API returns at most ten years per request.
BLS_CHUNKS = ((2000, 2009), (2010, 2019), (2020, 2020))

# FRED identifier and the BLS series it republishes.
SERIES = {
    "JTSQUR": "JTS000000000000000QUR",  # JOLTS quits rate, total nonfarm, SA, percent
    "UNEMPLOY": "LNS13000000",  # CPS unemployment level, SA, thousands
    "UEMPLT5": "LNS13008396",  # CPS unemployed less than 5 weeks, SA, thousands
    "JTSHIL": "JTS000000000000000HIL",  # JOLTS hires level, total nonfarm, SA, thousands
    "JTSJOL": "JTS000000000000000JOL",  # JOLTS job openings level, total nonfarm, SA, thousands
    "JTSLDR": "JTS000000000000000LDR",  # JOLTS layoffs and discharges rate, SA, percent
}

# Working days per month in the daily model (Davis et al. 2013, Section IV.B).
TAU = 26
# Shimer's (2012) scaling of short-term unemployment after the 1994 CPS redesign.
SHIMER_REDESIGN = 1.1

Series = dict[int, float]


def month(year: int, mon: int) -> int:
    """Encode a calendar month as a single integer, twelve per year."""
    return 12 * year + mon - 1


def month_range(start: tuple[int, int], end: tuple[int, int]) -> np.ndarray:
    """Return the encoded months from ``start`` to ``end``, both included."""
    return np.arange(month(*start), month(*end) + 1)


def month_label(k: int) -> str:
    """Return an encoded month as YYYY-MM."""
    return f"{k // 12}-{k % 12 + 1:02d}"


def parse_fred_csv(text: str) -> Series:
    """Parse a fredgraph.csv file into encoded month and value, skipping missing entries."""
    out: Series = {}
    for line in text.strip().splitlines()[1:]:
        date, value = line.split(",")
        if value.strip() in {"", "."}:
            continue
        year, mon, _ = date.split("-")
        out[month(int(year), int(mon))] = float(value)
    return out


def fetch_fred(fred_id: str) -> str:
    """Download one series from the FRED CSV endpoint and return the CSV text."""
    text = fetch(
        FRED_URL.format(fred_id),
        agent=USER_AGENT,
        timeout=FRED_TIMEOUT,
    ).decode()
    if not text.startswith(("observation_date", "DATE")):
        msg = f"FRED returned something other than a CSV for {fred_id}: {text[:80]!r}"
        raise ValueError(
            msg,
        )
    return text


def fetch_bls(fred_ids: list[str]) -> dict[str, Series]:
    """Download the BLS originals of the given FRED series over 2000-2020 through the public API."""
    out: dict[str, Series] = {fred_id: {} for fred_id in fred_ids}
    by_bls = {SERIES[fred_id]: fred_id for fred_id in fred_ids}
    for first, last in BLS_CHUNKS:
        body = json.dumps(
            {"seriesid": list(by_bls), "startyear": str(first), "endyear": str(last)},
        ).encode()
        payload = json.loads(
            fetch(
                BLS_URL,
                agent=USER_AGENT,
                timeout=BLS_TIMEOUT,
                payload=body,
                content_type="application/json",
            ),
        )
        if payload.get("status") != "REQUEST_SUCCEEDED":
            msg = f"BLS API refused {first}-{last}: {payload.get('message')}"
            raise RuntimeError(
                msg,
            )
        for series in payload["Results"]["series"]:
            target = out[by_bls[series["seriesID"]]]
            for obs in series["data"]:
                if obs["period"].startswith("M") and obs["period"] != "M13":
                    target[month(int(obs["year"]), int(obs["period"][1:]))] = float(
                        obs["value"],
                    )
    return out


def fred_path(fred_id: str) -> Path:
    """Return where the FRED CSV of a series is cached."""
    return FRED_DIR / f"{fred_id}.csv"


def bls_path(fred_id: str) -> Path:
    """Return where the BLS-API copy of a series is cached, named by its FRED identifier."""
    return BLS_DIR / f"{fred_id}.json"


def ensure_data() -> None:
    """Download every series that is not yet cached, trying FRED first and the BLS API second.

    FRED is tried one series at a time. At its first refusal the remaining series come from the
    BLS API in three requests. Each BLS cache file records the URL, the BLS identifier and the
    retrieval date alongside the observations.
    """
    missing = [
        f for f in SERIES if not fred_path(f).exists() and not bls_path(f).exists()
    ]
    while missing:
        fred_id = missing[0]
        try:
            text = fetch_fred(fred_id)
        except (OSError, ValueError) as err:
            log.warning(
                "FRED refused %s (%s); fetching %s from the BLS API",
                fred_id,
                err,
                ", ".join(missing),
            )
            break
        FRED_DIR.mkdir(parents=True, exist_ok=True)
        fred_path(fred_id).write_text(text)
        log.info("Downloaded %s from %s", fred_id, FRED_URL.format(fred_id))
        missing.pop(0)
    if not missing:
        return
    BLS_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    for fred_id, data in fetch_bls(missing).items():
        record = {
            "fred_id": fred_id,
            "bls_id": SERIES[fred_id],
            "source": BLS_URL,
            "retrieved": today,
            "data": {month_label(k): v for k, v in sorted(data.items())},
        }
        bls_path(fred_id).write_text(json.dumps(record, indent=1))
        log.info("Downloaded %s (BLS %s) from %s", fred_id, SERIES[fred_id], BLS_URL)


@functools.cache
def load(fred_id: str) -> Series:
    """Return one series as encoded month and value, downloading it if it is not cached.

    The result is memoized because several of ``main``'s targets read the same series, and no
    caller mutates the series it gets back.
    """
    ensure_data()
    if fred_path(fred_id).exists():
        return parse_fred_csv(fred_path(fred_id).read_text())
    record = json.loads(bls_path(fred_id).read_text())
    return {
        month(*map(int, key.split("-"))): value for key, value in record["data"].items()
    }


def provenance() -> list[str]:
    """Describe where each cached series came from, for the log."""
    lines = []
    for fred_id in SERIES:
        if fred_path(fred_id).exists():
            lines.append(f"{fred_id}: {FRED_URL.format(fred_id)}")
        else:
            record = json.loads(bls_path(fred_id).read_text())
            lines.append(
                f"{fred_id}: BLS {record['bls_id']} via {record['source']}, retrieved {record['retrieved']}",
            )
    return lines


def rounds_to(value: float, published: float, decimals: int) -> bool:
    """Say whether ``value`` lies within half a unit of the last printed place of ``published``."""
    return abs(value - published) <= 0.5 * 10.0**-decimals + 1e-12


# Target 1: the elasticity of quits to the job-finding rate (Section 3.2).


@dataclass(frozen=True)
class QuitSpec:
    """One way of estimating the elasticity of the quits rate to the job-finding rate.

    ``dating`` is "forward" when the finding rate of month t uses the flow from t to t+1, as in
    Shimer (2012), F_t = 1 - (U_{t+1} - U^s_{t+1}) / U_t, and "backward" when it uses the flow
    into month t. ``short_scale`` multiplies short-term unemployment (1.1 is Shimer's
    correction for the 1994 redesign). ``rate`` is "hazard" for -ln(1 - F_t) or "probability"
    for F_t. ``freq`` averages both series to months ("M"), quarters ("Q") or years ("A")
    before the log-log regression, which optionally carries a linear trend.
    """

    dating: str = "forward"
    short_scale: float = 1.0
    rate: str = "hazard"
    freq: str = "M"
    trend: bool = False
    start: tuple[int, int] = (2001, 1)
    end: tuple[int, int] = (2019, 12)

    @property
    def label(self) -> str:
        """Return a short description of the specification."""
        window = f"{month_label(month(*self.start))}..{month_label(month(*self.end))}"
        trend = "+trend" if self.trend else ""
        return f"{self.dating} x{self.short_scale:g} {self.rate} {self.freq}{trend} {window}"


def finding_probability(
    months: np.ndarray,
    dating: str = "forward",
    short_scale: float = 1.0,
) -> np.ndarray:
    """Return the monthly job-finding probability of Shimer (2012) from UNEMPLOY and UEMPLT5."""
    unemployed, short = load("UNEMPLOY"), load("UEMPLT5")
    shift = {"forward": 0, "backward": -1}[dating]
    now = months + shift
    return np.array(
        [
            1.0 - (unemployed[k + 1] - short_scale * short[k + 1]) / unemployed[k]
            for k in now
        ],
    )


def average_by(values: np.ndarray, months: np.ndarray, freq: str) -> np.ndarray:
    """Average a monthly series to months, quarters, or calendar years."""
    width = {"M": 1, "Q": 3, "A": 12}[freq]
    _, group = np.unique(months // width, return_inverse=True)
    return np.bincount(group, weights=values) / np.bincount(group)


def ols_slope(y: np.ndarray, x: np.ndarray, trend: bool) -> float:
    """Return the OLS coefficient on ``x`` in a regression of ``y`` on a constant, ``x``, and an optional trend."""
    columns = [np.ones_like(x), x]
    if trend:
        columns.append(np.arange(x.size, dtype=float))
    beta = np.linalg.lstsq(np.column_stack(columns), y, rcond=None)[0]
    return float(beta[1])


def quit_elasticity(spec: QuitSpec) -> float:
    """Estimate the elasticity of the JOLTS quits rate to the finding rate under one specification."""
    months = month_range(spec.start, spec.end)
    quits_series = load("JTSQUR")
    quits = np.array([quits_series[k] for k in months])
    finding = finding_probability(months, spec.dating, spec.short_scale)
    if spec.rate == "hazard":
        finding = -np.log1p(-finding)
    q, f = average_by(quits, months, spec.freq), average_by(finding, months, spec.freq)
    return ols_slope(np.log(q), np.log(f), spec.trend)


def quit_grid() -> list[tuple[QuitSpec, float]]:
    """Estimate the elasticity over every specification tried, in a fixed order."""
    specs = [
        QuitSpec(dating=d, short_scale=s, rate=r, freq=fr, trend=t, start=st)
        for st in ((2001, 1), (2000, 12))
        for d in ("forward", "backward")
        for s in (1.0, SHIMER_REDESIGN)
        for r in ("hazard", "probability")
        for fr in ("M", "Q", "A")
        for t in (False, True)
    ]
    return [(spec, quit_elasticity(spec)) for spec in specs]


# Target 2: the monthly job-finding rate and the quit-rate arithmetic (Section 3.2).


def shimer_finding_rate(short_scale: float = 1.0) -> dict[str, float]:
    """Return the 2010-19 mean of Shimer's monthly finding probability and hazard.

    This is a cross-check on the paper's 22 percent from IPUMS-CPS matched files, computed with
    a different estimator (see the module docstring).
    """
    prob = finding_probability(
        month_range((2010, 1), (2019, 12)),
        "forward",
        short_scale,
    )
    return {
        "probability": float(prob.mean()),
        "hazard": float((-np.log1p(-prob)).mean()),
    }


def implied_quit_rate(
    finding: float = 0.219,
    pool: float = 3.84,
    employed: float = 96.16,
) -> float:
    """Return the monthly quit rate, in percent of employment, at which hires from the pool equal quits."""
    return 100.0 * finding * pool / employed


# Target 3: the vacancy filling rate of footnote 9.


def dfh_month(
    v_prev: float,
    v_end: float,
    hires: float,
    lapse: float,
    tau: int = TAU,
) -> tuple[float, float]:
    """Solve the daily model of Davis et al. (2013, Equations (3) and (4)) for one month.

    Given the openings stock at the end of the previous month and of this month, the month's
    hires and the daily lapse rate, return the daily filling rate f and the daily flow of new
    vacancies. With a = (1 - f)(1 - lapse), Equation (3) gives the flow in closed form for each
    f, and bisection then solves Equation (4), monthly hires, for f.
    """
    days = np.arange(1, tau + 1)

    def hires_gap(f: float) -> tuple[float, float]:
        a = (1.0 - f) * (1.0 - lapse)
        weights = a ** (days - 1)
        flow = (v_end - a**tau * v_prev) / weights.sum()
        return f * v_prev * weights.sum() + f * flow * (
            (tau - days) * weights
        ).sum() - hires, flow

    lo, hi = 1e-9, 0.999
    if not hires_gap(lo)[0] < 0.0 < hires_gap(hi)[0]:
        msg = "the daily filling rate is not bracketed"
        raise ValueError(msg)
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if hires_gap(mid)[0] > 0.0:
            hi = mid
        else:
            lo = mid
    f = 0.5 * (lo + hi)
    return f, hires_gap(f)[1]


def dfh_filling(
    lapse: str = "layoffs",
    start: tuple[int, int] = (2010, 1),
    end: tuple[int, int] = (2019, 12),
) -> dict[str, float]:
    """Apply the daily model month by month to JOLTS 2010-19 and summarize, as in footnote 9.

    Davis et al. (2013) set the daily lapse rate from the monthly layoff rate; ``lapse`` is
    "layoffs" for the JOLTS layoffs and discharges rate spread over 26 working days, or "zero".
    Each month's openings at the end of the previous month, openings at the end of the month
    and hires give one daily filling rate f_t. The summary is the mean of f_t, the mean vacancy
    duration as the mean of 1/f_t (Davis et al. define duration as 1/f_t), and the share of a
    vacancy open at the start of a month that is filled within it, 1 - (1 - mean f)^26.
    """
    openings, hires, layoffs = load("JTSJOL"), load("JTSHIL"), load("JTSLDR")
    months = month_range(start, end)
    rates = []
    for k in months:
        daily_lapse = layoffs[k] / 100.0 / TAU if lapse == "layoffs" else 0.0
        rates.append(dfh_month(openings[k - 1], openings[k], hires[k], daily_lapse)[0])
    f = np.array(rates)
    return {
        "fill_rate_pct": 100.0 * float(f.mean()),
        "duration_days": float(np.mean(1.0 / f)),
        "duration_of_mean_rate": float(1.0 / f.mean()),
        "share_within_month": float(1.0 - (1.0 - f.mean()) ** TAU),
    }


def dfh_steady_state(
    start: tuple[int, int] = (2010, 1),
    end: tuple[int, int] = (2019, 12),
) -> dict[str, float]:
    """Apply the steady-state shortcut of Davis et al. (2013, footnote 10) to the 2010-19 means.

    In a steady state the stock is constant within the month, so f = (H / v) / 26 whatever the
    lapse rate. This is the plausible wrong aggregation against which footnote 9 is checked.
    """
    months = month_range(start, end)
    openings, hires = load("JTSJOL"), load("JTSHIL")
    f = (
        np.mean([hires[k] for k in months])
        / np.mean([openings[k] for k in months])
        / TAU
    )
    return {
        "fill_rate_pct": 100.0 * float(f),
        "duration_days": float(1.0 / f),
        "share_within_month": float(1.0 - (1.0 - f) ** TAU),
    }


def main() -> int:
    """Log the recomputed value of each target next to the published one."""
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    ensure_data()
    log.info("Data sources:")
    for line in provenance():
        log.info("  %s", line)

    log.info("")
    log.info(
        "Target 1: elasticity of JOLTS quits to the CPS finding rate, published 0.53 (Section 3.2)",
    )
    for spec, estimate in quit_grid():
        mark = "  <- rounds to 0.53" if rounds_to(estimate, 0.53, 2) else ""
        log.info("  %-44s %.4f%s", spec.label, estimate, mark)

    log.info("")
    log.info(
        "Target 2: monthly finding rate, published 0.22 from IPUMS-CPS matched files 2010-19",
    )
    for scale in (1.0, SHIMER_REDESIGN):
        rate = shimer_finding_rate(scale)
        log.info(
            "  Shimer estimator, short-term x%g: probability %.4f, hazard %.4f",
            scale,
            rate["probability"],
            rate["hazard"],
        )
    quit_rate = implied_quit_rate()
    log.info(
        "  0.219 x 3.84 / 96.16 = %.4f percent a month (published 0.875), x12 = %.4f a year (published 0.105)",
        quit_rate,
        12 * quit_rate / 100,
    )

    log.info("")
    log.info(
        "Target 3: vacancy filling (footnote 9), published 4.0 pct a day, 26 days, 0.65 within the month",
    )
    for lapse in ("layoffs", "zero"):
        r = dfh_filling(lapse)
        log.info(
            "  monthly solution, lapse %-7s: f %.3f pct, mean(1/f) %.2f days, 1/mean(f) %.2f days, share %.4f",
            lapse,
            r["fill_rate_pct"],
            r["duration_days"],
            r["duration_of_mean_rate"],
            r["share_within_month"],
        )
    s = dfh_steady_state()
    log.info(
        "  steady state on means   : f %.3f pct, 1/f %.2f days, share %.4f",
        s["fill_rate_pct"],
        s["duration_days"],
        s["share_within_month"],
    )

    r = dfh_filling("layoffs")
    table = [
        (
            "quit elasticity",
            "0.53",
            f"{quit_elasticity(QuitSpec()):.4f}",
            "forward x1 hazard M 2001-19",
            rounds_to(quit_elasticity(QuitSpec()), 0.53, 2),
        ),
        (
            "quit elasticity",
            "0.53",
            f"{quit_elasticity(QuitSpec(dating='backward')):.4f}",
            "backward x1 hazard M 2001-19",
            rounds_to(quit_elasticity(QuitSpec(dating="backward")), 0.53, 2),
        ),
        (
            "quit elasticity",
            "0.53",
            f"{quit_elasticity(QuitSpec(short_scale=SHIMER_REDESIGN)):.4f}",
            "forward x1.1 hazard M 2001-19",
            rounds_to(quit_elasticity(QuitSpec(short_scale=SHIMER_REDESIGN)), 0.53, 2),
        ),
        (
            "finding rate",
            "0.22",
            f"{shimer_finding_rate()['probability']:.4f}",
            "Shimer probability 2010-19 (not IPUMS)",
            rounds_to(shimer_finding_rate()["probability"], 0.22, 2),
        ),
        (
            "quit rate, pct/month",
            "0.875",
            f"{quit_rate:.4f}",
            "0.219 x 3.84 / 96.16",
            rounds_to(quit_rate, 0.875, 3),
        ),
        (
            "fill rate, pct/day",
            "4.0",
            f"{r['fill_rate_pct']:.3f}",
            "DFH monthly, mean f_t",
            rounds_to(r["fill_rate_pct"], 4.0, 1),
        ),
        (
            "duration, days",
            "26",
            f"{r['duration_days']:.2f}",
            "DFH monthly, mean 1/f_t",
            rounds_to(r["duration_days"], 26, 0),
        ),
        (
            "share within month",
            "0.65",
            f"{r['share_within_month']:.4f}",
            "1 - (1 - mean f)^26",
            rounds_to(r["share_within_month"], 0.65, 2),
        ),
    ]
    log.info("")
    log.info(
        "%-22s %-10s %-12s %-40s %s",
        "target",
        "published",
        "recomputed",
        "specification",
        "reproduces",
    )
    for name, published, value, spec, ok in table:
        log.info(
            "%-22s %-10s %-12s %-40s %s",
            name,
            published,
            value,
            spec,
            "yes" if ok else "no",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
