"""Import this repository's code in a JupyterLite kernel from the files the report's website serves.

The report's pages run in two places. A local build (``myst build --execute``) runs them in a
Jupyter kernel with ``code/`` on the path. In the browser (JupyterLite, on Pyodide) there is no
repository, but ``myst.yml`` publishes ``code/econ_scenarios``, ``code/validation`` and the
modules in ``MODULES`` at the site's root through ``static_files``. ``install`` adds an import
hook that reads them from there, so the browser runs the same files the tests run.
"""

from __future__ import annotations

import importlib.abc
import importlib.util
import sys
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from matplotlib import font_manager

if TYPE_CHECKING:
    from importlib.machinery import ModuleSpec
    from types import ModuleType

try:
    import js  # Pyodide's bridge to the browser
    import micropip
    from pyodide.http import pyfetch
except ImportError:
    js = None
    micropip = None
    pyfetch = None

PACKAGES = ("econ_scenarios", "validation")
MODULES = ("explore", "figures", "pages", "tables", "theme", "exhibits")
# The figures' typeface (theme.FONT_FILES), served from the theme submodule's fonts/ at the
# site's /fonts/. matplotlib cannot read a woff2, which is why the pair is TrueType.
FONTS = ("FiraSans-Regular.ttf", "FiraSans-Medium.ttf")
FONT_CACHE = Path("/tmp/econ-scenarios-fonts")

Fetch = Callable[[str], "str | None"]


def fetch_from_site(path: str) -> str | None:
    """The text at ``path`` relative to the site's root, or None when the site does not serve it."""
    if js is None:
        msg = "fetch_from_site runs in Pyodide; in a local kernel put code/ on sys.path"
        raise RuntimeError(
            msg,
        )
    request = js.XMLHttpRequest.new()
    request.open(
        "GET",
        path,
        False,
    )  # synchronous requests are allowed in the kernel's web worker
    request.send(None)
    return str(request.responseText) if request.status == 200 else None


class ServedSource(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """Finds this repository's modules among served files: ``pkg/__init__.py`` for a package in
    ``PACKAGES``, ``pkg/name.py`` for its modules, and ``name.py`` for a module in ``MODULES``.
    """

    def __init__(
        self,
        fetch: Fetch,
        packages: tuple[str, ...] = PACKAGES,
        modules: tuple[str, ...] = MODULES,
    ) -> None:
        self.fetch = fetch
        self.packages = frozenset(packages)
        self.modules = frozenset(modules)

    def find_spec(self, fullname: str, path=None, target=None) -> ModuleSpec | None:
        top, _, rest = fullname.partition(".")
        if top in self.packages:
            is_package = not rest
            file = (
                f"{top}/__init__.py"
                if is_package
                else f"{fullname.replace('.', '/')}.py"
            )
        elif fullname in self.modules:
            is_package, file = False, f"{fullname}.py"
        else:
            return None
        source = self.fetch(file)
        if source is None:
            return None
        spec = importlib.util.spec_from_file_location(
            fullname,
            file,
            loader=self,
            submodule_search_locations=[] if is_package else None,
        )
        if spec is not None:
            spec.loader_state = source
            if is_package:
                # spec_from_file_location fills an empty search path with the file's directory, which
                # is relative here and would let a path finder pick up same-named files from the
                # working directory; an empty path leaves the package's submodules to this finder
                spec.submodule_search_locations = []
        return spec

    def create_module(self, spec: ModuleSpec) -> None:
        return None  # the default module object

    def exec_module(self, module: ModuleType) -> None:
        spec = module.__spec__
        if spec is None or spec.origin is None:
            msg = f"{module.__name__} has no served source"
            raise ImportError(msg)
        # dont_inherit: the served file's own __future__ imports apply, never this module's
        exec(
            compile(spec.loader_state, spec.origin, "exec", dont_inherit=True),
            module.__dict__,
        )


def install(fetch: Fetch = fetch_from_site) -> ServedSource:
    """Put a ``ServedSource`` first on ``sys.meta_path``, once."""
    for finder in sys.meta_path:
        if isinstance(finder, ServedSource):
            return finder
    finder = ServedSource(fetch)
    sys.meta_path.insert(0, finder)
    return finder


async def install_fonts(directory: Path = FONT_CACHE) -> None:
    """Fetch the figures' typeface from the site and register it with matplotlib."""
    if pyfetch is None:
        msg = "install_fonts runs in Pyodide; locally theme.register_fonts reads theme.FONT_DIR"
        raise RuntimeError(
            msg,
        )
    directory.mkdir(parents=True, exist_ok=True)
    for name in FONTS:
        response = await pyfetch(f"fonts/{name}")
        if not response.ok:
            msg = f"the site does not serve fonts/{name} (status {response.status})"
            raise RuntimeError(
                msg,
            )
        path = directory / name
        path.write_bytes(await response.bytes())
        font_manager.fontManager.addfont(str(path))


async def prepare(widgets: bool = False) -> None:
    """Everything a page needs in the browser: the import hook, the figures' typeface, and
    ipywidgets when asked for.
    """
    install()
    await install_fonts()
    if widgets:
        if micropip is None:
            msg = (
                "prepare(widgets=True) runs in Pyodide; locally, install the docs group"
            )
            raise RuntimeError(
                msg,
            )
        await micropip.install("ipywidgets")
