"""Check that the supplement renders in a reader's browser, and fail on a launch control.

The checks here stop at the file on disk. ``myst build`` exits 0, the pages and assets are
written, and ``sitecheck`` finds the stylesheet and the equations sound, while the page itself
can be dead on arrival. That was the state of this site for a week, because the failure is a
JavaScript exception thrown while the page renders, which only a browser sees.

So this one does. It serves the built site over HTTP, loads the supplement, and reports what a
reader would find: an uncaught exception, or a launch control. article-theme's launch control
throws on the click (``LaunchBinder`` builds a URL from thebe's ``"/"`` sentinel,
jupyter-book/myst-theme#955), so the site sets no ``jupyter`` key, and any value there, ``lite:
false`` included, brings the control back (measured 2026-09-24). The cells' outputs come from
the build, which executes them.

``--strict`` turns the findings into a nonzero exit, which is how ``site.sh`` runs it.

Usage: ``python -m browsercheck [_build/html] [--strict] [--page reproduction-appendix]``
"""

from __future__ import annotations

import argparse
import contextlib
import functools
import http.server
import logging
import os
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
# The supplement, the one page with code cells. The report is a PDF-first article whose cells
# are all static, so checking it would assert nothing.
PAGE = "reproduction-appendix"
# A class each site template renders and the other never does (measured 2026-09-18). A stale
# build of the WRONG template renders a page that looks right and never names its template; one
# was measured here for an hour before a drifting button label gave it away.
MARKERS = {"article-theme": "article-left-grid", "book-theme": "myst-toc-item"}
TEMPLATE = re.compile(r"^\s+template:\s*(\S+)\s*$", re.MULTILINE)
# The launch control, which one theme labels in title= and the other in the button's text.
LAUNCH = (
    ".myst-jp-btn-binder, .myst-jp-btn-launch-binder, "
    "button[title*='compute session' i], button[title*='launch kernel' i], "
    "button:has-text('Launch kernel')"
)


class Quiet(http.server.SimpleHTTPRequestHandler):
    """A static handler that does not narrate every asset request, serving the site under
    ``base``, the path prefix a project page has on GitHub Pages."""

    base = ""

    def translate_path(self, path: str) -> str:
        if self.base and (path == self.base or path.startswith(self.base + "/")):
            path = path[len(self.base) :] or "/"
        return super().translate_path(path)

    def log_message(self, format: str, *args: object) -> None:
        return


@contextlib.contextmanager
def serving(html: Path, base: str = ""):
    """The built site on a loopback port under ``base``, for as long as the block runs.

    The Pages workflow builds with ``BASE_URL`` set to the repository's name, so every asset
    URL in the page carries that prefix; served at the root instead, each one answers 404
    (measured in CI, 2026-09-24).
    """
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    mounted = type("Mounted", (Quiet,), {"base": base.rstrip("/")})
    handler = functools.partial(mounted, directory=str(html))
    with socketserver.TCPServer(("127.0.0.1", port), handler) as httpd:
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{port}{base.rstrip('/')}"
        finally:
            httpd.shutdown()


def declared_template(root: Path = ROOT) -> str | None:
    """The site template ``myst.yml`` names, or None where it names anything but one."""
    found = TEMPLATE.findall((root / "myst.yml").read_text(encoding="utf-8"))
    return found[0] if len(found) == 1 else None


def visit(url: str) -> tuple[list[str], int, str]:
    """Load ``url`` in Chrome and report its uncaught exceptions, launch controls and HTML."""
    thrown: list[str] = []
    with sync_playwright() as play:
        # The system Chrome, so no browser download: this has to run on a laptop and in CI.
        browser = play.chromium.launch(channel="chrome")
        page = browser.new_page()
        page.on("pageerror", lambda exc: thrown.append(str(exc).split("\n")[0]))
        # React catches a render throw in an error boundary, so it never reaches pageerror; it
        # reaches the console. "Failed to load resource" is skipped there, as it lacks the URL.
        page.on(
            "console",
            lambda msg: (
                thrown.append(msg.text.split("\n")[0])
                if msg.type == "error"
                and not msg.text.startswith("Failed to load resource")
                else None
            ),
        )
        # A failed request, recorded here with the URL that failed.
        page.on(
            "response",
            lambda r: (
                thrown.append(f"{r.status} for {r.url}") if r.status >= 400 else None
            ),
        )
        page.goto(url, wait_until="networkidle")
        launches = page.locator(LAUNCH).count()
        served = page.content()
        browser.close()
    return thrown, launches, served


def check(html: Path = HTML, page: str = PAGE, url: str | None = None) -> list[str]:
    """Every complaint about the supplement in a browser, empty when it renders cleanly.

    ``url`` checks a site that is already served, which is how this is pointed at the published
    one; otherwise the built directory is served here.
    """
    problems = []
    if not url and not html.is_dir():
        msg = f"{html} does not exist; build the site first"
        raise RuntimeError(msg)
    try:
        if url:
            thrown, launches, served = visit(url)
        else:
            with serving(html, os.environ.get("BASE_URL", "")) as origin:
                thrown, launches, served = visit(f"{origin}/{page}/")
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
            (
                f"the page served is {others[0] if others else 'from an unknown template'}, and "
                f"myst.yml declares {declared}, so nothing measured here describes {declared}"
            ),
        ]
    for exc in dict.fromkeys(thrown):
        problems.append(f"{page} threw {exc!r} while rendering, which stops the page")
    if launches:
        problems.append(
            f"{page} draws a launch control, which throws on the click; drop the jupyter key "
            "from myst.yml",
        )
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check that the supplement renders in a browser without a launch control.",
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
    log.info("%s renders in a browser with no launch control", args.page)
    return 0


if __name__ == "__main__":
    sys.exit(main())
