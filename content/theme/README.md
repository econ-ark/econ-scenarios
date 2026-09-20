# The Econ-ARK house theme

Nothing from the theme is copied into this repository. `econ-ark/econ-ark-myst` is a submodule at
the repository root, `myst.yml` points at it by path, and the recorded commit is the pin.

| What | Where it comes from |
| --- | --- |
| The stylesheet, logos, favicon and banner | `econ-ark-myst/`, read by path from `myst.yml` |
| The site's woff2 | `econ-ark-myst/fonts`, written by `econ-ark-myst/scripts/fonts.sh webfonts` |
| The Typst template for the PDF | the theme's public URL, named in each page's `exports:` block |
| The face the figures are drawn in | `econ-ark-myst/fonts`, the TrueType pair the same script copies out, since matplotlib cannot read a woff2 |

`local.css` holds the one rule the house sheet has no reason to carry, the height a quiz iframe
needs, since MyST gives an iframe a fixed aspect ratio that cuts the questions off partway
down. `style:` takes a single path, so `code/theme.py` writes `site.css` from the submodule's
sheet plus that rule and `myst.yml` names the result. `site.css` is generated, so it is not
tracked, and `reproduce.sh` writes it.

## Updating

A submodule records a commit, and `-b main` does not make a newer one arrive. Moving the pointer
is a step someone takes:

```bash
git submodule update --remote econ-ark-myst   # moves the recorded commit; commit the change
./econ-ark-myst/scripts/fonts.sh webfonts     # the fonts are generated, not tracked
(cd code && uv run python -m theme --write)   # the stylesheet is generated too
```

A plain `git clone` of this repository leaves the submodule empty, and `reproduce.sh` initialises
it. If that fails, MyST falls back to its own look, and every number, table and test is
identical. Theme reproduction is not scientific reproduction.

## Two failures that exit 0

`code/sitecheck.py` runs after every build and catches both. Checking the exit code catches
neither.

The equations are set in Fira Math by a MyST plugin that re-renders them as MathML, because
KaTeX paints glyphs at precomputed positions and no stylesheet can restyle them. When the plugin
fails to load, MyST quietly reverts to KaTeX and the equations come out in a different face from
the page around them. Take `plugins/fira-math.bundle.mjs` and not `fira-math.mjs`: the unbundled
source imports `temml` and `js-yaml`, which resolve against nothing once MyST has copied the file
into its cache.

A stylesheet that asks for a font the build never published leaves every reader in a system
face. `scripts/fonts.sh webfonts` writes every face the site and the figures need, `temml.css`
and `Temml.woff2` among them, so the check is what says the script ran.
