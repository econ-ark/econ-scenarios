"""Export monthly paths to CSV, one file per case, at the baseline readings.

Rows run from t0 = 2024.0 (month 0) to 2030.0 (month 72); column is_2030 flags the 2030.0 row.
"""

import csv
import logging
import math
from pathlib import Path

from .model import READINGS, Model

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("export")

HERE = Path(__file__).resolve().parent
OUT = HERE / "csv"
INF = float("inf")

CASES = {
    "modest": ("modest", {}),
    "substantial": ("substantial", {}),
    "extreme": ("extreme", {}),
    "extreme_eps1": ("extreme", {"eps": 1.0}),
    "extreme_epsinf": ("extreme", {"eps": INF}),
    "extreme_xi0": ("extreme", {"xi": 0.0}),
    "extreme_xi0.9": ("extreme", {"xi": 0.9}),
}

HEADER = [
    "month",
    "time",
    "is_2030",
    "m_t",
    "d_t",
    "a_t",
    "psi_t",
    "rho",
    "dlnY",
    "Y_pct",
    "s_L",
    "s_L_target",
    "dlnK",
    "dlnr",
    "r_minus_delta_pct",
    "dlnw",
    "dlnw_C",
    "dlnw_c_C",
    "dlnMPL_C",
    "dlnw_N",
    "dlnwbar",
    "dlnA",
    "dg",
    "dlnTFP",
    "ltilde_N",
    "ltilde_C",
    "lstar_C",
    "lstar_N",
    "l_C",
    "l_N",
    "U_C",
    "U_N",
    "N_C",
    "ld_C",
    "E",
    "Z",
    "G_C",
    "B_N",
    "q_C",
    "q_N",
    "quits_C",
    "quits_N",
    "D_C",
    "v_C",
    "v_N",
    "S_C",
    "S_N",
    "H_C",
    "H_N",
    "f_C",
    "f_N",
    "u_C_pct",
    "u_N_pct",
    "u_pct",
    "u_x",
    "X",
    "G",
]


def rows_for(model):
    p, o = model.p, model.out
    k30 = round((p["t_2030"] - p["t0"]) * 12)
    rows = []
    for k in range(k30 + 1):
        lC, lN, UC, UN = o["l_C"][k], o["l_N"][k], o["U_C"][k], o["U_N"][k]
        wC, wN = o["dlnw_C"][k], o["dlnw_N"][k]
        wbar = math.log((math.exp(wC) * lC + math.exp(wN) * lN) / (lC + lN))
        X = (abs(o["l_C"][k + 1] - lC) + abs(o["l_N"][k + 1] - lN)) / (2.0 * p["L"])
        rows.append(
            [
                k,
                round(o["time"][k], 6),
                int(k == k30),
                o["m"][k],
                o["d"][k],
                o["a"][k],
                o["psi"][k],
                o["rho"][k],
                o["dlnY"][k],
                100.0 * (math.exp(o["dlnY"][k]) - 1.0),
                o["sL_actual"][k],
                o["sL_target"][k],
                o["dlnK"][k],
                o["dlnr"][k],
                100.0 * (p["rbar"] * math.exp(o["dlnr"][k]) - p["delta"]),
                o["dlnw_common"][k],
                wC,
                o["dlnwc_C"][k],
                o["dlnMPL_C"][k],
                wN,
                wbar,
                o["dlnA"][k],
                o["dg"][k],
                o["dlnTFP"][k],
                o["ltilde_N"][k],
                o["ltilde_C"][k],
                o["lstar_C"][k],
                o["lstar_N"][k],
                lC,
                lN,
                UC,
                UN,
                o["N_C"][k],
                o["ld_C"][k],
                o["E"][k],
                o["Z"][k],
                o["G_C"][k],
                o["B_N"][k],
                o["q_C"][k],
                o["q_N"][k],
                o["q_C"][k] * lC,
                o["q_N"][k] * lN,
                o["D_C"][k],
                o["v_C"][k],
                o["v_N"][k],
                o["S_C"][k],
                o["S_N"][k],
                o["H_C"][k],
                o["H_N"][k],
                o["f_C"][k],
                o["f_N"][k],
                100.0 * UC / (UC + lC),
                100.0 * UN / (UN + lN),
                100.0 * (UC + UN) / p["L"],
                (UC + UN - p["Ubar"]) / p["L"],
                X,
                o["G_C"][k] * lC / p["L"],
            ],
        )
    return rows


# Closest reading set found by ledger.py (see README.md); exported alongside the baseline.
BESTFIT = {"Ubar": "data", "q_convert": False}


def main() -> None:
    for folder, extra in ((OUT, {}), (HERE / "csv_bestfit", BESTFIT)):
        folder.mkdir(exist_ok=True)
        readings = dict(READINGS)
        readings.update(extra)
        for name, (scen, ov) in CASES.items():
            mod = Model(scen, ov, readings)
            mod.simulate()
            path = folder / f"{name}.csv"
            with path.open("w", newline="") as fh:
                wr = csv.writer(fh)
                wr.writerow(HEADER)
                for row in rows_for(mod):
                    wr.writerow(
                        [f"{v:.10g}" if isinstance(v, float) else v for v in row],
                    )
            log.info("wrote %s", path)


if __name__ == "__main__":
    main()
