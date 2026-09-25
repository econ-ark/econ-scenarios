"""Fixtures and helpers every paper's tests share: the three scenario runs, the pages, and the
number and date patterns the page gates read. Session scope, since every object is immutable.

This module depends on the scenario model and on nothing above it, because every paper generated
from this repository carries it, the reproduction included, and the reproduction has no
household. Helpers that need one live in their own fixture module beside this file, which loads
as a plugin wherever it was exported.
"""

import re
from pathlib import Path

import pytest

from econ_scenarios import EXTREME, MODEST, SUBSTANTIAL, monthly_growth, simulate
from tables import MONTHS

# Every fixture module beside this one loads as a plugin. The directory is asked rather than a
# name written down: conftest is carried by every cut, so a name here is a name every public
# repository holds, whether or not the module it points at was exported with it.
pytest_plugins = [
    path.stem for path in sorted(Path(__file__).parent.glob("*_fixtures.py"))
]

# Read from a file, and derived per cut at export, so a repository holds the names of its own
# tests alone. The list was inline until 2026-09-18, when the reproduction's public repository
# turned out to carry the names of 19 tests belonging to papers it does not contain.
COMPUTE_FILE = Path(__file__).resolve().parent / "compute-modules.txt"
COMPUTE_MODULES = frozenset(
    line.strip()
    for line in COMPUTE_FILE.read_text(encoding="utf-8").splitlines()
    if line.strip() and not line.startswith("#")
)


def pytest_collection_modifyitems(items) -> None:
    """Mark by module, so a new test in a solving module is covered without anyone remembering."""
    for item in items:
        if Path(str(item.fspath)).stem in COMPUTE_MODULES:
            item.add_marker(pytest.mark.compute)


DECIMAL = re.compile(r"(?<![\w.])\d+\.\d+(?![\w.])")
DATE = re.compile(r"\b(?:" + "|".join(MONTHS) + r") \d{4}\b")


def quoted(page: str) -> set[str]:
    """The decimal numbers and month-and-year dates in the page's prose, outside code, includes, and
    directive options.
    """
    prose = [
        line for line in page.splitlines() if not re.match(r"\s*(```|:\w+:)", line)
    ]
    text = re.sub(r"`[^`]*`", "", "\n".join(prose))
    return set(DECIMAL.findall(text)) | set(DATE.findall(text))


def placed(template: str, key: str, facts: dict[str, str]) -> str:
    """The sentence a template stands for: a bare ``{}`` takes the fact under ``key``, and named
    fields take their own facts, so a sentence carrying two facts names both and no fact's value
    is ever typed into a template by hand.
    """
    return (
        template.format(**facts)
        if re.search(r"\{[a-z]", template)
        else template.format(facts[key])
    )


@pytest.fixture(scope="session")
def extreme():
    return simulate(EXTREME)


@pytest.fixture(
    scope="session",
    params=[MODEST, SUBSTANTIAL, EXTREME],
    ids=lambda s: s.name,
)
def scenario(request):
    return simulate(request.param)


@pytest.fixture(scope="session")
def growth(extreme):
    return monthly_growth(extreme.calibration)
