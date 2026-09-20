# Reproducing "Economic Scenarios for Transformative AI"

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22839070.svg)](https://doi.org/10.5281/zenodo.22839070)

An Econ-ARK REMARK by Alan Lujan.

Korinek, Jones, Sacher, Cotter, and McCrory (2026), "Economic Scenarios for Transformative AI",
here the economic scenarios, build a monthly model of how AI could change output, wages, capital,
and employment between 2024 and 2030 under three scenarios: modest, substantial, and extreme. It
gives paths for the wage in cognitive work, the wage in all other work, the rental rate of
capital, and the transition probabilities among four employment states, all relative to an
economy without AI. The paper publishes 226 numbers and an explorer that runs the model in the
browser.

## The article

`content/reproduction.md` rebuilds that model in plain Python and numpy from the paper's Appendix
A, the 44 equations of its Table A.1, and the calibration of its Table 1. It asks how closely the
rebuild reproduces the paper and the explorer, how much each check establishes, and what the text
leaves a reader to supply. It matches the explorer in every series and every month to
within 3.5e-14 on 25 configurations, and reproduces all 226 published numbers that public inputs
allow, within the printed rounding, once it runs on the unrounded calibration the explorer
records. Planted errors show both checks reject a wrong model, and that the errors the tables
alone miss move no published number by more than 0.07. The one open choice in the text that moves
a published number is whether quit fractions become continuous rates before or after the split
into the part that responds to job prospects and the rest.

`content/reproduction-appendix.md` holds the equations beside the module that evaluates each,
every published number next to the reproduction's value, the paper's figures regenerated, the
details of both checks, a recheck of the calibration's public data, and a small explorer whose
cells run in the reader's browser.

## Running it

You need Python 3.13, [uv](https://docs.astral.sh/uv/), git, and network access for the public
data behind the calibration rechecks, which the script downloads into `sources/upstream/`
(gitignored) before the tests. The two inputs bls.gov withholds from scripts are tracked under
`code/validation/data/` with their provenance.

```bash
./reproduce.sh        # uv sync, the three fetchers, pytest, myst build --html --execute
./reproduce_min.sh    # the quick path: model identities, tables, quit order
```

`uv sync` installs the environment pinned in `uv.lock`. The suite gates every table, figure, and
quoted decimal of both pages on what the code computes now. The build writes `_build/html`; `uv
run myst start` serves it locally. Minutes end to end, since nothing here solves a household.

`pyproject.toml` and `uv.lock` state the environment. This REMARK carries no
`binder/environment.yml`, which the standard lists among its required files: a conda file here
could only bootstrap uv and hand straight back to the lockfile, adding a second place to state
the environment while pinning nothing the lockfile does not. The `Dockerfile`
builds from `python:3.13-slim` and runs `reproduce.sh`; `.github/workflows/` runs it on every
push and publishes the site to GitHub Pages.

## Layout

```
content/    reproduction.md and its supplement, the generated fragments/ and figures/ they
            include, references.bib, theme/ (local.css and the econ-ark-myst submodule,
            which carries every face)
code/
  econ_scenarios/   the monthly model in numpy: paths, production, labor, simulate, calibration
  validation/       published.py (the 226 numbers as printed), oracle.py and compare.py (against
                    the explorer's recorded run), plants.py and resolution.py (planted errors and
                    what each check detects), upstream_*.py (the public data), data/ (the two
                    extracts bls.gov withholds from scripts), explorer_record.json.gz
  cleanroom/        a second implementation, written from the paper's PDF alone
  tests/            the gates, below
  tables.py, figures.py, theme.py    shared with the other papers built on this model
  explore.py, pages.py, exhibits.py, kernel.py    what the supplement's cells run
myst.yml    the site
```

## The tests

`uv run pytest -q` runs every gate. Among them:

- `test_model.py`: internal identities that hold whatever the explorer or the tables say, among
  them the market clearing the bisection solves and the accounting tying output to factor payments.
- `test_tables.py`, `test_quit_order.py`: the 226 published numbers within their printed
  rounding, and the quit order those tables require is the one the explorer uses.
- `test_text_claims.py`: the article's claims about the paper's text, against its own equations.
- `test_oracle.py`, `test_explorer.py`: the model against the explorer, series by series and
  month by month. The explorer's outputs are recorded in `validation/explorer_record.json.gz`,
  made by running its own JavaScript under node against a pinned sha256; it carries no license,
  so none of its code is here and the tests read the record.
- `test_rejection.py`: every planted error is caught above, which is what makes that agreement
  evidence rather than coincidence.
- `test_cleanroom.py`: the model against a second implementation written from the PDF alone,
  agreeing to 6e-14 once the open quit order is aligned.
- `test_upstream_*.py`: the public data behind the calibration, against its original sources.
- `test_pages.py`: every included table is the fragment the code writes now, every quoted decimal
  and date is a value it computes, and each stands in its own sentence; a swapped pair fails.
- `test_explore.py`, `test_kernel.py`, `test_theme.py`: the Explore controls reproduce the
  scenarios, the browser kernel serves this repository's files and only those, and the site's
  theme is the figures'.
- `test_figures.py`: the figures render with no overlapping text, and the overlap check itself
  can fail.
- `test_sitecheck.py`: the built site is checked for the two theme failures that exit 0, a
  stylesheet asking for a font the site does not serve and an equation left in KaTeX.
- `test_browsercheck.py`: the supplement is opened in a browser and its kernel started, so a
  page whose cells a reader cannot run is reported before it is published.
- `test_download.py`: a host answering 5xx is asked again. An answer about the request itself,
  a 404 or a 429, is raised on the first try.

## Regenerating tables and figures

From `code/`:

```bash
uv run python -m validation.gate        # the explorer comparison and every planted error
uv run python -m pages --write          # every table of the article and its supplement
uv run python -m pages --check          # fail if any table is stale
uv run python -m exhibits               # the article's figures
uv run python -m figures                # the paper's figures regenerated from the model
```

Each fragment's first line names the module that writes it and the command that regenerates it.

## Detection thresholds

Each check answers a different question. The explorer comparison holds the model to a full
monthly path, so it detects any error that moves a series at all; what it establishes is
agreement with the authors' implementation. Published tables hold the model to 226 numbers at
their printed precision, so they establish agreement with what the paper reports, down to half
a printed digit and no further. Planted errors measure the gap between the two directly: every
one of them fails the explorer comparison, a minority survive the tables, and the largest
published-number change any survivor produces is 0.07. For each published series the article
states the detection threshold.

Two published numbers need inputs the paper does not publish and are therefore out of scope
here. The article lists them, along with the places where the paper's text and its tables
differ.

## Relation to the economic scenarios and their explorer

The reproduction takes the economic scenarios' paper as its authoritative description. Where the
paper's text leaves a detail open, the reproduction records the choice the authors' explorer
makes and shows whether the published tables require it. The equations and the mechanisms are
the paper's throughout.

## Citing

See `CITATION.cff`. The economic scenarios are Korinek, Jones, Sacher, Cotter, and McCrory
(2026), "Economic Scenarios for Transformative AI".

## License

The code is under the MIT License, in `LICENSE`. The text, tables, and figures are under
Creative Commons Attribution 4.0 International (CC BY 4.0). The Fira Sans, Fira Mono and Fira
Math faces come from the `econ-ark-myst` submodule, under the SIL Open Font License its own
repository states.

## Contact

Alan Lujan, Johns Hopkins University, alujan@jhu.edu. Corrections and questions are welcome
as issues on this repository; any mistake in the reproduction is mine.
