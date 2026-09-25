"""What the in-browser gate reports, without opening a browser.

``visit`` is the one part that needs Chrome, so it is stubbed here and the reporting around it
is tested directly. The check's own rejection test is live: it reported the launch control and
its throw against the site published on 2026-09-24, and passes against a build with no
``jupyter`` key.
"""

from __future__ import annotations

import sys
import urllib.error
import urllib.request
from pathlib import Path

import pytest
from playwright.sync_api import Error as PlaywrightError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import browsercheck

ARTICLE = f"<html class='{browsercheck.MARKERS['article-theme']}'></html>"
BOOK = f"<html class='{browsercheck.MARKERS['book-theme']}'></html>"


@pytest.fixture
def built(tmp_path: Path) -> Path:
    """A directory that looks built, since check() refuses one that is absent."""
    (tmp_path / "reproduction-appendix").mkdir()
    return tmp_path


def test_the_repository_declares_one_known_template() -> None:
    """The markers are keyed on template names, so a rename upstream must not pass silently."""
    assert browsercheck.declared_template() in browsercheck.MARKERS


def test_a_build_of_the_wrong_template_is_refused_before_anything_is_measured(
    monkeypatch,
    built: Path,
) -> None:
    """The trap this check exists to close, and the one it fell into first.

    Measured 2026-09-18: a stale book-theme build sat in _build/html while myst.yml declared
    article-theme. Both render a plausible page, the template that made it goes unnamed in the
    output, and the check reported the supplement healthy. A drifting button label gave it away.
    """
    monkeypatch.setattr(browsercheck, "visit", lambda url: ([], 17, BOOK))
    monkeypatch.setattr(browsercheck, "declared_template", lambda: "article-theme")
    problems = browsercheck.check(built)
    assert problems == [
        (
            "the page served is book-theme, and myst.yml declares article-theme, so nothing "
            "measured here describes article-theme"
        ),
    ]


def test_an_unrecognised_page_is_refused_rather_than_measured(
    monkeypatch,
    built: Path,
) -> None:
    monkeypatch.setattr(browsercheck, "visit", lambda url: ([], 17, "<html></html>"))
    monkeypatch.setattr(browsercheck, "declared_template", lambda: "article-theme")
    assert "unknown template" in browsercheck.check(built)[0]


def test_a_template_the_markers_do_not_cover_is_refused(
    monkeypatch,
    built: Path,
) -> None:
    monkeypatch.setattr(browsercheck, "visit", lambda url: ([], 17, ARTICLE))
    monkeypatch.setattr(browsercheck, "declared_template", lambda: None)
    assert "no single known site template" in browsercheck.check(built)[0]


def test_the_site_is_served_under_the_base_path_pages_builds_it_for(
    tmp_path: Path,
) -> None:
    """The Pages build prefixes every asset with BASE_URL, so the check serves the site under
    that prefix; served at the root, every asset answered 404 in CI (2026-09-24)."""
    (tmp_path / "theme.css").write_text("body {}", encoding="utf-8")
    with browsercheck.serving(tmp_path, "/econ-scenarios") as origin:
        assert origin.endswith("/econ-scenarios")
        with urllib.request.urlopen(f"{origin}/theme.css") as answer:
            assert answer.read() == b"body {}"
        root = origin.removesuffix("/econ-scenarios")
        with pytest.raises(urllib.error.HTTPError):
            urllib.request.urlopen(f"{root}/other/theme.css")


def test_a_missing_build_is_an_error_rather_than_a_pass(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="build the site first"):
        browsercheck.check(tmp_path / "nowhere")


def test_a_page_that_renders_without_a_launch_control_draws_no_complaint(
    monkeypatch, built: Path
) -> None:
    monkeypatch.setattr(browsercheck, "visit", lambda url: ([], 0, ARTICLE))
    assert browsercheck.check(built) == []


def test_a_thrown_error_and_a_launch_control_are_each_reported(
    monkeypatch, built: Path
) -> None:
    """The live site on 2026-09-24: a launch button whose click threw."""
    monkeypatch.setattr(
        browsercheck,
        "visit",
        lambda url: (["TypeError: Failed to construct 'URL': Invalid URL"], 1, ARTICLE),
    )
    problems = browsercheck.check(built)
    assert any("Failed to construct" in p for p in problems)
    assert any("launch control" in p for p in problems)


def test_the_same_error_twice_is_reported_once(monkeypatch, built: Path) -> None:
    """A React error boundary logs its throw on every re-render, so the console repeats it."""
    monkeypatch.setattr(
        browsercheck,
        "visit",
        lambda url: (["boom", "boom"], 0, ARTICLE),
    )
    assert browsercheck.check(built) == [
        "reproduction-appendix threw 'boom' while rendering, which stops the page",
    ]


def test_a_browser_that_will_not_start_is_reported_rather_than_passed(
    monkeypatch,
    built: Path,
) -> None:
    """The failure mode this check exists to avoid, turned on the check itself.

    A missing Chrome makes ``visit`` raise. Swallowing that would return an empty problem list,
    which reads exactly like a page whose cells run.
    """

    def _raise(url: str) -> None:
        msg = "Executable doesn't exist"
        raise PlaywrightError(msg)

    monkeypatch.setattr(browsercheck, "visit", _raise)
    problems = browsercheck.check(built)
    assert problems
    assert "nothing ran" in problems[0]


@pytest.mark.parametrize(
    ("strict", "code"),
    [(False, 0), (True, 1)],
)
def test_strict_decides_whether_a_finding_fails_the_build(
    monkeypatch,
    built: Path,
    strict: bool,
    code: int,
) -> None:
    """A warning by default, and a failure under --strict, which is how site.sh runs it."""
    monkeypatch.setattr(browsercheck, "visit", lambda url: (["boom"], 0, ARTICLE))
    argv = [str(built), *(["--strict"] if strict else [])]
    assert browsercheck.main(argv) == code


def test_a_clean_run_exits_zero_under_strict(monkeypatch, built: Path) -> None:
    monkeypatch.setattr(browsercheck, "visit", lambda url: ([], 0, ARTICLE))
    assert browsercheck.main([str(built), "--strict"]) == 0
