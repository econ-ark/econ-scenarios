"""Tables for the report's pages: the paper's numbers next to the reproduction's.

Each function returns an ``IPython.display.HTML`` table, so a page cell shows it the same way in
a local build and in the browser.
"""

from __future__ import annotations

import html
from collections import Counter

import numpy as np
from econ_scenarios import (
    EXTREME,
    MODEST,
    SUBSTANTIAL,
    Calibration,
    Simulation,
    readout,
)
from exhibits import expected_spell, no_ai_year_risk, unemployed_a_year_later
from IPython.display import HTML
from validation.published import TABLE3, Check

SCENARIOS3 = (MODEST, SUBSTANTIAL, EXTREME)
SCENARIO_ROWS = (
    ("m_2030", "affected mass, 2030"),
    ("d_2030", "diffusion share, 2030"),
    ("a_anchor", "log gain per instance, mid-2026"),
    ("g_a", "slope of the log gain, per year"),
    ("psi", "automation share"),
    ("rho", "reinstatement ratio"),
    ("mu", "search discount on the path"),
    ("theta_H", "posting speed, per month"),
)


def _table(
    head: list[str],
    rows: list[list[str]],
    classes: list[str] | None = None,
) -> HTML:
    """An HTML table in the site's table style; ``classes`` marks each column (``num`` right-aligns
    figures, ``paper`` and ``here`` set the paper's values apart from the reproduction's).
    """
    classes = classes or ["num"] * len(head)
    header = "".join(
        f'<th class="{c}">{h}</th>' for c, h in zip(classes, head, strict=False)
    )
    body = "".join(
        "<tr>"
        + "".join(
            f'<td class="{c}">{cell}</td>'
            for c, cell in zip(classes, row, strict=False)
        )
        + "</tr>"
        for row in rows
    )
    return HTML(f'<table class="es-table"><tr>{header}</tr>{body}</table>')


def scenario_table() -> HTML:
    """The three scenarios' assumptions, as the code holds them (Table 1, panels B and C)."""
    rows = [
        [label] + [f"{getattr(s, field):g}" for s in SCENARIOS3]
        for field, label in SCENARIO_ROWS
    ]
    return _table(
        ["", *(s.name.capitalize() for s in SCENARIOS3)],
        rows,
        ["", "num", "num", "num"],
    )


def table3(run) -> HTML:
    """Table 3: each scenario's printed value beside the reproduction's, two digits further."""
    reports = [readout(run(s)) for s in SCENARIOS3]
    head = ["In 2030"] + [
        f"{s.name.capitalize()}: {side}"
        for s in SCENARIOS3
        for side in ("paper", "here")
    ]
    rows = [
        [html.escape(label)]
        + [
            cell
            for pub, rep in zip(values, reports, strict=False)
            for cell in (f"{pub:.{dec}f}", f"{rep[key]:.{dec + 2}f}")
        ]
        for key, label, values, dec in TABLE3
    ]
    return _table(head, rows, ["", *(["num paper", "num here"] * len(SCENARIOS3))])


def checks_table(checks: list[Check], sources: tuple[str, ...]) -> HTML:
    """The published numbers from ``sources``: printed value, reproduction, basis, and whether the
    reproduction rounds to the printed value.
    """
    rows = [
        [
            c.source,
            html.escape(c.label),
            f"{c.published:.{c.decimals}f}",
            f"{c.model:.{c.decimals + 2}f}",
            c.basis + (f": {html.escape(c.note)}" if c.note else ""),
            "yes" if c.ok else "<b>no</b>",
        ]
        for c in checks
        if c.source in sources
    ]
    return _table(
        ["Source", "Number", "Paper", "Here", "Basis", "Within rounding"],
        rows,
        ["", "", "num paper", "num here", "", ""],
    )


def summary(checks: list[Check]) -> HTML:
    """How many published numbers each source contributes, by basis, and how many are matched."""
    sources = list(dict.fromkeys(c.source for c in checks))
    count = Counter((c.source, c.basis) for c in checks)
    matched = Counter(c.source for c in checks if c.ok)
    rows = [
        [
            s,
            str(count[s, "predicted"]),
            str(count[s, "fitted"]),
            f"{matched[s]} of {count[s, 'predicted'] + count[s, 'fitted']}",
        ]
        for s in sources
    ]
    total = [
        "<b>All</b>",
        str(sum(c.basis == "predicted" for c in checks)),
        str(sum(c.basis == "fitted" for c in checks)),
        f"<b>{sum(c.ok for c in checks)} of {len(checks)}</b>",
    ]
    return _table(
        ["Source", "Predicted", "Fitted", "Within rounding"],
        [*rows, total],
        ["", "num", "num", "num"],
    )


def readouts_table(
    sims: dict[str, Simulation],
    keys: tuple[tuple[str, str], ...],
) -> HTML:
    """Selected Table 3 rows for each run in ``sims``."""
    reports = {name: readout(sim) for name, sim in sims.items()}
    rows = [
        [label] + [f"{rep[key]:.1f}" for rep in reports.values()] for key, label in keys
    ]
    return _table(
        ["In 2030", *(name.capitalize() for name in reports)],
        rows,
        ["", *(["num"] * len(reports))],
    )


def worker_table(sims: dict[str, Simulation], year: float = 2029.0) -> HTML:
    """A cognitive worker's odds in January of ``year``: the chance that a worker employed then is
    unemployed a year later, and the expected spell of a worker unemployed then.
    """
    ss = next(iter(sims.values())).steady
    rows = [
        [
            "No AI",
            f"{100 * no_ai_year_risk(ss, Calibration()):.1f}",
            f"{expected_spell(np.array([ss.f[0]]))[0]:.1f}",
        ],
    ]
    for name, sim in sims.items():
        k = sim.index(year)
        rows.append(
            [
                name.capitalize(),
                f"{100 * unemployed_a_year_later(sim)[k]:.1f}",
                f"{expected_spell(sim['f_C'])[k]:.1f}",
            ],
        )
    return _table(
        [
            f"January {year:.0f}",
            "Unemployed a year later, pct.",
            "Expected spell, months",
        ],
        rows,
        ["", "num", "num"],
    )
