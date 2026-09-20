"""The site check's own logic, on fixtures rather than on a real build.

It replaced a unit test that compared the stylesheet against ``fonts.MANIFEST``. That comparison
stopped meaning anything once the site's faces came from the submodule's build script instead of
our manifest, and checking the built site is the stronger question anyway: it asks what a reader
will actually be served.
"""

import pytest
import sitecheck


def site(tmp_path, css: str, pages: dict[str, str], assets=()):
    """A directory shaped like a built site: one stylesheet, some pages, some served assets."""
    (tmp_path / "myst-theme.css").write_text(css, encoding="utf-8")
    fonts = tmp_path / "fonts"
    fonts.mkdir()
    for name in assets:
        (fonts / name).write_bytes(b"x")
    for name, text in pages.items():
        (tmp_path / name).write_text(text, encoding="utf-8")
    return tmp_path


def test_a_sound_site_has_nothing_to_report(tmp_path) -> None:
    html = site(
        tmp_path,
        '@font-face { src: url("fonts/A.woff2"); }',
        {"p.json": '{"html": "<math><mi>x</mi></math>"}'},
        assets=("A.woff2",),
    )
    assert sitecheck.check(html) == []


def test_a_font_the_sheet_asks_for_and_the_site_lacks_is_reported(tmp_path) -> None:
    """The failure that put every reader in a system face twice, both times exiting 0."""
    html = site(
        tmp_path,
        '@font-face { src: url("fonts/Missing.woff2"); }',
        {"p.json": '{"html": "<math><mi>x</mi></math>"}'},
    )
    problems = sitecheck.check(html)
    assert any("Missing.woff2" in p for p in problems), problems


def test_equations_left_in_katex_are_reported(tmp_path) -> None:
    """A plugin that fails to load drops MyST back to KaTeX, in a face the page does not use."""
    html = site(
        tmp_path,
        "body { color: black; }",
        {"p.json": '{"html": "<span class=\\"katex\\">x</span>"}'},
    )
    problems = sitecheck.check(html)
    assert any("KaTeX" in p for p in problems), problems


def test_a_site_with_no_mathml_at_all_is_reported(tmp_path) -> None:
    html = site(
        tmp_path,
        "body { color: black; }",
        {"p.json": '{"html": "<p>text</p>"}'},
    )
    assert any("no built page carries MathML" in p for p in sitecheck.check(html))


def test_a_data_uri_is_not_mistaken_for_a_missing_asset(tmp_path) -> None:
    """The house sheet embeds the Econ-ARK mark as a data URI, which is served by definition."""
    html = site(
        tmp_path,
        'div { background: url("data:image/png;base64,iVBORw0KGgo="); }',
        {"p.json": '{"html": "<math><mi>x</mi></math>"}'},
    )
    assert sitecheck.check(html) == []


def test_an_absent_build_directory_is_an_error(tmp_path) -> None:
    with pytest.raises(RuntimeError, match="does not exist"):
        sitecheck.check(tmp_path / "never-built")


def test_a_site_without_a_stylesheet_is_an_error(tmp_path) -> None:
    """MyST names the published sheet, so its absence means the build shape changed."""
    (tmp_path / "p.json").write_text("{}", encoding="utf-8")
    with pytest.raises(RuntimeError, match="no published stylesheet"):
        sitecheck.check(tmp_path)
