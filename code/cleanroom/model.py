"""Clean-room monthly implementation of Korinek, Jones, Sacher, Cotter and McCrory (2026),
"Economic Scenarios for Transformative AI", from the paper text alone.

Equation numbers refer to the paper. All gaps are log gaps against the no-AI path unless
a name ends in ``_pct``. Wages inside the production solves are deflated by the ideas
stock A_t (Table A.1, note to system (39)); reported wage gaps add Delta ln A_t back.

Every point where the text underdetermines the computation is a key of ``READINGS``;
the default value is the baseline reading, and the ambiguity ledger in ``ledger.py``
lists the alternatives.
"""

import logging
import math

import numpy as np

log = logging.getLogger(__name__)

# ----------------------------------------------------------------------------------------
# Calibration as printed (Table 1, Table A.2, Section 2.3.2, Section 3)
# ----------------------------------------------------------------------------------------
BASE = {
    "sigma": 0.5,
    "sL0": 0.60,
    "c_share": 0.624,  # s_C,t0 / s_L,t0
    "eps": 3.0,
    "rbar": 0.115,
    "delta": 0.05,
    "t0": 2024.0,
    "t_anchor": 2026.5,
    "t_2030": 2030.0,
    "lam": 1.0,
    "one_minus_phiR": 2.86,
    "g": 0.0167,
    "n": 0.0033,
    "gA": 0.010,
    "L": 1.0,
    "Ubar": 0.038,
    "qbar_annual": 0.11,
    "qT_share": 0.55,
    "ratio_C": 0.69,
    "ratio_N": 1.52,
    "mubar": 0.17,
    "iota": 1.27,
    "pibar_mean": 0.65,
    "m_anchor": 0.14,
    "d_anchor": 0.10,
    "mbar": 0.624,
    "dbar": 1.0,
    "xi": 0.5,
}

SCENARIOS = {
    "modest": {
        "m2030": 0.2,
        "d2030": 0.2,
        "a_anchor": 0.30,
        "ga": 0.0,
        "psi": 0.50,
        "rho": 0.50,
        "mu": 0.17,
        "thetaH": 0.10,
    },
    "substantial": {
        "m2030": 0.3,
        "d2030": 0.4,
        "a_anchor": 0.35,
        "ga": 0.028,
        "psi": 0.75,
        "rho": 0.25,
        "mu": 0.08,
        "thetaH": 0.25,
    },
    "extreme": {
        "m2030": 0.5,
        "d2030": 0.6,
        "a_anchor": 0.45,
        "ga": 0.10,
        "psi": 0.90,
        "rho": 0.0,
        "mu": 0.04,
        "thetaH": 0.50,
    },
}

# Baseline readings. Each key is a ledger item; see ledger.py for quotes and alternatives.
READINGS = {
    "q_base": "annual/12",  # monthly aggregate quit fraction: 0.11/12 | "0.0092" | "cont_annual" | "compound_annual"
    "q_split": "ratio",  # "ratio" (0.69/1.52 x qbar) | "printed" (0.63%, 1.40%) | "ratio_data" (0.84/1.84 normalised)
    "q_convert": True,  # q = -ln(1 - qhat) (Appendix A) | False
    "theta_convert": False,  # thetaH -> -ln(1 - thetaH) | False
    "ga_sub": "printed",  # substantial slope 0.028 | "implied" = 0.10/3.5 so a_2030 = 0.45
    "growth_exact": False,  # g = 0.0167, n = 0.0033 | True: g = 0.01/0.6, n = 0.02 - g
    "mubar_mode": "printed",  # 0.17 | "sqrt_odds" sqrt(19/81*11/89) | "one_in_seven"
    "actual_rule": "R2",  # R2: MPL_C at realized l_C | R1: C instances priced at max(w_C, MPL_C)
    "A_in_39": "deflated",  # "deflated": labor demands use output net of A | "literal"
    "common_wage": "prop1",  # w_t in Eq (30): Prop 1 common wage | "wN_current": actual w_N at current employment
    "report_offset": 0,  # 2030.0 row is month 72 (and mid-2026 month 30) | -1 | +1
    "pct": "exp",  # pct above path = 100(exp(gap)-1) | "log" = 100 gap
    "ideas_growth": "log12",  # growth of ideas: 12-month log change | "instant" = g + Delta g_t
    "avg_wage": "level",  # employment-weighted level average | "log" (weighted log gaps)
    "labor_share": "price_index",  # s_L = 1 - B e^{(1-s)dlnr} | "paid" = paid wage bill / Y
    "uC_denom": "group_lf",  # U_C/(U_C + l_C) | "fixed" = U_C / (c_share * L)
    "tfp": "eq45",  # Eq (45) | "first_order" Eq (26)
    "ideas_update": "euler",  # monthly Euler step on Eq (42) | "closed" Eq (43)
    "gap_target": "t+1",  # Eq (28) against date-(t+1) target | "t"
    "wC_report": "paid",  # reported cognitive wage: paid sticky wage | "mpl"
    "fn14_theta": "substantial",  # footnote 14 posting speed: 0.25 | "extreme" 0.50
    "Ubar": "printed",  # 0.038 (Table 1) | "data" 0.0384 (Section 3.2 arithmetic, 1.76 + 2.08)
    "path_time": "start",  # month k evaluates paths at t0 + k/12 | "mid": t0 + (k + 1/2)/12
    "qT_share": "printed",  # 0.55 | "data" 0.53 (Section 3.2, before rounding)
    "a_origin": "anchor",  # a_t passes through the mid-2026 anchor | "t0": a_0 = anchor value at t0
    "transfer_basis": "t0",  # transfer arithmetic (Sec 4.3, fn 14): C employment vs l_C,t0 | "mid2026"
    # Added after unblinding (see README): where Appendix A's conversion enters Eq (27).
    "quit_order": "convert_then_split",  # split rates q^X, q^T | "split_then_convert": q = -ln(1 - qhat_t) monthly
}


def _bisect(fun, lo, hi, tol=1e-15, maxit=300):
    """Root of a function that is positive at lo and negative at hi (or vice versa)."""
    flo = fun(lo)
    fhi = fun(hi)
    if flo == 0.0:
        return lo
    if fhi == 0.0:
        return hi
    if np.sign(flo) == np.sign(fhi):
        msg = f"bisection bracket fails: f({lo})={flo}, f({hi})={fhi}"
        raise ValueError(msg)
    for _ in range(maxit):
        mid = 0.5 * (lo + hi)
        fm = fun(mid)
        if fm == 0.0 or (hi - lo) < tol:
            return mid
        if np.sign(fm) == np.sign(flo):
            lo, flo = mid, fm
        else:
            hi = mid
    return 0.5 * (lo + hi)


class Model:
    """One parameterisation (calibration + scenario + readings)."""

    def __init__(self, scenario, overrides=None, readings=None) -> None:
        self.p = dict(BASE)
        sc = dict(SCENARIOS[scenario]) if isinstance(scenario, str) else dict(scenario)
        self.p.update(sc)
        if overrides:
            self.p.update(overrides)
        self.r = dict(READINGS)
        if readings:
            self.r.update(readings)
        self.scenario_name = scenario if isinstance(scenario, str) else "custom"
        self._setup()

    # ------------------------------------------------------------------------------------
    def _setup(self) -> None:
        p, r = self.p, self.r
        if r["growth_exact"]:
            p["g"] = p["gA"] / p["sL0"]
            p["n"] = 0.02 - p["g"]
        if r["ga_sub"] == "implied" and self.scenario_name == "substantial":
            p["ga"] = 0.10 / 3.5
        if r["Ubar"] == "data":
            p["Ubar"] = 0.0384
        p["sK0"] = 1.0 - p["sL0"]
        p["sC0"] = p["sL0"] * p["c_share"]
        p["sN0"] = p["sL0"] * (1.0 - p["c_share"])
        p["Lbar"] = p["L"] - p["Ubar"]
        p["lC0"] = p["c_share"] * p["Lbar"]
        p["lN0"] = (1.0 - p["c_share"]) * p["Lbar"]
        # Logistic paths (8), slopes by (8'), through the mid-2026 anchor.
        span = p["t_2030"] - p["t_anchor"]
        for x, anchor, top in (
            ("m", p["m_anchor"], p["mbar"]),
            ("d", p["d_anchor"], p["dbar"]),
        ):
            v30 = p[f"{x}2030"]
            kappa = math.log((top - anchor) / anchor * v30 / (top - v30)) / span
            mid = p["t_anchor"] + math.log(top / anchor - 1.0) / kappa
            p[f"kappa_{x}"] = kappa
            p[f"tmid_{x}"] = mid
        # a_t = a0 + ga (t - t0), with a0 set so a(mid-2026) is the Table 1 anchor.
        p["a0"] = p["a_anchor"] - p["ga"] * (p["t_anchor"] - p["t0"])
        if r["a_origin"] == "t0":
            p["a0"] = p["a_anchor"]
        if r["qT_share"] == "data":
            p["qT_share"] = 0.53
        # mubar
        if r["mubar_mode"] == "sqrt_odds":
            p["mubar"] = math.sqrt((19 / 81) * (11 / 89))
        # thetaH conversion
        th = p["thetaH"]
        p["theta"] = -math.log(1.0 - th) if r["theta_convert"] else th
        p["xi_m"] = p["xi"] ** (1.0 / 12.0) if p["xi"] > 0 else 0.0
        self._steady_state()

    def _quit_rates(self):
        p, r = self.p, self.r
        base = r["q_base"]
        if base == "annual/12":
            qhat = p["qbar_annual"] / 12.0
        elif base == "0.0092":
            qhat = 0.0092
        elif base == "cont_annual":
            qhat = -math.log(1.0 - p["qbar_annual"]) / 12.0
        elif base == "compound_annual":
            qhat = 1.0 - (1.0 - p["qbar_annual"]) ** (1.0 / 12.0)
        elif base == "data":
            qhat = (
                0.219 * 0.0384 / 0.9616
            )  # Section 3.2, before rounding to 0.11 a year
        else:
            raise ValueError(base)
        split = r["q_split"]
        if split == "ratio":
            qC, qN = p["ratio_C"] * qhat, p["ratio_N"] * qhat
        elif split == "printed":
            qC, qN = 0.0063, 0.0140
        elif split == "ratio_data":
            agg = p["c_share"] * 0.84 + (1 - p["c_share"]) * 1.84
            qC, qN = 0.84 / agg * qhat, 1.84 / agg * qhat
        else:
            raise ValueError(split)
        p["qhat"], p["qhat_C"], p["qhat_N"] = qhat, qC, qN
        if r["q_convert"]:
            qC, qN = -math.log(1.0 - qC), -math.log(1.0 - qN)
        return qC, qN

    def _ss_given_mubar(self, mub):
        p = self.p
        qC, qN = p["qbar_C"], p["qbar_N"]
        HC, HN = qC * p["lC0"], qN * p["lN0"]
        target = HC / HN

        # h_C/h_N = U_C/U_N and H_o = k U_o S_o; ratio in r = U_C/U_N
        def fun(z):
            return z * (z + mub) / (mub * z + 1.0) - target

        z = _bisect(fun, 1e-9, 1e3)
        UN = p["Ubar"] / (1.0 + z)
        UC = p["Ubar"] - UN
        SC, SN = UC + mub * UN, mub * UC + UN
        hC, hN = HC / SC, HN / SN
        fC, fN = hC + mub * hN, mub * hC + hN
        switch = mub * (hN * UC + hC * UN) / (HC + HN)
        return {
            "UC": UC,
            "UN": UN,
            "SC": SC,
            "SN": SN,
            "HC": HC,
            "HN": HN,
            "hC": hC,
            "hN": hN,
            "fC": fC,
            "fN": fN,
            "switch": switch,
        }

    def _steady_state(self) -> None:
        p, r = self.p, self.r
        qC, qN = self._quit_rates()
        p["qbar_C"], p["qbar_N"] = qC, qN
        if r["mubar_mode"] == "one_in_seven":
            p["mubar"] = _bisect(
                lambda mu: self._ss_given_mubar(mu)["switch"] - 1.0 / 7.0,
                1e-4,
                1.0,
            )
        ss = self._ss_given_mubar(p["mubar"])
        io = p["iota"]

        def pibar(chi, h):
            return chi * (1.0 - (h / chi) ** io) ** (1.0 / io)

        def mean_fill(chi):
            return (
                p["lC0"] * pibar(chi, ss["hC"]) + p["lN0"] * pibar(chi, ss["hN"])
            ) / p["Lbar"]

        lo = max(ss["hC"], ss["hN"]) * (1 + 1e-12)
        chi = _bisect(lambda c: mean_fill(c) - p["pibar_mean"], lo, 50.0)
        ss["chi"] = chi
        ss["piC"], ss["piN"] = pibar(chi, ss["hC"]), pibar(chi, ss["hN"])
        ss["f_agg"] = (ss["HC"] + ss["HN"]) / p["Ubar"]
        ss["uC_rate"] = ss["UC"] / (ss["UC"] + p["lC0"])
        ss["uN_rate"] = ss["UN"] / (ss["UN"] + p["lN0"])
        self.ss = ss
        p["qX_C"], p["qT_C"] = (1 - p["qT_share"]) * qC, p["qT_share"] * qC
        p["qX_N"], p["qT_N"] = (1 - p["qT_share"]) * qN, p["qT_share"] * qN
        p["qhX_C"], p["qhT_C"] = (
            (1 - p["qT_share"]) * p["qhat_C"],
            p["qT_share"] * p["qhat_C"],
        )
        p["qhX_N"], p["qhT_N"] = (
            (1 - p["qT_share"]) * p["qhat_N"],
            p["qT_share"] * p["qhat_N"],
        )

    # ------------------------------------------------------------------------------------
    # Scenario paths (8)
    def paths(self, t):
        p = self.p
        m = p["mbar"] / (1.0 + math.exp(-p["kappa_m"] * (t - p["tmid_m"])))
        d = p["dbar"] / (1.0 + math.exp(-p["kappa_d"] * (t - p["tmid_d"])))
        a = p["a0"] + p["ga"] * (t - p["t0"])
        return m, d, a, p["psi"], p["rho"]

    def _blocks(self, m, d, a, psi, rho):
        """B_t (labor-share bracket), Lambda_C (surviving cognitive mass), ltilde_N (15)."""
        p = self.p
        k = 1.0 - p["sigma"]
        ea = math.exp(-k * a)
        shift = m * d * (1.0 - rho * psi - (1.0 - psi) * ea)
        B = p["sK0"] + p["sL0"] * psi * m * d * (ea - rho)
        LamC = p["c_share"] - shift
        ltN = -math.log(1.0 - shift)
        return B, LamC, ltN

    # Proposition 1 (target / full-employment economy)
    def prop1(self, m, d, a, psi, rho, dlnA):
        p = self.p
        _s, k, eps = p["sigma"], 1.0 - p["sigma"], p["eps"]
        B, LamC, ltN = self._blocks(m, d, a, psi, rho)

        def pieces(dr):
            sL = 1.0 - B * math.exp(k * dr)
            dlsL = math.log(sL / p["sL0"])
            what = (dlsL + ltN) / k  # deflated common wage
            dly = what + dlnA - dlsL
            dlK = math.log((1.0 - sL) / p["sK0"]) + dly - dr
            return sL, dlsL, what, dly, dlK

        if math.isinf(eps):
            dr = 0.0
        else:
            drmax = math.log(1.0 / B) / k
            dr = _bisect(lambda x: pieces(x)[4] - eps * x, -2.0, drmax - 1e-12)
        sL, _dlsL, what, dly, dlK = pieces(dr)
        return {
            "dr": dr,
            "sL": sL,
            "what": what,
            "dlw": what + dlnA,
            "dly": dly,
            "dlK": dlK,
            "ltN": ltN,
            "B": B,
            "LamC": LamC,
        }

    # System (39) at given employment: MPL prices
    def sys_mpl(self, lC, lN, B, LamC, dlnA):
        p = self.p
        s, k, eps = p["sigma"], 1.0 - p["sigma"], p["eps"]
        lamC = LamC / p["c_share"]
        xC, xN = lC / p["lC0"], lN / p["lN0"]
        D = p["sC0"] * lamC ** (1.0 / s) * xC ** (-k / s) + p["sN0"] * xN ** (-k / s)
        Aterm = dlnA if self.r["A_in_39"] == "deflated" else 0.0

        def y_of(dr):
            return (s / k) * math.log((1.0 - B * math.exp(k * dr)) / D)

        def kdem(dr):
            return math.log(B * math.exp(k * dr) / p["sK0"]) + y_of(dr) + Aterm - dr

        if math.isinf(eps):
            dr = 0.0
        else:
            drmax = math.log(1.0 / B) / k
            dr = _bisect(lambda x: kdem(x) - eps * x, -2.0, drmax - 1e-12)
        y = y_of(dr)
        wC = (math.log(lamC) + y - math.log(xC)) / s
        wN = (y - math.log(xN)) / s
        return {
            "dr": dr,
            "y": y,
            "wC": wC,
            "wN": wN,
            "dlK": kdem(dr),
            "sL": 1.0 - B * math.exp(k * dr),
            "dlY": y + Aterm,
        }

    # System (39) solved for l_C at a given deflated cognitive wage
    def sys_demand(self, wC, lN, B, LamC, dlnA):
        p = self.p
        s, k, eps = p["sigma"], 1.0 - p["sigma"], p["eps"]
        lamC = LamC / p["c_share"]
        xN = lN / p["lN0"]
        cterm = p["sC0"] * lamC * math.exp(k * wC)
        Aterm = dlnA if self.r["A_in_39"] == "deflated" else 0.0

        def parts(dr):
            rest = 1.0 - B * math.exp(k * dr) - cterm
            wN = math.log(rest / p["sN0"]) / k
            y = math.log(xN) + s * wN
            return wN, y

        def kdem(dr):
            _wN, y = parts(dr)
            return math.log(B * math.exp(k * dr) / p["sK0"]) + y + Aterm - dr

        if math.isinf(eps):
            dr = 0.0
        else:
            drmax = math.log((1.0 - cterm) / B) / k
            dr = _bisect(lambda x: kdem(x) - eps * x, -2.0, drmax - 1e-12)
        wN, y = parts(dr)
        lC = p["lC0"] * lamC * math.exp(y - s * wC)
        return {
            "dr": dr,
            "y": y,
            "wC": wC,
            "wN": wN,
            "lC": lC,
            "dlK": kdem(dr),
            "sL": 1.0 - B * math.exp(k * dr),
            "dlY": y + Aterm,
        }

    def tfp(self, m, d, a, dlnA):
        p = self.p
        k = 1.0 - p["sigma"]
        if self.r["tfp"] == "first_order":
            return p["sL0"] * (dlnA + m * d * a)
        inner = p["sK0"] + p["sL0"] * (
            1.0 - m * d * (1.0 - math.exp(-k * a))
        ) * math.exp(-k * dlnA)
        return -math.log(inner) / k

    # ------------------------------------------------------------------------------------
    def simulate(self, months=74):
        p, r, ss = self.p, self.r, self.ss
        K = months
        out = {name: np.full(K, np.nan) for name in COLUMNS}
        lC, lN = p["lC0"], p["lN0"]
        UC, UN = ss["UC"], ss["UN"]
        fC_prev, fN_prev = ss["fC"], ss["fN"]
        rel_prev = 0.0  # ln(w_C/w)_{t0-1} = 0
        dlnA = 0.0
        mu, theta = p["mu"], p["theta"]
        io, chi = p["iota"], ss["chi"]
        p["sigma"]
        dlnR_hist = []
        shift = 0.5 / 12.0 if r["path_time"] == "mid" else 0.0
        for kk in range(K):
            t = p["t0"] + kk / 12.0 + shift
            # 1. paths at t and t+1
            m, d, a, psi, rho = self.paths(t)
            m1, d1, a1, psi1, rho1 = self.paths(t + 1.0 / 12.0)
            # 2-3. capital market, wage, shares, targets (Prop 1)
            P = self.prop1(m, d, a, psi, rho, dlnA)
            _, _, ltN1 = self._blocks(m1, d1, a1, psi1, rho1)
            lNs, lNs1 = p["lN0"] * math.exp(P["ltN"]), p["lN0"] * math.exp(ltN1)
            lCs = p["lC0"] + p["lN0"] - lNs
            lCs1 = p["lC0"] + p["lN0"] - lNs1
            tfp = self.tfp(m, d, a, dlnA)
            # 4. gaps and cognitive wage
            lNg, lCg = (lNs1, lCs1) if r["gap_target"] == "t+1" else (lNs, lCs)
            BN = max(0.0, math.log(lNg) - math.log(lN))
            GC = max(0.0, math.log(lC) - math.log(lCg))
            NC = lC + max(0.0, UC - ss["UC"])
            clear = self.sys_mpl(NC, lN, P["B"], P["LamC"], dlnA)
            cur = self.sys_mpl(lC, lN, P["B"], P["LamC"], dlnA)
            wref = P["what"] if r["common_wage"] == "prop1" else cur["wN"]
            rel = p["xi_m"] * rel_prev + (1.0 - p["xi_m"]) * (clear["wC"] - wref)
            wC = wref + rel
            dem = self.sys_demand(wC, lN, P["B"], P["LamC"], dlnA)
            lCd = dem["lC"]
            E = max(0.0, lC - lCd)
            Z = max(0.0, lCd - lC)
            # 5. separations and openings
            if r["quit_order"] == "split_then_convert":
                qC = -math.log(1.0 - (p["qhX_C"] + p["qhT_C"] * fC_prev / ss["fC"]))
                qN = -math.log(1.0 - (p["qhX_N"] + p["qhT_N"] * fN_prev / ss["fN"]))
            else:
                qC = p["qX_C"] + p["qT_C"] * fC_prev / ss["fC"]
                qN = p["qX_N"] + p["qT_N"] * fN_prev / ss["fN"]
            DC = max(0.0, E - qC * lC)
            vC = (max(0.0, qC * lC - E) + theta * Z) / ss["piC"]
            vN = (qN + theta * BN) * lN / ss["piN"]
            # 6. matching
            SC, SN = UC + mu * UN, mu * UC + UN
            HC = chi * SC * vC / (SC**io + vC**io) ** (1.0 / io) if vC > 0 else 0.0
            HN = chi * SN * vN / (SN**io + vN**io) ** (1.0 / io) if vN > 0 else 0.0
            fC = HC / SC + mu * HN / SN
            fN = mu * HC / SC + HN / SN
            # 8. reporting: actual economy at realized employment
            if r["actual_rule"] == "R1" and lC > lCd:
                act = dem  # C output demand-determined at the sticky wage
            else:
                act = cur  # C priced at MPL at realized employment
            wC_rep = wC if r["wC_report"] == "paid" else cur["wC"]
            dlY = act["dlY"]
            # 7. stocks
            lC1 = (1.0 - qC) * lC - DC + HC
            lN1 = (1.0 - qN) * lN + HN
            UC1 = UC + qC * lC + DC - fC * UC
            UN1 = UN + qN * lN - fN * UN
            # record
            row = {
                "month": kk,
                "time": t,
                "m": m,
                "d": d,
                "a": a,
                "psi": psi,
                "rho": rho,
                "dlnA": dlnA,
                "dlnr_target": P["dr"],
                "sL_target": P["sL"],
                "dlnw_common": P["dlw"],
                "dlnYL_target": P["dly"],
                "dlnK_target": P["dlK"],
                "ltilde_N": P["ltN"],
                "ltilde_C": math.log(lCs / p["lC0"]),
                "lstar_C": lCs,
                "lstar_N": lNs,
                "dlnTFP": tfp,
                "G_C": GC,
                "B_N": BN,
                "N_C": NC,
                "dlnwc_C": clear["wC"] + dlnA,
                "dlnw_C": wC_rep + dlnA,
                "dlnw_C_paid": wC + dlnA,
                "dlnMPL_C": cur["wC"] + dlnA,
                "ld_C": lCd,
                "E": E,
                "Z": Z,
                "q_C": qC,
                "q_N": qN,
                "D_C": DC,
                "v_C": vC,
                "v_N": vN,
                "S_C": SC,
                "S_N": SN,
                "H_C": HC,
                "H_N": HN,
                "f_C": fC,
                "f_N": fN,
                "l_C": lC,
                "l_N": lN,
                "U_C": UC,
                "U_N": UN,
                "dlnY": dlY,
                "dlnw_N": act["wN"] + dlnA,
                "dlnr": act["dr"],
                "dlnK": act["dlK"],
                "sL_actual": act["sL"],
            }
            for key, val in row.items():
                out[key][kk] = val
            # 9. ideas
            dlnR = dlY
            dlnR_hist.append(dlnR)
            dg = p["g"] * (math.exp(p["lam"] * dlnR - p["one_minus_phiR"] * dlnA) - 1.0)
            out["dg"][kk] = dg
            if r["ideas_update"] == "euler":
                dlnA = dlnA + dg / 12.0
            else:
                dlnA = self._ideas_closed(np.array(dlnR_hist))
            # advance
            lC, lN, UC, UN = lC1, lN1, UC1, UN1
            fC_prev, fN_prev = fC, fN
            rel_prev = rel
        self.out = out
        return out

    def _ideas_closed(self, dlnR_hist):
        """Eq (43) with the integral by the rectangle rule over months (R piecewise constant)."""
        p = self.p
        c = p["one_minus_phiR"] * p["g"]
        h = 1.0 / 12.0
        nmon = len(dlnR_hist)
        tau = nmon * h
        s_mid = (np.arange(nmon) + 0.5) * h  # R constant within each month
        weights = np.exp(-c * (tau - s_mid)) * h
        integ = np.sum(weights * np.exp(p["lam"] * dlnR_hist))
        return math.log(math.exp(-c * tau) + c * integ) / p["one_minus_phiR"]


COLUMNS = [
    "month",
    "time",
    "m",
    "d",
    "a",
    "psi",
    "rho",
    "dlnA",
    "dg",
    "dlnr_target",
    "sL_target",
    "dlnw_common",
    "dlnYL_target",
    "dlnK_target",
    "ltilde_N",
    "ltilde_C",
    "lstar_C",
    "lstar_N",
    "dlnTFP",
    "G_C",
    "B_N",
    "N_C",
    "dlnwc_C",
    "dlnw_C",
    "dlnw_C_paid",
    "dlnMPL_C",
    "ld_C",
    "E",
    "Z",
    "q_C",
    "q_N",
    "D_C",
    "v_C",
    "v_N",
    "S_C",
    "S_N",
    "H_C",
    "H_N",
    "f_C",
    "f_N",
    "l_C",
    "l_N",
    "U_C",
    "U_N",
    "dlnY",
    "dlnw_N",
    "dlnr",
    "dlnK",
    "sL_actual",
]


def report(model, month=None):
    """Reported quantities at a month (default 2030.0 row), in the units of Table 3."""
    p, r, o = model.p, model.r, model.out
    k30 = round((p["t_2030"] - p["t0"]) * 12) + r["report_offset"]
    k26 = round((p["t_anchor"] - p["t0"]) * 12) + r["report_offset"]
    k = k30 if month is None else month
    pct = (
        (lambda x: 100.0 * (math.exp(x) - 1.0))
        if r["pct"] == "exp"
        else (lambda x: 100.0 * x)
    )
    lC, lN, UC, UN = o["l_C"][k], o["l_N"][k], o["U_C"][k], o["U_N"][k]
    wC, wN = o["dlnw_C"][k], o["dlnw_N"][k]
    wCp = o["dlnw_C_paid"][k]
    if r["avg_wage"] == "level":
        avg = (math.exp(wC) * lC + math.exp(wN) * lN) / (lC + lN)
        avg_gap = math.log(avg)
    else:
        avg_gap = (wC * lC + wN * lN) / (lC + lN)
    dlY = o["dlnY"][k]
    paid_bill = math.exp(wCp) * lC + math.exp(wN) * lN  # in units of no-AI wage x L
    labor_income_ratio = paid_bill / p["Lbar"]
    if r["labor_share"] == "price_index":
        sL = o["sL_actual"][k]
    else:
        sL = p["sL0"] * labor_income_ratio / math.exp(dlY)
    sK = 1.0 - sL
    dr, dK = o["dlnr"][k], o["dlnK"][k]

    def grow(x):
        return 100.0 * (o[x][k] - o[x][k - 12])

    uC = UC / (UC + lC) if r["uC_denom"] == "group_lf" else UC / (p["c_share"] * p["L"])
    uC26 = (
        o["U_C"][k26] / (o["U_C"][k26] + o["l_C"][k26])
        if r["uC_denom"] == "group_lf"
        else o["U_C"][k26] / (p["c_share"] * p["L"])
    )
    if r["ideas_growth"] == "log12":
        g_ideas = 100.0 * p["g"] + grow("dlnA")
    else:
        g_ideas = 100.0 * (p["g"] + o["dg"][k])
    wbC = math.exp(wCp) * lC / p["lC0"]
    wbN = math.exp(wN) * lN / p["lN0"]
    res = {
        "gdp": pct(dlY),
        "gdp_index": 100.0
        * math.exp((p["g"] + p["n"]) * (k / 12.0))
        * (1.0 + pct(dlY) / 100.0)
        if r["pct"] == "exp"
        else 100.0 * math.exp((p["g"] + p["n"]) * (k / 12.0) + dlY),
        "gdp_growth": 100.0 * (p["g"] + p["n"]) + grow("dlnY"),
        "avg_wage": pct(avg_gap),
        "wC": pct(wC),
        "wN": pct(wN),
        "net_return": 100.0 * (p["rbar"] * math.exp(dr) - p["delta"]),
        "capital": pct(dK),
        "labor_share": 100.0 * sL,
        "capital_share": 100.0 * sK,
        "labor_income": 100.0 * (labor_income_ratio - 1.0),
        "wagebill_C": 100.0 * (wbC - 1.0),
        "capital_income": pct(dr + dK),
        "cog_emp": 100.0 * (lC / o["l_C"][k26] - 1.0),
        "oth_emp": 100.0 * (lN / o["l_N"][k26] - 1.0),
        "u_C": 100.0 * uC,
        "u_C_mid2026": 100.0 * uC26,
        "u_all": 100.0 * (UC + UN) / p["L"],
        "tfp": pct(o["dlnTFP"][k]),
        "tfp_growth": 100.0 * p["gA"] + grow("dlnTFP"),
        "ideas": pct(o["dlnA"][k]),
        "ideas_growth": g_ideas,
        # derived text quantities
        "gdp_vs_mid2026": 100.0
        * (math.exp((p["g"] + p["n"]) * (k - k26) / 12.0 + dlY - o["dlnY"][k26]) - 1.0),
        "wC_level_vs_mid2026": 100.0
        * (math.exp(p["g"] * (k - k26) / 12.0 + wC - o["dlnw_C"][k26]) - 1.0),
        "labor_share_mid2026": 100.0 * o["sL_actual"][k26],
        "wagebill_N": 100.0 * (wbN - 1.0),
        "dlnR": dlY,
        "rental_target_pct": pct(o["dlnr_target"][k]),
        "wage_common_pct": pct(o["dlnw_common"][k]),
        "mda": o["m"][k] * o["d"][k] * o["a"][k],
    }
    res["share_shift"] = 100.0 * p["sL0"] - res["labor_share"]
    res["return_increase"] = 100.0 * (
        res["net_return"] / (100.0 * (p["rbar"] - p["delta"])) - 1.0
    )
    res["uC_increase"] = 100.0 * (res["u_C"] / res["u_C_mid2026"] - 1.0)
    # Section 2.1 holds A_t at its no-AI path: the level channel alone
    lvl = model.prop1(o["m"][k], o["d"][k], o["a"][k], o["psi"][k], o["rho"][k], 0.0)
    res["tfp_levelonly_log"] = model.tfp(o["m"][k], o["d"][k], o["a"][k], 0.0)
    res["rental_levelonly_pct"] = pct(lvl["dr"])
    res["wage_levelonly_pct"] = pct(lvl["dlw"])
    # redistribution arithmetic (Section 4.3 and footnote 14), in units of no-AI GDP
    cshare_bill = p["sL0"] * p["lC0"] / p["Lbar"]
    gain = math.exp(dlY) - 1.0
    wbC_transfer = (
        wbC if r["transfer_basis"] == "t0" else math.exp(wCp) * lC / o["l_C"][k26]
    )
    transfer = cshare_bill * (1.0 - wbC_transfer)
    res["labor_income_gdp_units"] = 100.0 * p["sL0"] * (labor_income_ratio - 1.0)
    res["transfer_share_of_gain"] = (
        100.0 * transfer / gain if gain != 0 else float("nan")
    )
    res["transfer_share_of_gdp"] = 100.0 * transfer / math.exp(dlY)
    res["gain_over_loss"] = gain / transfer if transfer != 0 else float("nan")
    res["net_gain_after_transfer"] = 100.0 * (gain - transfer)
    res["N_bill_gain_vs_C_loss"] = (
        (p["sL0"] * p["lN0"] / p["Lbar"] * (wbN - 1.0)) / transfer
        if transfer
        else float("nan")
    )
    # diagnostic only: the same transfer with cognitive employment measured against mid-2026
    wbC26 = math.exp(wCp) * lC / o["l_C"][k26]
    res["transfer_share_of_gain_mid2026basis"] = (
        100.0 * cshare_bill * (1.0 - wbC26) / gain if gain else float("nan")
    )
    res["gdp_gap_t0"] = pct(o["dlnY"][0])
    return res


def steady_state_report(model):
    p, ss = model.p, model.ss
    return {
        "qbar_C_pct": 100.0 * p["qhat_C"],
        "qbar_N_pct": 100.0 * p["qhat_N"],
        "f_agg": ss["f_agg"],
        "UC_pct": 100.0 * ss["UC"],
        "UN_pct": 100.0 * ss["UN"],
        "uC_rate": 100.0 * ss["uC_rate"],
        "uN_rate": 100.0 * ss["uN_rate"],
        "piC": ss["piC"],
        "piN": ss["piN"],
        "chi": ss["chi"],
        "switch_share": ss["switch"],
        "mubar": p["mubar"],
    }
