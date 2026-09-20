"""Ambiguity ledger: run every alternative reading one at a time against the baseline,
count targets that change status, then search combinations.

Writes ledger_results.json in the workspace.
"""

import itertools
import json
import logging
from pathlib import Path

from .compare import evaluate
from .model import READINGS

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("ledger")

HERE = Path(__file__).resolve().parent

# item: (alternatives, location and quote, chosen reading and why)
LEDGER = {
    "actual_rule": (
        ["R1"],
        "Table A.1 panel D, row (39): 'the price index, the two groups' labor demands, and the supply "
        "of capital at realized employment (l_C,t, l_N,t) ... the cognitive wage is the sticky wage "
        "w_C,t, or MPL_C,t where employment trails demand'; App. A step 8: 'Record the actual economy's "
        "GDP ... from the system (39) at realized employment, with the cognitive wage paid'",
        "R2: the actual economy is system (39) at realized employment with C priced at its MPL; the "
        "paid sticky wage is recorded separately. R1: C output is demand-determined at the sticky wage "
        "when employment exceeds demand (effective C employment min(l_C, l^d_C)).",
    ),
    "A_in_39": (
        ["literal"],
        "Table A.1 note to (39): 'and the wages deflated by A_t'; the labor-demand rows contain "
        "Delta ln(Y_t/Lbar) with no A term",
        "deflated: output in the labor-demand rows is net of Delta ln A (the only reading under which "
        "'at the targets it is Proposition 1' holds). literal: Delta ln Y including A.",
    ),
    "common_wage": (
        ["wN_current"],
        "Eq (30) and p. 19: 'This rigidity occurs relative to the common wage w_t'",
        "prop1: w_t is the full-employment common wage of Prop. 1 (Table A.1 panel B wage row). "
        "alt: the all-other wage at current employment.",
    ),
    "q_base": (
        ["0.0092", "cont_annual", "compound_annual", "data"],
        "App. A: 'Rates quoted as fractions per period are converted to continuously compounded rates. "
        "For example, a quit fraction qhat enters as q = -ln(1 - qhat).' Sec 3.2: 'We round it to 0.11 a "
        "year, or 0.92 percent a month'",
        "annual/12: qhat = 0.11/12 per month (the text's own 0.92), then converted. alts: 0.0092 as printed; "
        "-ln(0.89)/12; 1-(0.89)^(1/12); unrounded 0.219 x 3.84/96.16.",
    ),
    "q_split": (
        ["printed", "ratio_data"],
        "Table 1 D: 'qbar_C/qbar; qbar_N/qbar relative separation rates 0.69; 1.52'; Sec 2.3.2: "
        "'qbar_C = 0.63 and qbar_N = 1.40 percent a month'",
        "ratio: 0.69 and 1.52 times qbar. alts: 0.63% and 1.40% as printed; 0.84/1.84 renormalised.",
    ),
    "q_convert": (
        [False],
        "App. A: 'a quit fraction qhat enters as q = -ln(1 - qhat)'",
        "True: apply the conversion to the monthly quit fractions. alt: no conversion.",
    ),
    "theta_convert": (
        [True],
        "App. A conversion sentence vs Table 1 'theta^H posting speed, per month' and Sec 2.3.1 "
        "'post openings for a fraction theta^H of any shortfall per month'",
        "False: theta^H enters (32) as printed. alt: theta = -ln(1 - theta^H).",
    ),
    "ga_sub": (
        ["implied"],
        "Table 1 B: substantial g_a = 0.028 'which imply a_2030 = 0.30 / 0.45 / 0.80'",
        "printed 0.028 (a_2030 = 0.448). alt: 0.10/3.5 so a_2030 = 0.45 exactly.",
    ),
    "growth_exact": (
        [True],
        "Table 1 A: g = 0.0167, g_A = 0.010 = s_L g; n = 0.0033 'so that GDP grows at 2 percent'",
        "printed. alt: g = 0.01/0.6, n = 0.02 - g.",
    ),
    "mubar_mode": (
        ["sqrt_odds", "one_in_seven"],
        "Sec 3.2: 'mubar = sqrt(0.23 x 0.12) = 0.17'; Sec 2.3.2: 'the value at which the share of "
        "job-finders ... who change groups equals one in seven'",
        "printed 0.17. alts: sqrt(19/81 x 11/89) = 0.1703; fit to a 1/7 switching share.",
    ),
    "report_offset": (
        [-1, 1],
        "Table 3 note: 'at the start of 2030'; Table 1: 'date of the scenarios' 2030 values 2030.0'",
        "row 72 = 2030.0 on a grid t0 + k/12 with t0 = 2024.0 (mid-2026 = row 30). alts: +-1 month.",
    ),
    "path_time": (
        ["mid"],
        "App. A: 'The model is simulated on a monthly grid'",
        "start: month k evaluates the paths at t0 + k/12. alt: mid-month t0 + (k + 1/2)/12.",
    ),
    "pct": (
        ["log"],
        "Table 3 'pct. above the no-AI path'; Sec 4.3 '0.45 x 1.32 = 0.60'; Sec 2.2.1 'uplift reaches 0.28'",
        "exp: 100(exp(gap) - 1). alt: 100 x log gap.",
    ),
    "ideas_growth": (
        ["instant"],
        "Table 3 note: 'Growth rates are log changes over the twelve months to 2030'",
        "log12 for all growth rows. alt for the ideas row: instantaneous g + Delta g_t.",
    ),
    "avg_wage": (
        ["log"],
        "Table A.1 D: 'Average wage wbar_t = (w_C l_C + w_N l_N)/(l_C + l_N)'",
        "level average. alt: employment-weighted average of log gaps.",
    ),
    "labor_share": (
        ["paid"],
        "Table A.1 D row (39) lists s_L,t among the actual economy's unknowns; 'cognitive firms' "
        "profit (MPL_C - w_C) l_C'",
        "price_index: s_L = 1 - B e^{(1-sigma) dlnr} (= 1 - rK/Y). alt: paid wage bill / Y.",
    ),
    "uC_denom": (
        ["fixed"],
        "Fig. 4 'percent of the group's labor force'; Sec 2.3.2 '2.9 percent of the one group'",
        "U_C/(U_C + l_C). alt: U_C/(0.624 L).",
    ),
    "tfp": (
        ["first_order"],
        "App. C.4: 'Equation (45) is the definition of the measured TFP gap used in the simulations'",
        "Eq (45). alt: first-order Eq (26).",
    ),
    "ideas_update": (
        ["closed"],
        "App. A step 9: 'a step of length h = 1/12 on Equation (42)'; closed form (43)",
        "euler. alt: closed form (43), research input constant within the month.",
    ),
    "gap_target": (
        ["t"],
        "Eq (28): 'ln l*_{N,t+1} - ln l_N,t'",
        "date-(t+1) target as written. alt: date-t target.",
    ),
    "wC_report": (
        ["mpl"],
        "App. A step 8: 'with the cognitive wage paid'",
        "paid sticky wage. alt: MPL_C at realized employment.",
    ),
    "fn14_theta": (
        ["extreme"],
        "Footnote 14 lists psi, mu, rho at extreme values and eps = 1; theta^H unstated",
        "substantial theta^H = 0.25. alt: 0.50.",
    ),
    "Ubar": (
        ["data"],
        "Table 1 D: 'Ubar 0.038'; Sec 3.2: '0.219 x 3.84/96.16'; Sec 2.3.2: pools 1.76 + 2.08 = 3.84",
        "printed 0.038. alt: 0.0384.",
    ),
    "qT_share": (
        ["data"],
        "Sec 3.2: 'an elasticity of 0.53, which we round to 0.55'",
        "printed 0.55. alt: 0.53.",
    ),
    "transfer_basis": (
        ["mid2026"],
        "Fn 14: 'Holding cognitive occupations' income at its no-AI level would take a transfer "
        "equal to 84 percent of GDP gains'; Sec 4.3: '31 percent below its previous path as wages "
        "are 11.5 percent lower paid on 21.5 percent fewer jobs' (21.5 is the since-mid-2026 row)",
        "t0: cognitive wage bill exp(dlnw_C) l_C / l_C,t0, the Table 3 wage-bill row. alt: employment "
        "measured against mid-2026, as the Sec 4.3 sentence multiplies.",
    ),
    "a_origin": (
        ["t0"],
        "Eq (8): 'a_t = a_0 + g_a (t - t0)'; Table A.2: 'a_0 level of the gain at t0'; Table 1: 'a_t log "
        "gain per instance, mid-2026 anchor'",
        "anchor: a(2026.5) equals the Table 1 value, so a_2030 = 0.30/0.448/0.80. alt: a(t0) = Table 1 "
        "value.",
    ),
}


def status(rows):
    return {r["tid"]: (r["hit"], r["value"], r["printed"]) for r in rows}


def run_single(base_status, item, alt):
    readings = dict(READINGS)
    readings[item] = alt
    rows, _qual, _extra, _ = evaluate(readings)
    st = status(rows)
    gained = [t for t in st if st[t][0] and not base_status[t][0]]
    lost = [t for t in st if not st[t][0] and base_status[t][0]]
    return {
        "item": item,
        "alt": alt,
        "hits": sum(v[0] for v in st.values()),
        "gained": gained,
        "lost": lost,
        "values": {t: st[t][1] for t in gained + lost},
    }


def main() -> None:
    rows, _qual, _extra, _ = evaluate(dict(READINGS))
    base = status(rows)
    nbase = sum(v[0] for v in base.values())
    log.info("baseline %d / %d", nbase, len(base))
    singles = []
    for item, (alts, _, _) in LEDGER.items():
        for alt in alts:
            res = run_single(base, item, alt)
            singles.append(res)
            log.info(
                "%-14s %-16s hits %3d  +%-3d -%-3d changed %d",
                item,
                str(alt),
                res["hits"],
                len(res["gained"]),
                len(res["lost"]),
                len(res["gained"]) + len(res["lost"]),
            )
    # combination search over items whose alternative changes any status
    active = [(s["item"], s["alt"]) for s in singles if s["gained"] or s["lost"]]
    by_item = {}
    for item, alt in active:
        by_item.setdefault(item, []).append(alt)
    items = sorted(by_item)
    log.info("active items for combination search: %s", items)
    # greedy forward selection from baseline
    current = dict(READINGS)
    best = nbase
    improved = True
    path = []
    while improved:
        improved = False
        cand_best = None
        for item in items:
            for alt in [READINGS[item]] + by_item[item]:
                if current[item] == alt:
                    continue
                trial = dict(current)
                trial[item] = alt
                h = sum(r["hit"] for r in evaluate(trial)[0])
                if h > best and (cand_best is None or h > cand_best[0]):
                    cand_best = (h, item, alt)
        if cand_best:
            best, item, alt = cand_best
            current[item] = alt
            path.append((item, alt, best))
            improved = True
            log.info("greedy: set %s=%s -> %d", item, alt, best)
    # exhaustive search over alternatives that gain a target at a cost of at most MAXLOSS
    # (alternatives that lose dozens of targets on their own are rejected outright)
    maxloss = 12
    keep = {}
    for s in singles:
        if s["gained"] and len(s["lost"]) <= maxloss:
            keep.setdefault(s["item"], []).append(s["alt"])
    helpful = sorted(keep)
    log.info("exhaustive over helpful items: %s", {i: keep[i] for i in helpful})
    choices = [[READINGS[i]] + keep[i] for i in helpful]
    top = []
    for combo in itertools.product(*choices):
        trial = dict(READINGS)
        trial.update(dict(zip(helpful, combo, strict=False)))
        rws = evaluate(trial)[0]
        h = sum(r["hit"] for r in rws)
        top.append(
            (
                h,
                dict(zip(helpful, combo, strict=False)),
                [r["tid"] for r in rws if not r["hit"]],
            ),
        )
    top.sort(key=lambda x: -x[0])
    for h, combo, misses in top[:10]:
        log.info("combo %3d  %s  misses %s", h, combo, misses)
    out = {
        "baseline_hits": nbase,
        "n_targets": len(base),
        "singles": singles,
        "greedy": path,
        "exhaustive_items": helpful,
        "top": [{"hits": h, "combo": c, "misses": m} for h, c, m in top[:40]],
    }
    (HERE / "ledger_results.json").write_text(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
