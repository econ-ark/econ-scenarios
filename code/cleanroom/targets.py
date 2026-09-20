"""Published targets, transcribed by hand from the PDF page images (not from any other source).

Each target: (id, case, report key, printed string, location). A target matches when the
model value differs from the printed value by at most half a unit in the last printed digit.
"""

# Table 3 rows: report key and printed values for (No AI, Modest, Substantial, Extreme). p. 31.
TABLE3 = [
    ("gdp", "GDP, pct. above the no-AI path", ["0", "1.6", "8.3", "32.4"]),
    ("gdp_index", "GDP, index with 2024 = 100", ["112.7", "114.5", "122.1", "149.3"]),
    ("gdp_growth", "GDP growth, pct. per year", ["2.0", "2.4", "5.4", "15.4"]),
    ("avg_wage", "Average wage, pct. above the no-AI path", ["0", "0.7", "2.1", "9.7"]),
    ("wC", "cognitive occupations, w_C", ["0", "0.4", "-0.3", "-11.5"]),
    ("wN", "all other occupations, w_N", ["0", "1.1", "5.9", "33.6"]),
    (
        "net_return",
        "Net return to capital r - delta, pct. per year",
        ["6.5", "6.6", "7.0", "8.3"],
    ),
    (
        "capital",
        "Capital stock, pct. above the no-AI path",
        ["0", "2.3", "13.8", "56.3"],
    ),
    ("labor_share", "Labor share, pct. of income", ["60.0", "59.4", "56.1", "45.2"]),
    (
        "capital_share",
        "Capital share, pct. of income",
        ["40.0", "40.6", "43.9", "54.8"],
    ),
    (
        "labor_income",
        "Labor income, pct. above the no-AI path",
        ["0", "0.6", "1.4", "0.5"],
    ),
    (
        "wagebill_C",
        "wage bill of cognitive occupations",
        ["0", "-0.3", "-4.6", "-31.0"],
    ),
    (
        "capital_income",
        "Capital income, pct. above the no-AI path",
        ["0", "3.1", "18.9", "81.4"],
    ),
    (
        "cog_emp",
        "Cognitive employment, pct. change since mid-2026",
        ["0", "-0.5", "-3.9", "-21.5"],
    ),
    (
        "u_C",
        "Unemployment rate, cognitive workers, pct.",
        ["2.9", "2.9", "4.5", "17.9"],
    ),
    ("u_all", "Unemployment rate, all workers, pct.", ["3.8", "3.9", "4.6", "11.9"]),
    ("tfp", "Measured TFP, pct. above the no-AI path", ["0", "0.7", "3.1", "13.4"]),
    ("tfp_growth", "Measured TFP growth, pct. per year", ["1.0", "1.2", "2.3", "7.3"]),
    (
        "ideas",
        "Ideas stock A, pct. above the no-AI path",
        ["0", "0.07", "0.20", "0.61"],
    ),
    (
        "ideas_growth",
        "Growth of the ideas stock, pct. per year",
        ["1.67", "1.69", "1.76", "2.02"],
    ),
]

# Table 5, p. 37: substantial eps = 1, 3, 6, inf; extreme eps = 1, 3, 6, inf.
TABLE5 = [
    ("gdp", ["6.4", "8.3", "9.1", "10.0", "21.3", "32.4", "37.2", "43.3"]),
    ("avg_wage", ["-1.6", "2.1", "3.7", "5.6", "-9.2", "9.7", "18.3", "30.1"]),
    ("net_return", ["7.6", "7.0", "6.8", "6.5", "10.3", "8.3", "7.5", "6.5"]),
    ("capital", ["9.3", "13.8", "15.7", "18.2", "33.5", "56.3", "67.1", "82.2"]),
    ("labor_share", ["55.1", "56.1", "56.5", "57.0", "41.2", "45.2", "46.9", "49.1"]),
]
TABLE5_CASES = [
    "sub_eps1",
    "substantial",
    "sub_eps6",
    "sub_epsinf",
    "ext_eps1",
    "extreme",
    "ext_eps6",
    "ext_epsinf",
]

# Table 6, p. 38: substantial xi = 0.5, 0.75, 0.9; extreme xi = 0, 0.5, 0.75, 0.9.
TABLE6 = [
    ("gdp", ["8.3", "7.9", "7.7", "36.6", "32.4", "30.5", "29.2"]),
    ("avg_wage", ["2.1", "2.2", "2.3", "1.6", "9.7", "11.1", "11.9"]),
    ("wC", ["-0.3", "0.7", "1.4", "-42.2", "-11.5", "-2.9", "2.8"]),
    ("wN", ["5.9", "4.5", "3.7", "70.1", "33.6", "25.8", "21.1"]),
    ("cog_emp", ["-3.9", "-4.6", "-5.0", "-1.3", "-21.5", "-25.9", "-28.5"]),
    ("u_C", ["4.5", "5.1", "5.4", "2.6", "17.9", "21.7", "24.0"]),
    ("u_all", ["4.6", "4.9", "5.2", "3.1", "11.9", "13.9", "15.2"]),
]
TABLE6_CASES = [
    "substantial",
    "sub_xi075",
    "sub_xi09",
    "ext_xi0",
    "extreme",
    "ext_xi075",
    "ext_xi09",
]

# Footnote 14, p. 37.
FN14 = [
    ("fn14", "gdp", "7.2", "fn14: 2030 GDP is 7.2 percent above its no-AI path"),
    (
        "fn14",
        "labor_income_gdp_units",
        "-4.3",
        "fn14: total labor income lower by 4.3 percent of no-AI GDP",
    ),
    (
        "fn14",
        "transfer_share_of_gain",
        "84",
        "fn14: transfer equal to 84 percent of GDP gains",
    ),
]

# Section 2.3.2 (p. 21) and Section 3.2 (p. 26): steady state. Case "ss".
SEC232 = [
    ("ss", "qbar_C_pct", "0.63", "2.3.2: qbar_C = 0.63 percent a month"),
    ("ss", "qbar_N_pct", "1.40", "2.3.2: qbar_N = 1.40 percent a month"),
    ("ss", "f_agg", "0.23", "2.3.2/3.2: aggregate finding rate 0.23 a month"),
    (
        "ss",
        "UC_pct",
        "1.76",
        "2.3.2: pool of cognitive origin 1.76 percent of the labor force",
    ),
    ("ss", "UN_pct", "2.08", "2.3.2: pool of other origin 2.08"),
    ("ss", "uC_rate", "2.9", "2.3.2: 2.9 percent of the one group"),
    ("ss", "uN_rate", "5.4", "2.3.2: 5.4 percent of the other"),
    ("ss", "piC", "0.66", "2.3.2: filling rate 0.66"),
    ("ss", "piN", "0.64", "2.3.2: filling rate 0.64"),
    ("ss", "chi", "0.76", "2.3.2: chi is 0.76"),
]

# Section 4.2 (pp. 32-34), substantial scenario at 2030 unless stated.
SEC42 = [
    ("substantial", "gdp", "8.3", "4.2: GDP 8.3 percent above its no-AI path"),
    (
        "substantial",
        "gdp_growth",
        "5.4",
        "4.2: growth over the twelve months to 2030 is 5.4 percent",
    ),
    ("substantial", "avg_wage", "2.1", "4.2: average wage up 2.1 percent"),
    (
        "substantial",
        "wC",
        "-0.3",
        "4.2: cognitive wages below the no-AI path by 0.3 percent",
    ),
    (
        "substantial",
        "wN",
        "5.9",
        "4.2: wages in the rest of the economy higher by 5.9 percent",
    ),
    (
        "substantial",
        "labor_share_mid2026",
        "60",
        "4.2: labor share 60 percent of income in 2026",
    ),
    ("substantial", "labor_share", "56", "4.2: 56 percent in 2030"),
    (
        "substantial",
        "capital_share",
        "44",
        "4.2: capital share rises ... to 44 percent",
    ),
    (
        "substantial",
        "cog_emp",
        "-3.9",
        "4.2: cognitive employment 3.9 percent below its mid-2026 level",
    ),
    (
        "substantial",
        "oth_emp",
        "4.6",
        "4.2: employment in all other occupations has risen by 4.6 percent",
    ),
    (
        "substantial",
        "u_C_mid2026",
        "2.9",
        "4.2: cognitive unemployment rate 2.9 percent in mid-2026",
    ),
    ("substantial", "u_C", "4.5", "4.2: ... to 4.5 percent in 2030"),
]

# Section 4.3 (pp. 34-35), extreme scenario at 2030.
SEC43 = [
    (
        "extreme",
        "gdp_vs_mid2026",
        "40",
        "4.3: GDP is 40 percent higher than in mid-2026",
    ),
    ("extreme", "gdp", "32", "4.3: 32 percent above the no-AI path"),
    (
        "extreme",
        "gdp_growth",
        "15.4",
        "4.3: GDP growth in 2030 accelerates to 15.4 percent",
    ),
    (
        "extreme",
        "avg_wage",
        "9.7",
        "4.3: average wage 9.7 percent above the no-AI path",
    ),
    ("extreme", "wC", "-11.5", "4.3: cognitive wages 11.5 percent below"),
    (
        "extreme",
        "wN",
        "33.6",
        "4.3: wages in all other occupations 33.6 percent higher",
    ),
    ("extreme", "capital_share", "55", "4.3: capital share rises from 40% to 55%"),
    ("extreme", "labor_share", "45", "4.3: labor share declines from 60% to 45%"),
    (
        "extreme",
        "share_shift",
        "15",
        "4.3: a full 15 percent of GDP moves from labor to capital",
    ),
    ("extreme", "net_return", "8.3", "4.3: net return rises from 6.5 to 8.3 percent"),
    ("extreme", "return_increase", "28", "4.3: an increase of about 28 percent"),
    (
        "extreme",
        "cog_emp",
        "-21.5",
        "4.3: cognitive employment 21.5 percent below its mid-2026 level",
    ),
    (
        "extreme",
        "u_C",
        "17.9",
        "4.3: unemployment rate for cognitive-origin workers 17.9 percent",
    ),
    ("extreme", "u_all", "11.9", "4.3: economy-wide unemployment rate 11.9 percent"),
    (
        "extreme",
        "capital_income",
        "81",
        "4.3: capital income 81 percent above its no-AI path",
    ),
    (
        "extreme",
        "wagebill_C",
        "-31",
        "4.3: cognitive wage bill 31 percent below its previous path",
    ),
    (
        "extreme",
        "transfer_share_of_gdp",
        "9",
        "4.3: a transfer of about 9 percent of GDP",
    ),
]

# Qualitative claims (evaluated by an explicit predicate, reported separately, not counted).
QUALITATIVE = [
    (
        "ss",
        "switch_share",
        "one in seven",
        lambda v: abs(v - 1 / 7) < 0.005,
        "2.3.2: share of job-finders who change groups equals one in seven",
    ),
    (
        "substantial",
        "uC_increase",
        "more than 50 percent",
        lambda v: v > 50.0,
        "4.2: cognitive unemployment rate rises ... more than a 50 percent increase",
    ),
    (
        "extreme",
        "wC_level_vs_mid2026",
        "slightly lower",
        lambda v: -10.0 < v < 0.0,
        "4.3: cognitive wages are slightly lower in 2030 than in mid-2026",
    ),
    (
        "extreme",
        "labor_income",
        "almost exactly unchanged",
        lambda v: abs(v) < 1.0,
        "4.3: total labor income almost exactly what it would have been without AI",
    ),
    (
        "extreme",
        "gain_over_loss",
        "almost three times",
        lambda v: 2.5 <= v < 3.0,
        "4.3: the economy's gain is almost three times the cognitive occupations' loss",
    ),
    (
        "extreme",
        "N_bill_gain_vs_C_loss",
        "nearly the same amount",
        lambda v: 0.9 < v < 1.1,
        "4.3: wage bill of all other occupations higher by nearly the same amount",
    ),
    (
        "extreme",
        "net_gain_after_transfer",
        "more than 20 percent",
        lambda v: v > 20.0,
        "4.3: leave the rest of the economy more than 20 percent ahead",
    ),
]

# Numbers from other sections that the model produces (reported separately, not counted).
EXTRA = [
    ("substantial", "tfp_levelonly_log", "0.029", "2.1.3: the exact solution is 0.029"),
    (
        "substantial",
        "rental_levelonly_pct",
        "4.6",
        "2.1.3: rental rate in 2030 is 4.6 percent above rbar",
    ),
    (
        "substantial",
        "wage_levelonly_pct",
        "1.9",
        "2.1.3: the wage is 1.9 percent above its no-AI path",
    ),
    (
        "modest",
        "gdp_gap_t0",
        "0.25",
        "App. A: at t0 the GDP gap is at most a quarter of a percent (checked as <= 0.25)",
    ),
    ("extreme", "dlnR", "0.28", "2.2.1: the uplift Delta ln R reaches 0.28 in 2030"),
    (
        "extreme",
        "ideas",
        "0.6",
        "2.2.1: ideas stock just 0.6 percent above its no-AI path",
    ),
    ("extreme", "wN", "34", "1: wage in all other occupations is 34 percent above"),
    ("modest", "gdp", "1.6", "1: GDP in 2030 is 1.6 percent higher"),
    ("substantial", "gdp", "8", "abstract: GDP rises by 8 percent"),
    (
        "substantial",
        "cog_emp",
        "-4",
        "abstract: cognitive employment declines by 4 percent",
    ),
]


def decimals(s):
    return len(s.split(".")[1]) if "." in s else 0


def matches(value, printed):
    return abs(value - float(printed)) <= 0.5 * 10 ** (-decimals(printed)) + 1e-12


def all_targets():
    """Flat list of counted targets: (tid, case, key, printed, where)."""
    out = []
    scen = ["noai", "modest", "substantial", "extreme"]
    for key, label, vals in TABLE3:
        for sc, v in zip(scen, vals, strict=False):
            out.append((f"T3.{key}.{sc}", sc, key, v, f"Table 3: {label} [{sc}]"))
    for key, vals in TABLE5:
        for case, v in zip(TABLE5_CASES, vals, strict=False):
            out.append((f"T5.{key}.{case}", case, key, v, f"Table 5: {key} [{case}]"))
    for key, vals in TABLE6:
        for case, v in zip(TABLE6_CASES, vals, strict=False):
            out.append((f"T6.{key}.{case}", case, key, v, f"Table 6: {key} [{case}]"))
    for prefix, source in (
        ("FN14", FN14),
        ("S232", SEC232),
        ("S42", SEC42),
        ("S43", SEC43),
    ):
        for case, key, v, where in source:
            out.append((f"{prefix}.{key}", case, key, v, where))
    return out
