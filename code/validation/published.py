"""The numbers Korinek et al. (2026) publish, and the model readout that reproduces each.

Every entry is a value the paper prints rounded to ``decimals`` places. A published number is
matched when the model's value rounds to it, that is when they differ by at most half a unit in
the last printed place. Such a match certifies only that band, which is why the oracle comparison
of full paths is the stronger instrument.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, replace

import numpy as np
from econ_scenarios import (
    EXTREME,
    MODEST,
    SUBSTANTIAL,
    Answers,
    Calibration,
    Scenario,
    Simulation,
    answers_to_scenario,
    fit_mu_bar,
    mu_from_switching_odds,
    readout,
    simulate,
    survey,
)
from econ_scenarios.paths import ScenarioPaths, logistic_slope
from econ_scenarios.production import tfp_base_weight

Runner = Callable[..., Simulation]
SCENARIOS3 = (MODEST, SUBSTANTIAL, EXTREME)

# Table 3: readout key, row label, (modest, substantial, extreme), decimals.
TABLE3 = (
    ("gdp", "GDP, pct. above the no-AI path", (1.6, 8.3, 32.4), 1),
    ("gdp_index", "GDP, index with 2024 = 100", (114.5, 122.1, 149.3), 1),
    ("gdp_growth", "GDP growth, pct. per year", (2.4, 5.4, 15.4), 1),
    ("wage_avg", "Average wage, pct. above the no-AI path", (0.7, 2.1, 9.7), 1),
    ("wage_C", "cognitive occupations, w_C", (0.4, -0.3, -11.5), 1),
    ("wage_N", "all other occupations, w_N", (1.1, 5.9, 33.6), 1),
    ("net_return", "Net return to capital, pct. per year", (6.6, 7.0, 8.3), 1),
    ("capital", "Capital stock, pct. above the no-AI path", (2.3, 13.8, 56.3), 1),
    ("labor_share", "Labor share, pct. of income", (59.4, 56.1, 45.2), 1),
    ("capital_share", "Capital share, pct. of income", (40.6, 43.9, 54.8), 1),
    ("labor_income", "Labor income, pct. above the no-AI path", (0.6, 1.4, 0.5), 1),
    ("wage_bill_C", "wage bill of cognitive occupations", (-0.3, -4.6, -31.0), 1),
    (
        "capital_income",
        "Capital income, pct. above the no-AI path",
        (3.1, 18.9, 81.4),
        1,
    ),
    (
        "employment_C",
        "Cognitive employment, pct. change since mid-2026",
        (-0.5, -3.9, -21.5),
        1,
    ),
    (
        "unemployment_C",
        "Unemployment rate, cognitive workers, pct.",
        (2.9, 4.5, 17.9),
        1,
    ),
    ("unemployment", "Unemployment rate, all workers, pct.", (3.9, 4.6, 11.9), 1),
    ("tfp", "Measured TFP, pct. above the no-AI path", (0.7, 3.1, 13.4), 1),
    ("tfp_growth", "Measured TFP growth, pct. per year", (1.2, 2.3, 7.3), 1),
    ("ideas", "Ideas stock A_t, pct. above the no-AI path", (0.07, 0.20, 0.61), 2),
    ("ideas_growth", "Growth of the ideas stock, pct. per year", (1.69, 1.76, 2.02), 2),
)
# Table 5: (scenario, eps) -> GDP, average wage, net return, capital stock, labor share.
TABLE5_ROWS = ("gdp", "wage_avg", "net_return", "capital", "labor_share")
TABLE5 = {
    (SUBSTANTIAL, 1.0): (6.4, -1.6, 7.6, 9.3, 55.1),
    (SUBSTANTIAL, 3.0): (8.3, 2.1, 7.0, 13.8, 56.1),
    (SUBSTANTIAL, 6.0): (9.1, 3.7, 6.8, 15.7, 56.5),
    (SUBSTANTIAL, math.inf): (10.0, 5.6, 6.5, 18.2, 57.0),
    (EXTREME, 1.0): (21.3, -9.2, 10.3, 33.5, 41.2),
    (EXTREME, 3.0): (32.4, 9.7, 8.3, 56.3, 45.2),
    (EXTREME, 6.0): (37.2, 18.3, 7.5, 67.1, 46.9),
    (EXTREME, math.inf): (43.3, 30.1, 6.5, 82.2, 49.1),
}
# Table 6: (scenario, xi) -> GDP, average wage, w_C, w_N, cognitive employment, both unemployment rates.
TABLE6_ROWS = (
    "gdp",
    "wage_avg",
    "wage_C",
    "wage_N",
    "employment_C",
    "unemployment_C",
    "unemployment",
)
TABLE6 = {
    (SUBSTANTIAL, 0.5): (8.3, 2.1, -0.3, 5.9, -3.9, 4.5, 4.6),
    (SUBSTANTIAL, 0.75): (7.9, 2.2, 0.7, 4.5, -4.6, 5.1, 4.9),
    (SUBSTANTIAL, 0.9): (7.7, 2.3, 1.4, 3.7, -5.0, 5.4, 5.2),
    (EXTREME, 0.0): (36.6, 1.6, -42.2, 70.1, -1.3, 2.6, 3.1),
    (EXTREME, 0.5): (32.4, 9.7, -11.5, 33.6, -21.5, 17.9, 11.9),
    (EXTREME, 0.75): (30.5, 11.1, -2.9, 25.8, -25.9, 21.7, 13.9),
    (EXTREME, 0.9): (29.2, 11.9, 2.8, 21.1, -28.5, 24.0, 15.2),
}
# Footnote 14: substantial pace and gain, extreme disruptiveness, eps = 1. theta_H and xi are not
# stated; the substantial scenario's theta_H = 0.25 and the common xi = 0.5 reproduce GDP and labor
# income, and theta_H = 0.5 does not.
INPUT_SOURCES = frozenset(
    {"Table 1", "Table A.2", "Table B.1", "Appendix B.3", "Section 3.2"},
)
FOOTNOTE14 = Scenario(
    "footnote14",
    m_2030=0.3,
    d_2030=0.4,
    a_anchor=0.35,
    g_a=0.028,
    psi=0.9,
    rho=0.0,
    mu=0.04,
    theta_H=0.25,
)


@dataclass(frozen=True)
class Check:
    """One published number against the model.

    ``basis`` is "predicted" when the paper's text fixes how the number is computed before any
    comparison, and "fitted" when the definition or an unstated parameter was inferred by matching
    the number or taken from the explorer's source; ``note`` says which. A third basis,
    "text_differs", marks a number a sentence of the paper dates or bases differently from the
    tables (see ``text_table_differences``); those are expected to miss and stay out of ``checks``.
    """

    source: str
    label: str
    published: float
    model: float
    decimals: int
    basis: str = "predicted"
    note: str = ""

    @property
    def role(self) -> str:
        """ "input" for numbers the model takes as given (calibration and survey coding), which no
        bug in the dynamics can move, and "output" for numbers the simulation produces.
        """
        return "input" if self.source in INPUT_SOURCES else "output"

    @property
    def slack(self) -> float:
        """Half a unit in the last printed place minus the gap; negative when the number is missed."""
        return 0.5 * 10.0 ** (-self.decimals) - abs(self.model - self.published)

    @property
    def ok(self) -> bool:
        return self.slack >= -1e-9


def cached_runner(simulate_fn: Runner = simulate, **fixed) -> Runner:
    """A memoized ``run(scenario, **calibration_overrides)`` around ``simulate_fn``."""
    cache: dict = {}

    def run(scenario: Scenario, **overrides) -> Simulation:
        key = (scenario, tuple(sorted(overrides.items())))
        if key not in cache:
            cal = replace(Calibration(), **overrides)
            cache[key] = simulate_fn(scenario, cal, **fixed)
        return cache[key]

    return run


def checks(run: Runner) -> list[Check]:
    """Every published number against the model, runs supplied by ``run``."""
    out: list[Check] = []
    base = [readout(run(s)) for s in SCENARIOS3]
    for key, label, values, dec in TABLE3:
        for s, rep, pub in zip(SCENARIOS3, base, values, strict=False):
            out.append(Check("Table 3", f"{label} [{s.name}]", pub, rep[key], dec))
    for (s, eps), values in TABLE5.items():
        rep = readout(run(s, eps=eps))
        for key, pub in zip(TABLE5_ROWS, values, strict=False):
            out.append(
                Check("Table 5", f"{key} [{s.name}, eps={eps}]", pub, rep[key], 1),
            )
    for (s, xi), values in TABLE6.items():
        rep = readout(run(s, xi=xi))
        for key, pub in zip(TABLE6_ROWS, values, strict=False):
            out.append(Check("Table 6", f"{key} [{s.name}, xi={xi}]", pub, rep[key], 1))
    sim14 = run(FOOTNOTE14, eps=1.0)
    fn14 = readout(sim14)
    unstated = "theta_H = 0.25 and xi = 0.5 are unstated; theta_H = 0.5 misses"
    out.append(
        Check(
            "Footnote 14",
            "GDP, pct. above the no-AI path",
            7.2,
            fn14["gdp"],
            1,
            "fitted",
            unstated,
        ),
    )
    out.append(
        Check(
            "Footnote 14",
            "labor income, pct. of no-AI GDP",
            -4.3,
            fn14["labor_income_share_of_gdp"],
            1,
            "fitted",
            unstated,
        ),
    )
    out.append(
        Check(
            "Footnote 14",
            "transfer holding cognitive income at no-AI, pct. of the GDP gain",
            84.0,
            _transfer(sim14),
            0,
            "fitted",
            "base inferred: cognitive jobs counted from mid-2026; the no-AI base gives 87",
        ),
    )
    out.extend(_steady_state_checks(run))
    out.extend(_text_checks(run))
    out.extend(_survey_coding_checks())
    out.extend(_page_checks(run))
    return out


def _page_checks(run: Runner) -> list[Check]:
    """Numbers the explorer page (v1.0, September 2026) prints in its text.

    The page converts GDP to dollars by scaling the 2025 average of the substantial path to
    $30.76 trillion and growing it at 2 percent a year. Its worker split compares 2026.0 with 2030.0
    in the substantial scenario, and its survey sentence runs Table 2's median answers through the quiz.
    """
    cal = Calibration()
    sub = run(SUBSTANTIAL)
    months_2025 = [sub.index(2025.0 + m / 12) for m in range(12)]
    level_2025 = (
        sum(1.02 ** (sub.t[k] - 2025.0) * math.exp(sub["lnY"][k]) for k in months_2025)
        / 12
    )
    scale = round(30.76 / level_2025, 3)
    out = []
    for s, dollars in zip(SCENARIOS3, (34.1, 36.3, 44.4), strict=False):
        sim = run(s)
        value = scale * 1.02**5 * math.exp(sim["lnY"][sim.index(cal.t_read)])
        out.append(
            Check(
                "Explorer page",
                f"GDP in 2030, trillions of 2025 dollars [{s.name}]",
                dollars,
                value,
                1,
                "fitted",
                "dollar scaling taken from the explorer's source",
            ),
        )
    k26, k30 = sub.index(2026.0), sub.index(cal.t_read)
    per = 100 / (sub["ell_C"][k26] + sub["ell_N"][k26])
    start_C = sub["ell_C"][k26] * per
    stay = sub["ell_C"][k30] * per
    lost = max(0.0, start_C - stay)
    moved = min(max(0.0, sub["ell_N"][k30] * per - (100 - start_C)), lost)
    for label, published, value in (
        ("knowledge workers in 2026, pct. of workers", 62.2, start_C),
        ("all other workers in 2026, pct. of workers", 37.8, 100 - start_C),
        ("knowledge workers still in knowledge work in 2030", 59.7, stay),
        ("all other workers in 2030", 39.6, sub["ell_N"][k30] * per),
        ("knowledge jobs lost by 2030", 2.5, lost),
        ("of whom moved to other work", 1.8, moved),
        ("of whom not yet re-employed", 0.7, lost - moved),
    ):
        out.append(
            Check(
                "Explorer page",
                f"{label} [substantial]",
                published,
                value,
                1,
                "fitted",
                "split taken from the explorer's source",
            ),
        )
    medians = Answers(
        capability=0.44 / cal.share_C,
        adoption=0.40,
        alone=0.47,
        gain=math.exp(0.44),
        months=3 * cal.mu_bar / 0.064,
    )
    typical = readout(simulate(answers_to_scenario(medians), horizon=2035.0))
    quiz = "Table 2 medians through the explorer's quiz mapping"
    out.append(
        Check(
            "Explorer page",
            "typical respondent: GDP above the no-AI path, pct.",
            10.0,
            typical["gdp"],
            0,
            "fitted",
            quiz,
        ),
    )
    out.append(
        Check(
            "Explorer page",
            "typical respondent: unemployment rate, pct.",
            5.0,
            typical["unemployment"],
            0,
            "fitted",
            quiz,
        ),
    )
    growth = readout(run(EXTREME))["gdp_growth"]
    out.append(
        Check(
            "Explorer page",
            "extreme: GDP growth reaches, pct. a year",
            15.0,
            growth,
            0,
        ),
    )
    out.append(
        Check(
            "Explorer page",
            "extreme: years for the economy to double",
            4.5,
            100 * math.log(2) / growth,
            1,
        ),
    )
    return out


def _survey_coding_checks() -> list[Check]:
    """Table B.1, the automation example of Appendix B, and the two mu-bar rules of Sections 2.3.2 and 3.2."""
    cal = Calibration()
    out = []
    for n, (pct, m) in enumerate(
        zip(
            (12, 24, 36, 48, 59, 71, 83, 95),
            (0.07, 0.15, 0.22, 0.30, 0.37, 0.44, 0.52, 0.59),
            strict=False,
        ),
        1,
    ):
        out.append(
            Check(
                "Table B.1",
                f"{n} of 8 tasks, pct. of knowledge work",
                pct,
                100 * survey.knowledge_work_share(n),
                0,
            ),
        )
        out.append(
            Check(
                "Table B.1",
                f"{n} of 8 tasks, m_2030",
                m,
                survey.capability_m(n, cal=cal),
                2,
            ),
        )
    for answer, a in zip(
        survey.TIME_RATIO,
        (0.0, 0.0, 0.22, 0.69, 1.39, 2.30),
        strict=False,
    ):
        out.append(
            Check("Table B.1", f"a_2030 for '{answer}'", a, survey.gain_a(answer), 2),
        )
    for answer, mu in zip(
        survey.MONTHS,
        (1.0, 0.34, 0.15, 0.09, 0.05, 0.03, 0.02, 0.0),
        strict=False,
    ):
        out.append(
            Check(
                "Table B.1",
                f"mu for '{answer}'",
                mu,
                survey.reemployment_mu(answer, cal),
                2,
            ),
        )
    example = (
        ["AI does it alone"] * 2
        + ["AI does most of it, with workers checking"] * 2
        + ["workers do most of it, with AI helping"]
    )
    out.append(
        Check(
            "Appendix B.3",
            "automation example psi",
            0.6,
            survey.automation_psi(example),
            1,
        ),
    )
    out.append(
        Check(
            "Section 3.2",
            "mu-bar from the switching odds 19/81 and 11/89",
            0.17,
            mu_from_switching_odds((0.19, 0.11)),
            2,
        ),
    )
    out.append(
        Check(
            "Section 2.3.2",
            "mu-bar at which one job-finder in seven changes group",
            0.17,
            fit_mu_bar(cal, 1.0 / 7.0),
            2,
        ),
    )
    return out


def _transfer(sim: Simulation, base: float | None = None) -> float:
    """Footnote 14's transfer as a percent of the 2030 GDP gain, with cognitive employment
    counted from ``base``, a year of the run.

    The paper does not define it, so the reading that reproduces the printed 84 counts employment
    from mid-2026, the base Section 4.3 uses when it describes the extreme loss as "11.5 percent
    lower paid on 21.5 percent fewer jobs". Against no-AI employment, the 2024 base of Table 3's
    labor income rows, the same transfer is 87 percent.
    """
    cal = sim.calibration
    k = sim.index(cal.t_read)
    k0 = sim.index(cal.t_anchor if base is None else base)
    bill = math.exp(sim["lnW_C"][k]) * sim["ell_C"][k] / sim["ell_C"][k0]
    return 100 * cal.s_L * cal.share_C * (1.0 - bill) / math.expm1(sim["lnY"][k])


def cognitive_profit_share(sim: Simulation) -> float:
    """The largest profit cognitive employers make on the path, in percent of GDP, when their
    labor is valued at its marginal product in System (39) and paid the sticky wage (Table A.1,
    panel D).
    """
    cal, s = sim.calibration, sim.series
    profit = (
        cal.s_L
        * cal.share_C
        * s["ell_C"]
        / sim.steady.ell0[0]
        * (np.exp(s["lnMPL_C"]) - np.exp(s["lnW_C"]))
    )
    return 100 * float(np.max(np.abs(profit / np.exp(s["lnY"]))))


def transfer_bases(run: Runner) -> tuple[float, float]:
    """Footnote 14's transfer on the two employment bases the text allows: counted from mid-2026,
    which reproduces the printed 84, and from 2024, the no-AI employment.
    """
    sim = run(FOOTNOTE14, eps=1.0)
    return _transfer(sim), _transfer(sim, 2024.0)


def output_misses(**inputs) -> int:
    """Published outputs outside their rounding when the model runs on the given Table 1 inputs."""

    def run(scenario, cal=None, **kw):
        return simulate(scenario, replace(cal or Calibration(), **inputs), **kw)

    return sum(not c.ok for c in checks(cached_runner(run)) if c.role == "output")


# Table 1's data inputs as the paper prints them, and to one more digit, as the explorer's
# calibration record holds them.
PRINTED_INPUTS = {
    "share_C_override": 0.624,
    "U_bar": 0.038,
    "sep_rel_override": (0.69, 1.52),
    "q_T_share": 0.55,
}
ONE_MORE_DIGIT = {
    "share_C_override": 0.6235,
    "U_bar": 0.0384,
    "sep_rel_override": (0.689, 1.515),
    "q_T_share": 0.545,
}


def _steady_state_checks(run: Runner) -> list[Check]:
    """Section 2.3.2 and 3.2: the normal-times flow block."""
    sim = run(SUBSTANTIAL)
    ss = sim.steady
    rates = [100 * ss.U[o] / (ss.U[o] + ss.ell0[o]) for o in (0, 1)]
    return [
        Check(
            "Section 2.3.2",
            "pool of cognitive origin, pct. of L",
            1.76,
            100 * ss.U[0],
            2,
        ),
        Check(
            "Section 2.3.2",
            "pool of other origin, pct. of L",
            2.08,
            100 * ss.U[1],
            2,
        ),
        Check(
            "Section 2.3.2",
            "unemployment rate of the cognitive group, pct.",
            2.9,
            rates[0],
            1,
        ),
        Check(
            "Section 2.3.2",
            "unemployment rate of the other group, pct.",
            5.4,
            rates[1],
            1,
        ),
        Check("Section 2.3.2", "normal filling rate, cognitive", 0.66, ss.pi_bar[0], 2),
        Check("Section 2.3.2", "normal filling rate, other", 0.64, ss.pi_bar[1], 2),
        Check("Section 2.3.2", "matching efficiency chi", 0.76, ss.chi, 2),
        Check(
            "Section 2.3.2",
            "aggregate finding rate, per month",
            0.23,
            ss.f_aggregate,
            2,
        ),
        Check(
            "Section 2.3.2",
            "normal quit rate, cognitive, pct. a month",
            0.63,
            100 * ss.q[0],
            2,
        ),
        Check(
            "Section 2.3.2",
            "normal quit rate, other, pct. a month",
            1.40,
            100 * ss.q[1],
            2,
            note="1.40 is reproduced by the converted rate -ln(1 - q-hat), 1.3985, and by the paper's own"
            " arithmetic 0.92 x 1.52 = 1.398; the unrounded monthly fraction, 1.389, would print as 1.39",
        ),
    ]


def _text_checks(run: Runner) -> list[Check]:
    """Numbers stated in the text, Table 1, and Table A.2."""
    cal = Calibration()
    years = cal.t_read - cal.t_anchor
    out = [
        Check("Table 1", "cognitive share of employment", 0.624, cal.share_C, 3),
        Check("Table 1", "normal search pool, share of L", 0.038, cal.U_bar, 3),
        Check(
            "Table 1",
            "relative separation rate, cognitive",
            0.69,
            cal.sep_rel[0],
            2,
        ),
        Check("Table 1", "relative separation rate, other", 1.52, cal.sep_rel[1], 2),
        Check(
            "Table 1",
            "share of quits that responds to job prospects",
            0.55,
            cal.q_T_share,
            2,
        ),
    ]
    for s, (k_m, k_d) in zip(
        SCENARIOS3,
        ((0.14, 0.23), (0.33, 0.51), (0.75, 0.74)),
        strict=False,
    ):
        out.append(
            Check(
                "Table A.2",
                f"kappa_m [{s.name}]",
                k_m,
                logistic_slope(cal.m_anchor, s.m_2030, cal.m_bar, years),
                2,
            ),
        )
        out.append(
            Check(
                "Table A.2",
                f"kappa_d [{s.name}]",
                k_d,
                logistic_slope(cal.d_anchor, s.d_2030, cal.d_ceiling, years),
                2,
            ),
        )
    sub = run(SUBSTANTIAL)
    k = sub.index(cal.t_read)
    x = ScenarioPaths(SUBSTANTIAL, cal).at(cal.t_read)
    out += [
        Check(
            "Section 2.1.3",
            "substantial rental rate above r-bar in 2030, pct.",
            4.6,
            100 * math.expm1(sub["pot_dlnr"][k]),
            1,
        ),
        Check(
            "Section 2.1.3",
            "substantial wage above no-AI in 2030 at eps = 3, pct.",
            1.9,
            100 * math.expm1(sub["pot_lnW"][k]),
            1,
            note="includes the ideas gain Delta ln A (1.87); the level channel alone gives 1.71",
        ),
        Check(
            "Section 2.1.3",
            "substantial exact TFP gain in 2030",
            0.029,
            tfp_base_weight(x, 0.0, cal),
            3,
            note="excludes the ideas gain, unlike the wage in the same paragraph; with it, 0.031",
        ),
        Check(
            "Section 4.2",
            "substantial employment in all other occupations since mid-2026, pct.",
            4.6,
            readout(sub)["employment_N"],
            1,
        ),
    ]
    ext = run(EXTREME)
    k = ext.index(cal.t_read)
    k26 = ext.index(cal.t_anchor)
    growth = (cal.g + cal.n) * (cal.t_read - cal.t_anchor)
    out += [
        Check(
            "Section 2.2.1",
            "extreme research uplift in 2030",
            0.28,
            ext["lnY"][k],
            2,
        ),
        Check(
            "Section 4.3",
            "extreme GDP above mid-2026, pct.",
            40.0,
            100 * math.expm1(ext["lnY"][k] - ext["lnY"][k26] + growth),
            0,
        ),
    ]
    return out


def text_table_differences(run: Runner) -> list[Check]:
    """The two differences between the paper's text and its tables that carry a checkable number.

    Both are Section 4.2's sentence that cognitive unemployment "rises from 2.9 percent in
    mid-2026 to 4.5 percent in 2030, more than a 50 percent increase" in the substantial
    scenario. Appendix A lets the scenario's reemployment discount mu apply from t0 = 2024, so
    the rate already stands at 3.06 by mid-2026, before any displacement, and 2.9 is the rate at
    t0, the normal-times steady state of Section 2.3.2. The sentence therefore dates its starting
    level differently from the model, which is what these two numbers record; measured from the
    2024 rate the sentence most likely means, the rise is 59 percent and its claim of more than 50
    holds. The explorer agrees with the model throughout.

    The other two differences the reproduction reports, Section 2.1.3's three potential-economy
    numbers and Footnote 14's transfer share, turn on which base a number is read on and are
    handled in the report's prose, so they are not here.
    """
    cal = Calibration()
    sim = run(SUBSTANTIAL)

    def rate(t: float) -> float:
        k = sim.index(t)
        return 100 * sim["U_C"][k] / (sim["U_C"][k] + sim["ell_C"][k])

    start, anchor, end = rate(cal.t0), rate(cal.t_anchor), rate(cal.t_read)
    note = (
        "the scenario mu applies from 2024, raising the rate before mid-2026; 2.9 is the 2024"
        " steady state, the base the sentence most likely means"
    )
    rise = (
        f"the sentence says more than 50; from the mid-2026 rate it is"
        f" {100 * (end / anchor - 1):.0f}, from the 2024 rate"
        f" {100 * (end / start - 1):.0f}, on which the claim holds"
    )
    return [
        Check(
            "Section 4.2",
            "substantial cognitive unemployment in mid-2026, pct.",
            2.9,
            anchor,
            1,
            "text_differs",
            note,
        ),
        Check(
            "Section 4.2",
            "rise in substantial cognitive unemployment from mid-2026 to 2030, pct.",
            50.0,
            100 * (end / anchor - 1),
            0,
            "text_differs",
            rise,
        ),
    ]


def failures(run: Runner) -> list[Check]:
    """The published numbers the model misses."""
    return [c for c in checks(run) if not c.ok]
