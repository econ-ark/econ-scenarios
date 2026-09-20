"""Check a built site for the two theme failures that exit 0 and tell nobody.

Both were found the hard way. A stylesheet that asks for a font the build never published leaves
every reader in a system face, and the build reports success. The Fira Math plugin re-renders
each equation as MathML, and when it fails to load, MyST falls back to KaTeX and the equations
come out in a different typeface from the page, again with a clean exit.

Neither is a scientific error: no number moves. Both are invisible without a check, which is why
this reads the built artifact rather than the build log. ``reproduce.sh`` runs it after the build.

Usage: ``python -m sitecheck [_build/html]``
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path

log = logging.getLogger("sitecheck")

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "_build" / "html"
# Any url() in the published sheet, which is what a browser will actually ask for.
ASSET_URL = re.compile(r"url\(\s*[\"']?(?!data:)/?([^\"')]+)[\"']?\s*\)")
# KaTeX leaves its own class names in the rendered page; Temml leaves MathML elements.
KATEX = re.compile(r"katex")
MATHML = re.compile(r"<math[\s>]")


def sheet(html: Path) -> Path:
    """The stylesheet the site serves, whatever MyST decided to call it."""
    for name in ("myst-theme.css", "site.css"):
        candidate = html / name
        if candidate.is_file():
            return candidate
    msg = f"no published stylesheet under {html}"
    raise RuntimeError(msg)


def dangling(html: Path) -> list[str]:
    """Assets the published stylesheet asks for that the site does not serve.

    This is the general form of a bug that has already happened twice here: a face renamed in a
    font swap, and Temml's own woff2, which its stylesheet asks for and the theme's build script
    does not produce.
    """
    css = sheet(html)
    out = []
    for asked in sorted(set(ASSET_URL.findall(css.read_text(encoding="utf-8")))):
        if asked.startswith(("http://", "https://", "#")):
            continue
        if not (html / asked).is_file() and not (css.parent / asked).is_file():
            out.append(asked)
    return out


def equations(html: Path) -> tuple[int, int]:
    """How many pages carry MathML, and how many still carry KaTeX markup."""
    mathml = katex = 0
    for page in html.rglob("*.json"):
        text = page.read_text(encoding="utf-8", errors="replace")
        if MATHML.search(text):
            mathml += 1
        if KATEX.search(text):
            katex += 1
    return mathml, katex


def check(html: Path = HTML) -> list[str]:
    """Every complaint about the built site, empty when it is sound."""
    if not html.is_dir():
        msg = f"{html} does not exist; build the site first"
        raise RuntimeError(msg)
    problems = []
    missing = dangling(html)
    if missing:
        problems.append(
            f"the published stylesheet asks for {missing}, which the site does not serve",
        )
    mathml, katex = equations(html)
    if katex:
        problems.append(
            f"{katex} built pages still carry KaTeX markup, so the Fira Math plugin did not run",
        )
    if not mathml:
        problems.append("no built page carries MathML, so no equation was re-rendered")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check a built site's theme assets.")
    parser.add_argument("html", nargs="?", default=str(HTML))
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    problems = check(Path(args.html))
    for problem in problems:
        sys.stderr.write(f"{problem}\n")
    if problems:
        return 1
    log.info(
        "%s serves every asset its stylesheet asks for, with MathML equations",
        args.html,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
