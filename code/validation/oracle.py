"""The authors' public scenario explorer as an oracle for full monthly paths.

The explorer at https://www.anthropic.com/institute/econ-scenarios runs the model in the browser.
Its JavaScript carries no license, so none of its code is copied into this repository. Its
outputs are: ``explorer_record.json.gz`` beside this module holds the explorer's raw output for
every specification the tests and the validation figures ask for, keyed by a digest of the
specification, and ``run_explorer`` answers from it. The record was made by executing the
explorer's model chunk under node through ``oracle.mjs``, with the chunk downloaded from the
authors' site and checked against a pinned sha256. Set ``EXPLORER_RECORD=write`` to run the chunk
live and rewrite the record, which is the refresh after a redeploy of the explorer: find the
chunk that carries the model among the page's ``_next/static/chunks``, re-pin its URL and
sha256, and run the oracle tests with the variable set. Where the chunk is reachable, a test runs
it live and compares the result with the record, so a stale record cannot pass for a fresh one.

The explorer's monthly rows are mapped onto this package's series names by ``ROW_MAP``.
"""

from __future__ import annotations

import dataclasses
import functools
import gzip
import hashlib
import io
import json
import math
import os
import subprocess
import urllib.error
from pathlib import Path

import numpy as np
from econ_scenarios import Answers, Calibration, Scenario

from .download import BROWSER_AGENT, fetch_to

REPO = Path(__file__).resolve().parents[2]
CHUNK_URL = "https://www.anthropic.com/_next/static/chunks/0obtknnye5e24.js"
CHUNK_SHA256 = "0a75763f2ca4479bd88b240a7264307802b2ea6829d8db0c8efb5f515b8920f6"
CHUNK_PATH = REPO / "sources" / "explorer-2026-09-10" / "chunks" / "0obtknnye5e24.js"
RUNNER = Path(__file__).resolve().parent / "oracle.mjs"
RECORD = Path(__file__).resolve().parent / "explorer_record.json.gz"
RECORDING = os.environ.get("EXPLORER_RECORD", "").lower() == "write"

# The explorer's scenario keys, and its names for the data-source and reporting options.
KEYS = {"modest": "conservative", "substantial": "central", "extreme": "fast"}
SHARES = {"CPS 2025": "cps2025", "OEWS 2021": "oews2021"}
HAZARDS = {"2010-19": "w1019", "2015-19 and 2022-24": "recent", "1994-2024": "pooled"}
SEPARATIONS = {"by group": "byGroup", "common": "common"}
TFP = {"base_weight": "baseWeight", "dual": "dual"}
MATRICES = {"CPS 2010-19": "cps1019", "CPS 1976-2021": "cps7621"}

# series name -> function of one explorer row
ROW_MAP = {
    "t": lambda r: r["t"],
    "m": lambda r: r["x"]["m"],
    "d": lambda r: r["x"]["d"],
    "a": lambda r: r["x"]["a"],
    "psi": lambda r: r["x"]["psi"],
    "dlnA": lambda r: r["dlnA"],
    "dg": lambda r: r["dg"],
    "pot_dlnr": lambda r: r["xr"],
    "pot_lnW": lambda r: r["lnW"],
    "pot_lnSL": lambda r: r["lnSL"],
    "pot_lnYL": lambda r: r["lnYL"],
    "pot_lnK": lambda r: r["lnK"],
    "lnTFP": lambda r: r["lnTFP"],
    "shift_N": lambda r: r["ltilde"][1],
    "target_C": lambda r: r["tgt"][0],
    "target_N": lambda r: r["tgt"][1],
    "target_C_next": lambda r: r["tgtNext"][0],
    "target_N_next": lambda r: r["tgtNext"][1],
    "ell_C": lambda r: r["ell"][0],
    "ell_N": lambda r: r["ell"][1],
    "U_C": lambda r: r["U"][0],
    "U_N": lambda r: r["U"][1],
    "overhang_C": lambda r: r["G"][0],
    "overhang_N": lambda r: r["G"][1],
    "shortfall_N": lambda r: r["B"][1],
    "q_C": lambda r: r["q"][0],
    "q_N": lambda r: r["q"][1],
    "N_C": lambda r: r["NC"],
    "lnW_C_clear": lambda r: r["wcClear_act"],
    "wage_gap": lambda r: r["g"],
    "lnW_C": lambda r: r["wC_act"],
    "ell_C_demand": lambda r: r["ellD"],
    "excess_C": lambda r: r["E"],
    "demand_gap_C": lambda r: r["Z"],
    "D_C": lambda r: r["D"][0],
    "v_C": lambda r: r["v"][0],
    "v_N": lambda r: r["v"][1],
    "S_C": lambda r: r["S"][0],
    "S_N": lambda r: r["S"][1],
    "H_C": lambda r: r["H"][0],
    "H_N": lambda r: r["H"][1],
    "f_C": lambda r: r["f"][0],
    "f_N": lambda r: r["f"][1],
    "lnY": lambda r: r["lnY_act"],
    "lnW_N": lambda r: r["wN_act"],
    "lnMPL_C": lambda r: r["mplC_act"],
    "lnW_avg": lambda r: r["wavg_act"],
    "dlnr": lambda r: r["xr_act"],
    "lnK": lambda r: r["lnK_act"],
    "lnSL": lambda r: r["lnSL_act"],
    "net_return": lambda r: r["netReturn_act"],
    "U_total": lambda r: r["Ut"],
    "u_excess": lambda r: r["uAI"],
    "reallocation": lambda r: r["X"],
    "overhang_agg": lambda r: r["Gt"],
}


def fetch_chunk(path: Path = CHUNK_PATH) -> Path:
    """Download the explorer's model chunk if absent and verify its pinned sha256."""
    if not path.exists():
        try:
            fetch_to(CHUNK_URL, path, agent=BROWSER_AGENT, timeout=60)
        except urllib.error.HTTPError as e:
            msg = (
                f"{CHUNK_URL} answered {e.code}: the explorer was redeployed. The tests read "
                f"{RECORD.name}; to refresh it, find the model chunk among the page's "
                "_next/static/chunks (it carries the string 0.624), re-pin CHUNK_URL and "
                "CHUNK_SHA256, and run the oracle tests with EXPLORER_RECORD=write."
            )
            raise RuntimeError(msg) from e
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != CHUNK_SHA256:
        msg = (
            f"{path} has sha256 {digest}, expected {CHUNK_SHA256}: the explorer was redeployed. "
            "Find the model chunk again by grepping the page's chunks for 0.624, and re-pin."
        )
        raise RuntimeError(
            msg,
        )
    return path


def key(spec: dict) -> str:
    """The record's key for a specification: a digest of its canonical JSON."""
    return hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()[:16]


@functools.cache
def record() -> dict[str, dict]:
    """The recorded explorer outputs by key; empty where the record file is absent."""
    if not RECORD.exists():
        return {}
    with gzip.open(RECORD, "rt", encoding="utf-8") as f:
        return json.load(f)


def save_record(entries: dict[str, dict]) -> None:
    """Write the record deterministically: sorted keys, compact separators, no gzip timestamp,
    so that re-recording an unchanged explorer leaves the file byte-identical.
    """
    text = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    buffer = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buffer, mtime=0) as f:
        f.write(text)
    RECORD.write_bytes(buffer.getvalue())


def run_live(spec: dict) -> dict:
    """Execute the explorer's chunk under node on ``spec`` and return its raw output."""
    chunk = fetch_chunk()
    result = subprocess.run(
        ["node", str(RUNNER), str(chunk), json.dumps(spec)],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def explorer_choices(cal: Calibration, matrix: str | None = None) -> dict:
    """The explorer's data-source and reporting options that correspond to ``cal``.

    The explorer builds the cognitive share and the separation relatives from its data sources,
    so a calibration that overrides either one cannot be sent to it.
    """
    if cal.share_C_override is not None or cal.sep_rel_override is not None:
        msg = "the explorer cannot take a cognitive share or separation relatives off its data sources"
        raise ValueError(
            msg,
        )
    choices = {
        "shares": SHARES[cal.shares],
        "hazards": HAZARDS[cal.hazards],
        "sepRates": SEPARATIONS[cal.separations],
        "tfpExact": TFP[cal.tfp_form],
    }
    if matrix is not None:
        choices["matrix"] = MATRICES[matrix]
    return choices


def explorer_params(scenario: Scenario, cal: Calibration) -> dict:
    """Translate a scenario and calibration into the explorer's parameter overrides."""
    psi_ceiling = scenario.psi if scenario.psi_ceiling is None else scenario.psi_ceiling
    return {
        "mAnchor": cal.m_anchor,
        "m2030": scenario.m_2030,
        "mCeil": cal.m_ceiling,
        "dAnchor": cal.d_anchor,
        "d2030": scenario.d_2030,
        "dCeil": cal.d_ceiling,
        "aAnchor": scenario.a_anchor,
        "aSlope": scenario.g_a,
        "aCeil": 1e300 if scenario.a_ceiling is None else scenario.a_ceiling,
        "psiAnchor": scenario.psi,
        "psiFloor": scenario.psi_floor,
        "psiCeil": psi_ceiling,
        "psiKappa": scenario.psi_kappa,
        "rho": scenario.rho,
        "theta": scenario.theta_H,
        "gamma": cal.xi,
        "qBar": cal.q_bar_annual,
        "uBar": cal.U_bar,
        "muCN": scenario.mu,
        "muNC": scenario.mu,
        "muNormal": cal.mu_bar,
        "sigma": cal.sigma,
        "eps": None if math.isinf(cal.eps) else cal.eps,
        "rBar": cal.r_bar,
        "deltaK": cal.delta,
        "sL": cal.s_L,
        "lambda": cal.lam,
        "oneMinusPhi": cal.one_minus_phi,
        "gA": cal.g_A,
        "n": cal.n,
        "iotaR": cal.iota_R,
        "iota": cal.iota,
        "piBarMean": cal.pi_bar_mean,
        "qTshare": cal.q_T_share,
        "tAnchor": cal.t_anchor,
        "tRead": cal.t_read,
    }


def _run(spec: dict) -> dict:
    """The explorer's output for ``spec``: from the record, or live when recording or when the
    record has no entry, in which case the entry is added under ``EXPLORER_RECORD=write`` and
    the caller sees the same output either way.
    """
    k = key(spec)
    entries = record()
    if k in entries and not RECORDING:
        return entries[k]
    raw = run_live(spec)
    if RECORDING:
        entries[k] = raw
        save_record(entries)
    return raw


def explorer_spec(
    scenario: Scenario,
    cal: Calibration | None = None,
    horizon: float = 2030.0,
    level_form: str = "exact",
    matrix: str | None = None,
) -> dict:
    """The specification the explorer is run on for one scenario."""
    cal = Calibration() if cal is None else cal
    if cal.t0 != 2024.0 or cal.months_per_year != 12:
        msg = "the explorer runs monthly from t0 = 2024"
        raise ValueError(msg)
    return {
        "scenario": KEYS.get(scenario.name, "central"),
        "overrides": explorer_params(scenario, cal),
        "choices": explorer_choices(cal, matrix),
        "levelForm": "firstOrder" if level_form == "first_order" else "exact",
        "horizon": horizon,
    }


def run_explorer(
    scenario: Scenario,
    cal: Calibration | None = None,
    horizon: float = 2030.0,
    level_form: str = "exact",
    matrix: str | None = None,
) -> dict:
    """Run the explorer on one scenario; return its raw output (``rows``, ``ss``, ``diag``, ``muFitted``)."""
    return _run(explorer_spec(scenario, cal, horizon, level_form, matrix))


def quiz_spec(answers: Answers, horizon: float = 2035.0) -> dict:
    return {"quiz": dataclasses.asdict(answers), "horizon": horizon}


def run_explorer_quiz(answers: Answers, horizon: float = 2035.0) -> dict:
    """Run the explorer on a visitor's quiz answers, exactly as its page does."""
    return _run(quiz_spec(answers, horizon))


def explorer_series(raw: dict) -> dict[str, np.ndarray]:
    """The explorer's rows as arrays under this package's series names."""
    return {
        name: np.array([get(row) for row in raw["rows"]], dtype=float)
        for name, get in ROW_MAP.items()
    }
