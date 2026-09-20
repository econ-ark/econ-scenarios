"""Evaluate a reading set against every transcribed target."""

import math

from .model import READINGS, Model, report, steady_state_report
from .targets import EXTRA, QUALITATIVE, all_targets, matches

INF = float("inf")


def case_specs(readings):
    fn14_theta = (
        0.50
        if readings.get("fn14_theta", READINGS["fn14_theta"]) == "extreme"
        else 0.25
    )
    return {
        "modest": ("modest", {}),
        "substantial": ("substantial", {}),
        "extreme": ("extreme", {}),
        "sub_eps1": ("substantial", {"eps": 1.0}),
        "sub_eps6": ("substantial", {"eps": 6.0}),
        "sub_epsinf": ("substantial", {"eps": INF}),
        "ext_eps1": ("extreme", {"eps": 1.0}),
        "ext_eps6": ("extreme", {"eps": 6.0}),
        "ext_epsinf": ("extreme", {"eps": INF}),
        "sub_xi075": ("substantial", {"xi": 0.75}),
        "sub_xi09": ("substantial", {"xi": 0.9}),
        "ext_xi0": ("extreme", {"xi": 0.0}),
        "ext_xi075": ("extreme", {"xi": 0.75}),
        "ext_xi09": ("extreme", {"xi": 0.9}),
        "fn14": (
            "substantial",
            {"psi": 0.9, "rho": 0.0, "mu": 0.04, "eps": 1.0, "thetaH": fn14_theta},
        ),
    }


def noai_report(model):
    p, ss = model.p, model.ss
    zero = [
        "gdp",
        "avg_wage",
        "wC",
        "wN",
        "capital",
        "labor_income",
        "wagebill_C",
        "capital_income",
        "cog_emp",
        "tfp",
        "ideas",
    ]
    rep = dict.fromkeys(zero, 0.0)
    k = round((p["t_2030"] - p["t0"]) * 12)
    rep.update(
        gdp_index=100.0 * math.exp((p["g"] + p["n"]) * k / 12.0),
        gdp_growth=100.0 * (p["g"] + p["n"]),
        net_return=100.0 * (p["rbar"] - p["delta"]),
        labor_share=100.0 * p["sL0"],
        capital_share=100.0 * (1.0 - p["sL0"]),
        u_C=100.0 * ss["uC_rate"],
        u_all=100.0 * p["Ubar"],
        tfp_growth=100.0 * p["gA"],
        ideas_growth=100.0 * p["g"],
    )
    return rep


def run_cases(readings):
    reps = {}
    for case, (scen, ov) in case_specs(readings).items():
        mod = Model(scen, ov, readings)
        mod.simulate()
        reps[case] = report(mod)
    base = Model("substantial", {}, readings)
    reps["ss"] = steady_state_report(base)
    reps["noai"] = noai_report(base)
    return reps


def _scored(reps, case, key, printed, where, tid=None):
    """One printed target against the reading set's value for it."""
    val = reps[case][key]
    row = {
        "case": case,
        "key": key,
        "printed": printed,
        "value": val,
        "hit": matches(val, printed),
        "where": where,
    }
    return row if tid is None else {"tid": tid, **row}


def evaluate(readings):
    """Return (rows, qual, extra, reps). rows: list of dicts per counted target."""
    reps = run_cases(readings)
    rows = [
        _scored(reps, case, key, printed, where, tid)
        for tid, case, key, printed, where in all_targets()
    ]
    qual = []
    for case, key, claim, pred, where in QUALITATIVE:
        val = reps[case][key]
        qual.append(
            {
                "case": case,
                "key": key,
                "claim": claim,
                "value": val,
                "hit": bool(pred(val)),
                "where": where,
            },
        )
    extra = [
        _scored(reps, case, key, printed, where) for case, key, printed, where in EXTRA
    ]
    return rows, qual, extra, reps
