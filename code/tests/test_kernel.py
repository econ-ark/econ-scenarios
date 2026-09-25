"""The browser import hook runs the repository's own files, and only those."""

import contextlib
import importlib
import re
import sys
from pathlib import Path

import econ_scenarios
import numpy as np
import pytest
import yaml
from kernel import MODULES, PACKAGES, ServedSource

CODE = Path(__file__).resolve().parents[1]


def serve(root: Path, overrides: dict[str, str | None] | None = None):
    """A fetch that reads files under ``root``, with some paths replaced or withheld."""
    overrides = overrides or {}

    def fetch(path: str) -> str | None:
        if path in overrides:
            return overrides[path]
        file = root / path
        return file.read_text() if file.is_file() else None

    return fetch


def _ours(name: str) -> bool:
    return name.partition(".")[0] in PACKAGES + MODULES


@contextlib.contextmanager
def served(fetch):
    """Import through a ``ServedSource`` alone, then restore the modules already loaded."""
    saved = {name: module for name, module in sys.modules.items() if _ours(name)}
    for name in saved:
        del sys.modules[name]
    finder = ServedSource(fetch)
    sys.meta_path.insert(0, finder)
    try:
        yield
    finally:
        sys.meta_path.remove(finder)
        for name in [name for name in sys.modules if _ours(name)]:
            del sys.modules[name]
        sys.modules.update(saved)


def test_served_package_runs_the_same_model() -> None:
    reference = econ_scenarios.simulate(econ_scenarios.MODEST)
    with served(serve(CODE)):
        package = importlib.import_module("econ_scenarios")
        assert isinstance(package.__spec__.loader, ServedSource)
        sim = package.simulate(package.MODEST)
    for name in reference.series:
        np.testing.assert_array_equal(sim[name], reference[name])


def test_the_served_file_is_the_one_that_runs() -> None:
    source = (CODE / "econ_scenarios" / "__init__.py").read_text() + "\nSERVED = True\n"
    with served(serve(CODE, {"econ_scenarios/__init__.py": source})):
        assert importlib.import_module("econ_scenarios").SERVED


def test_a_file_the_site_does_not_serve_is_not_found() -> None:
    with (
        served(serve(CODE, {"econ_scenarios/labor.py": None})),
        pytest.raises(ModuleNotFoundError),
    ):
        importlib.import_module("econ_scenarios")


def test_top_level_modules_and_the_validation_package_load() -> None:
    with served(serve(CODE)):
        published = importlib.import_module("validation.published")
        figures = importlib.import_module("figures")
        assert isinstance(published.__spec__.loader, ServedSource)
        assert isinstance(figures.__spec__.loader, ServedSource)


def test_other_modules_are_left_to_the_usual_finders() -> None:
    def fetch(path: str) -> str | None:
        msg = f"asked the site for {path}"
        raise AssertionError(msg)

    assert ServedSource(fetch).find_spec("numpy") is None


def test_the_supplement_bootstraps_this_module_by_the_name_the_site_serves() -> None:
    """The appendix's first cell fetches this module by filename, and the site serves that name.

    The browser branch of that cell runs under Pyodide alone. A local ``myst build --execute``
    takes the other branch, and no test imported the module the way the cell does, so the
    filename in the string was checked by nothing: renaming this module on 2026-09-18 would
    have left the reader's cells fetching a 404 with the suite and the build both green.
    """
    cell = (CODE.parent / "content" / "reproduction-appendix.md").read_text()
    fetched = set(re.findall(r'open_url\("([^"]+)"\)', cell))
    registered = set(re.findall(r'sys\.modules\["([^"]+)"\]', cell))
    assert fetched == {f"{Path(__file__).stem.removeprefix('test_')}.py"}, fetched
    assert registered == {p.removesuffix(".py") for p in fetched}, registered
    project = yaml.safe_load((CODE.parent / "myst.yml").read_text())["project"]
    served = {Path(s).name for s in project["static_files"]}
    assert fetched <= served, (fetched, served)
    for name in fetched:
        assert (CODE / name).is_file(), name
