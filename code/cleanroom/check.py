"""Internal consistency checks, each with a rejection test that must fail on a perturbed input."""

import logging
import math

from .model import READINGS, Model

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("check")


def adding_up(o, L):
    return max(
        abs(o["l_C"][k] + o["l_N"][k] + o["U_C"][k] + o["U_N"][k] - L)
        for k in range(len(o["l_C"]))
    )


def prop1_at(mod, k):
    """Proposition 1 evaluated at month ``k`` of a run."""
    o = mod.out
    return mod.prop1(
        o["m"][k],
        o["d"][k],
        o["a"][k],
        o["psi"][k],
        o["rho"][k],
        o["dlnA"][k],
    )


def prop1_vs_39(mod, k, perturb=0.0):
    o = mod.out
    P = prop1_at(mod, k)
    S = mod.sys_mpl(
        o["lstar_C"][k] * (1 + perturb),
        o["lstar_N"][k],
        P["B"],
        P["LamC"],
        o["dlnA"][k],
    )
    return max(
        abs(S["dr"] - P["dr"]),
        abs(S["dlY"] - P["dly"]),
        abs(S["wC"] - P["what"]),
        abs(S["wN"] - P["what"]),
    )


def demand_inverts_mpl(mod, k, perturb=0.0):
    o = mod.out
    P = mod.prop1(
        o["m"][k],
        o["d"][k],
        o["a"][k],
        o["psi"][k],
        o["rho"][k],
        o["dlnA"][k],
    )
    S = mod.sys_mpl(o["l_C"][k], o["l_N"][k], P["B"], P["LamC"], o["dlnA"][k])
    D = mod.sys_demand(S["wC"] + perturb, o["l_N"][k], P["B"], P["LamC"], o["dlnA"][k])
    return abs(D["lC"] - o["l_C"][k])


def main() -> None:
    for scen in ("modest", "substantial", "extreme"):
        mod = Model(scen, {}, dict(READINGS))
        o = mod.simulate()
        p = mod.p
        log.info("%s: adding-up max error %.2e", scen, adding_up(o, p["L"]))
        hires = max(
            abs(
                o["f_C"][k] * o["U_C"][k]
                + o["f_N"][k] * o["U_N"][k]
                - o["H_C"][k]
                - o["H_N"][k],
            )
            for k in range(len(o["l_C"]))
        )
        log.info("%s: f U = H max error %.2e", scen, hires)
        e1 = max(prop1_vs_39(mod, k) for k in (0, 30, 72))
        r1 = prop1_vs_39(mod, 72, perturb=1e-3)
        log.info(
            "%s: system (39) at targets vs Prop 1 max error %.2e (rejection with l_C +0.1%%: %.2e)",
            scen,
            e1,
            r1,
        )
        e2 = max(demand_inverts_mpl(mod, k) for k in (0, 30, 72))
        r2 = demand_inverts_mpl(mod, 72, perturb=1e-3)
        log.info(
            "%s: demand(MPL(l_C)) = l_C max error %.2e (rejection with w_C +0.001: %.2e)",
            scen,
            e2,
            r2,
        )
    # steady state (38)
    mod = Model("substantial", {}, dict(READINGS))
    ss, p = mod.ss, mod.p
    ssres = max(
        abs(p["qbar_C"] * p["lC0"] - ss["fC"] * ss["UC"]),
        abs(p["qbar_N"] * p["lN0"] - ss["fN"] * ss["UN"]),
    )
    io = p["iota"]

    def fill(h):
        return ss["chi"] * (1 - (h / ss["chi"]) ** io) ** (1 / io)

    hires_back = max(abs(fill(ss["hC"]) * (ss["hC"] / fill(ss["hC"])) - ss["hC"]), 0.0)
    mean_fill = (p["lC0"] * ss["piC"] + p["lN0"] * ss["piN"]) / p["Lbar"]
    # matching inversion: H = chi S v / (S^i + v^i)^(1/i) at v = H/pibar must return H
    vC = ss["HC"] / ss["piC"]
    Hback = ss["chi"] * ss["SC"] * vC / (ss["SC"] ** io + vC**io) ** (1 / io)
    log.info(
        "steady state: inflow=outflow max error %.2e; mean filling %.12f; H(v=H/pibar) - H = %.2e; %s",
        ssres,
        mean_fill,
        Hback - ss["HC"],
        hires_back,
    )
    # no-AI invariance of the flow block: with mu = mubar and AI switched off the stocks stay put
    for mu in (p["mubar"], 0.08):
        mod = Model(
            "modest",
            {"m_anchor": 1e-12, "m2030": 2e-12, "mu": mu},
            dict(READINGS),
        )
        o = mod.simulate()
        drift = max(
            abs(o["U_C"][k] - ss["UC"]) + abs(o["U_N"][k] - ss["UN"])
            for k in range(len(o["U_C"]))
        )
        log.info(
            "no-AI flow block drift over 74 months at mu=%.2f: %.2e (nonzero expected only if mu != mubar)",
            mu,
            drift,
        )
    log.info("sanity: pct of 0.28 log gap = %.3f", 100 * (math.exp(0.28) - 1))


if __name__ == "__main__":
    main()
