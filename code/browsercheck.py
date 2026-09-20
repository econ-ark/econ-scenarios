"""Check that the supplement's cells still run in a reader's browser.

The supplement is online only, and its point is that the reader edits a cell and re-runs it.
The checks here stop at the file on disk. ``myst build`` exits 0, the pages and assets are
written, and ``sitecheck`` finds the stylesheet and the equations sound, while the page itself
is dead on arrival. That was the state of this site for a week, because the failure is a
JavaScript exception thrown while the page renders, which only a browser sees.

So this one does. It serves the built site over HTTP, because JupyterLite needs a real origin,
loads the supplement, and reports what a reader would find: an uncaught exception, or no control
to run a cell with.

It warns rather than fails by default. The theme's own launch control throws today
(``LaunchBinder`` builds a URL from thebe's ``"/"`` sentinel), which is upstream and not
something a release here can fix, and a gate that is red for a reason nobody can act on stops
being read. ``--strict`` turns the same findings into a nonzero exit, which is what this should
run as once the theme is fixed.

Usage: ``python -m browsercheck [_build/html] [--strict] [--page reproduction-appendix]``
"""

from __future__ import annotations

import argparse
import contextlib
import functools
import http.server
import logging
import re
import socket
import socketserver
import sys
import threading
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

log = logging.getLogger("browsercheck")

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "_build" / "html"
# The supplement, the one page whose cells are meant to run. The report is a PDF-first article
# whose cells are all static, so checking it would assert nothing.
PAGE = "reproduction-appendix"
# Long enough for Pyodide to come down and thebe to draw its controls on a cold cache, and short
# enough that a broken page reports in a minute and a half.
READY_MS = 90_000
# A class each site template renders and the other one never does, measured 2026-09-18 by
# diffing one page's class names built both ways. A stale build of the WRONG template renders a
# page that looks right and never names the template that made it; one was measured here for an
# hour before a drifting button label gave it away.
MARKERS = {"article-theme": "article-left-grid", "book-theme": "myst-toc-item"}
TEMPLATE = re.compile(r"^\s+template:\s*(\S+)\s*$", re.MULTILINE)
# A reader starts the kernel here, and one theme puts the label in title= while the other puts
# it in the button's text. The crash this check exists for fires on that click, so a check that
# only opens the page sees a healthy one (measured on the live site, 2026-09-18).
LAUNCH = (
    "button[title*='compute session' i], button[title*='launch kernel' i], "
    "button:has-text('Launch kernel')"
)
# What thebe renders for a runnable cell once the kernel is up.
CONTROLS = "button[title*='run cell' i], button[title*='run all' i]"


class Quiet(http.server.SimpleHTTPRequestHandler):
    """A static handler that does not narrate every asset request."""

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002, ARG002
        return


@contextlib.contextmanager
def serving(html: Path):
    """The built site on a loopback port, for as long as the block runs."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    handler = functools.partial(Quiet, directory=str(html))
    with socketserver.TCPServer(("127.0.0.1", port), handler) as httpd:
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{port}"
        finally:
            httpd.shutdown()


def declared_template(root: Path = ROOT) -> str | None:
    """The site template ``myst.yml`` names, or None where it names anything but one."""
    found = TEMPLATE.findall((root / "myst.yml").read_text(encoding="utf-8"))
    return found[0] if len(found) == 1 else None


def visit(url: str) -> tuple[list[str], int, str]:
    """Load ``url`` in Chrome and report its uncaught exceptions, run controls and page HTML."""
    thrown: list[str] = []
    with sync_playwright() as play:
        # The system Chrome, so no browser download: this has to run on a laptop and in CI.
        browser = play.chromium.launch(channel="chrome")
        page = browser.new_page()
        page.on("pageerror", lambda exc: thrown.append(str(exc).split("\n")[0]))
        # React catches a throw from a component's render in an error boundary, so the one that
        # kills this page never reaches pageerror. It reaches the console instead, which is why
        # the first run of this check reported dead controls with the cause missing.
        page.on(
            "console",
            lambda msg: (
                thrown.append(msg.text.split("\n")[0]) if msg.type == "error" else None
            ),
        )
        page.goto(url, wait_until="networkidle")
        # Start the kernel the way a reader does. Without this the page looks healthy: the
        # published site answers, draws its controls, and logs nothing until the click.
        with contextlib.suppress(PlaywrightError):
            page.click(LAUNCH, timeout=READY_MS)
        with contextlib.suppress(PlaywrightError):
            page.wait_for_selector(CONTROLS, timeout=READY_MS, state="attached")
        controls = page.locator(CONTROLS).count()
        served = page.content()
        browser.close()
    return thrown, controls, served


def check(html: Path = HTML, page: str = PAGE, url: str | None = None) -> list[str]:
    """Every complaint about running the supplement, empty when a reader could run it.

    ``url`` checks a site that is already served, which is how this is pointed at the published
    one; otherwise the built directory is served here.
    """
    problems = []
    if not url and not html.is_dir():
        msg = f"{html} does not exist; build the site first"
        raise RuntimeError(msg)
    try:
        if url:
            thrown, controls, served = visit(url)
        else:
            with serving(html) as origin:
                thrown, controls, served = visit(f"{origin}/{page}/")
    except PlaywrightError as exc:
        # A machine without Chrome cannot answer the question, so it says that instead. A check
        # that comes back clean when it never ran does more damage than one nobody wrote.
        return [
            f"the browser would not start ({str(exc).splitlines()[0]}), so nothing ran",
        ]
    # Which build answered, before a word is said about what it does. Everything below describes
    # the theme under test, and describes it wrongly if some other build is on the port.
    declared = declared_template()
    if declared not in MARKERS:
        return [
            f"myst.yml names no single known site template, so {page} was left unmeasured",
        ]
    if MARKERS[declared] not in served:
        others = [t for t, mark in MARKERS.items() if mark in served]
        return [
            f"the page served is {others[0] if others else 'from an unknown template'}, and "
            f"myst.yml declares {declared}, so nothing measured here describes {declared}",
        ]
    for exc in dict.fromkeys(thrown):
        problems.append(f"{page} threw {exc!r} while rendering, which stops the page")
    if not controls:
        problems.append(
            f"{page} drew no control a reader could run a cell with, so its cells are dead",
        )
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check that the supplement's cells can run.",
    )
    parser.add_argument("html", nargs="?", default=str(HTML))
    parser.add_argument("--page", default=PAGE)
    parser.add_argument(
        "--url",
        help="check a served page instead of a built directory",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit nonzero on what is otherwise reported as a warning",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    problems = check(Path(args.html), args.page, args.url)
    for problem in problems:
        sys.stderr.write(f"{'' if args.strict else 'warning: '}{problem}\n")
    if problems:
        return 1 if args.strict else 0
    log.info("%s runs its cells in a browser", args.page)
    return 0


if __name__ == "__main__":
    sys.exit(main())
