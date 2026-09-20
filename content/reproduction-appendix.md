---
title: Supplement to Reproducing “Economic Scenarios for Transformative AI”
short_title: Reproduction, Supplement
kernelspec:
  name: python3
  display_name: Python 3
 # Online only. Supplements carry S-numbered figures and tables, hence the enumerators below.
numbering:
  figure:
    enumerator: S%s
  table:
    enumerator: S%s
---

This supplement to [Reproducing “Economic Scenarios for Transformative AI”](reproduction.md) holds the model's equations with the module that evaluates each, every published number beside the reproduction's value, the paper's figures regenerated from the reproduction, the details of the two checks, the remaining notes on the paper and its data, and a small version of the authors' explorer, the web page that runs their model in the reader's browser. The supplement's code cells are executable.

## Running the Code

Every output on this page was computed when the site was built, from the same files that the test suite runs. The cells can also run in your browser once the compute button at the top of the page starts a Python kernel with JupyterLite, which installs nothing on your computer and fetches the code from this site. That button appears once the article theme's launch control supports JupyterLite, which [myst-theme pull request 955](https://github.com/jupyter-book/myst-theme/pull/955) adds. To run everything locally instead:

```bash
uv sync
uv run pytest
uv run myst build --html --execute
```

From `code/`, the command `uv run python -m validation.gate` runs both checks and every planted-error test. Refreshing the explorer record after the authors redeploy their page needs Node.js, as `code/validation/oracle.py` describes. The second implementation of the article's third comparison, written from the paper's text alone, is `code/cleanroom`. The module `code/validation/cleanroom.py` compares it with the reproduction path by path, and `code/tests/test_cleanroom.py` holds the tests that isolate the quit order as their only difference.

```{code-cell} python
:tags: [hide-input]
# Make the repository's code importable. A local build runs this page in a Jupyter kernel beside
# the repository; in the browser, JupyterLite reads the same files from this website and installs
# ipywidgets for the sliders.
import importlib.util
import logging
import sys
from pathlib import Path

try:
    from pyodide.http import open_url  # the browser kernel only
except ImportError:
    open_url = None

# The browser kernel builds matplotlib's font cache on first import, with a notice; keep it quiet.
font_log = logging.getLogger("matplotlib.font_manager")
font_log.setLevel(logging.ERROR)
import matplotlib.pyplot as plt  # imported here so that the browser kernel loads the package
import numpy as np

font_log.setLevel(logging.NOTSET)

if sys.platform == "emscripten":
    kernel = importlib.util.module_from_spec(importlib.util.spec_from_loader("kernel", loader=None))
    sys.modules["kernel"] = kernel
    exec(open_url("kernel.py").read(), kernel.__dict__)

    await kernel.prepare(widgets=True)
else:
    root = next(p for p in (Path.cwd(), *Path.cwd().parents) if (p / "code" / "econ_scenarios").is_dir())
    sys.path.insert(0, str(root / "code"))
```

(sec-model)=
## The Model in Brief

Section 2 and Appendix A of {cite:t}`korinek2026scenarios` are the authoritative description of the model. This supplement follows their symbols and their equation numbers; each part below gives the module of the code that computes it.

### Scenarios

AI enters the model through the share of tasks it can perform, how widely it spreads, how much it raises output where it is used, and how much it disrupts workers. Table 1 of the paper sets these for three scenarios, which the table below prints as the code stores them.

```{code-cell} python
import pages

pages.scenario_table()
```

The paper's Equation (8) sets the paths of the first three: the affected mass $m_t$, the fraction of the economy's tasks that AI can perform; the diffusion share $d_t$, the fraction of those tasks' instances performed with AI; and the log gain $a_t$ on each AI-performed instance. Of these, the first two follow logistic curves and the gain follows a straight line:

```{math}
:label: eq-paths
:enumerator: 8
m_t = \frac{\bar{m}}{1 + e^{-\kappa_m (t - t_m)}}, \qquad d_t = \frac{\bar{d}}{1 + e^{-\kappa_d (t - t_d)}}, \qquad a_t = a_0 + g_a (t - t_0).
```

Each logistic curve rises from zero toward a ceiling. For the affected mass the ceiling is all cognitive work, the cognitive occupations' share of the wage bill: $\bar{m} = s_{C,t_0}/s_{L,t_0} = 0.624$, where $s_{C,t_0}$ is their share of income in the base period $t_0$ and the labor share $s_{L,t_0}$ is 0.6. For diffusion the ceiling $\bar{d}$ is 1, every instance. Their slopes, $\kappa_m$ and $\kappa_d$, set how fast each curve climbs, and their midpoints, $t_m$ and $t_d$, set when. From its starting value $a_0$, the gain grows by $g_a$ log points a year.

The three scenarios share the mid-2026 anchors $m_{2026} = 0.14$ and $d_{2026} = 0.10$ and differ in their 2030 values. For the affected mass, the paper's Equation (8') gives the slope that takes it from its anchor to its 2030 value $m_{2030}$ in the three and a half years between them,

```{math}
:label: eq-logistic-slope
:enumerator: 8'
\kappa_m = \frac{1}{3.5} \ln\left[ \frac{\bar{m} - m_{2026}}{m_{2026}} \cdot \frac{m_{2030}}{\bar{m} - m_{2030}} \right],
```

and the same expression in $d$ gives $\kappa_d$. Requiring each curve to pass through its anchor then fixes its midpoint. Because Table 1 reports $a_0$ at the same mid-2026 anchor, the reproduction starts the line there (`paths.py`); [](#sec-notation) records the notation point.

Each scenario also fixes two constants: the automation share $\psi$, the fraction of AI-performed instances that capital performs outright, and the reinstatement ratio $\rho$, the mass of new labor tasks created per unit of automated tasks. In the labor market, the search discount $\mu$ scales the job-finding chances of workers who look for work outside their old occupation group, and the posting speed $\theta_H$ sets how fast firms open vacancies once AI changes the jobs they want to fill.

### Production

In the potential economy, workers move freely between the two occupation groups (cognitive and all other) and all earn a common wage. Proposition 1 of the paper solves this economy in closed form given the rental rate of capital. Every $\Delta$ below is a log gap against the path without AI, so that $\Delta \ln r_t$ is the gap in the rental rate. Summing over tasks $i$, each of base mass $m_i$, we can write the proposition as

```{math}
:label: eq-closed-form
:enumerator: 14-17
\begin{aligned}
s_{L,t} &= 1 - \Big[ s_{K,t_0} + s_{L,t_0} \sum_i \psi_{i,t}\, m_i d_{i,t} \big( e^{-(1-\sigma) a_{i,t}} - \rho_i \big) \Big] e^{(1-\sigma) \Delta \ln r_t}, \\
\tilde{\ell}_{N,t} &= -\ln\Big( 1 - \sum_i m_i d_{i,t} \big[ 1 - \rho_i \psi_{i,t} - (1 - \psi_{i,t})\, e^{-(1-\sigma) a_{i,t}} \big] \Big), \\
\Delta \ln w_t &= \frac{\Delta \ln s_{L,t} + \tilde{\ell}_{N,t}}{1 - \sigma}, \qquad \Delta \ln (Y_t/L_t) = \Delta \ln w_t - \Delta \ln s_{L,t}, \\
\Delta \ln K_t &= \ln \frac{1 - s_{L,t}}{s_{K,t_0}} + \Delta \ln (Y_t/L_t) - \Delta \ln r_t.
\end{aligned}
```

The first line gives the labor share $s_{L,t}$, in which the base capital share $s_{K,t_0}$ is 0.4 and the elasticity of substitution across tasks $\sigma$ is 0.5, a value that makes tasks gross complements. The second gives the shift $\tilde{\ell}_{N,t}$ in the demand for the all-other group's labor, which the paper's Equation (13) turns into the two groups' employment targets. From these two follow the common wage $w_t$ and output per worker $Y_t/L_t$, with $\Delta \ln s_{L,t} = \ln(s_{L,t}/s_{L,t_0})$, and last the capital stock $K_t$. Because the three scenarios give every task the same parameters, the two sums reduce to $\psi_t m_t d_t [e^{-(1-\sigma) a_t} - \rho]$ and $m_t d_t [1 - \rho \psi_t - (1 - \psi_t) e^{-(1-\sigma) a_t}]$, the forms the code evaluates. Table A.1 adds the ideas stock $A_t$ of the Ideas section below to the wage, $\Delta \ln w_t = (\Delta \ln s_{L,t} + \tilde{\ell}_{N,t})/(1 - \sigma) + \Delta \ln A_t$, and I follow Table A.1 in the code.

The rental-rate gap is the unique root of the capital market's clearing condition, the paper's Equation (18),

```{math}
:label: eq-rental-gap
:enumerator: 18
\varepsilon \, \Delta \ln r_t = \Delta \ln K_t,
```

where the elasticity of capital supply $\varepsilon$ is 3. Its right side is the capital demanded by Equation (17), which falls as the rental rate rises. The reproduction brackets the root on $[-4, 4]$, a rental rate between $e^{-4}$ and $e^{4}$ times its no-AI value, and halves the bracket 100 times. The paper's runs stay within $e^{-1}$, so the wide lower end matters only for the capital deepening of a long transition. With perfectly elastic capital ($\varepsilon = \infty$) the root is zero.

Measured TFP is the reciprocal of the CES price index over all tasks at base factor prices, the paper's Equation (45):

```{math}
:label: eq-measured-tfp
:enumerator: 45
\Delta \ln \mathrm{TFP}_t \approx -\frac{1}{1 - \sigma} \ln\Big[ s_{K,t_0} + s_{L,t_0} \big( 1 - m_t d_t \big( 1 - e^{-(1-\sigma) a_t} \big) \big) e^{-(1-\sigma) \Delta \ln A_t} \Big].
```

To first order the TFP gap is $s_{L,t_0} (\Delta \ln A_t + m_t d_t a_t)$, the share-weighted sum of the paper's Equation (26). Month by month, the scenario paths thus fix the potential economy: output, the common wage, the labor share, and the capital stock (`production.py`).

### Labor Market

Workers belong to one of two groups, the cognitive occupations (SOC major groups 11 to 29, 41, and 43, with 62.4 percent of employment in the 2025 CPS) and all other occupations. As AI automates cognitive tasks, the employment the cognitive group can sustain falls. Displaced workers search for jobs.

Part of normal quitting responds to job prospects. A worker in group $o$, either $C$ (cognitive) or $N$ (all other), quits at the rate

```{math}
:label: eq-quit-rate
:enumerator: 27
q_{o,t} = q_o^X + q_o^T \, \frac{f_{o,t-1}}{\bar{f}_o},
```

where $q_o^X$ is an exogenous base rate and $q_o^T$ scales the part that moves with the group's job-finding rate last month, $f_{o,t-1}$, relative to its normal value $\bar{f}_o$. Table 1 prints that responsive part as 0.55 of normal quits, from the elasticity of JOLTS quits to the CPS finding rate, while the explorer's calibration record holds it as 6/11. On the model's monthly grid, Appendix A converts every per-period fraction into a continuously compounded rate, so that a quit fraction $\hat{q}$ enters as $q = -\ln(1 - \hat{q})$. The reproduction applies that conversion to the whole right side of Equation (27) each month, splitting the fraction before converting it. The text allows converting first as well. As the article's [](#sec-findings) shows, the order is the one open reading of the equations that moves published numbers. The explorer's paths select splitting first.

The cognitive wage adjusts gradually. Write $w^c_{C,t}$ for the wage that would clear the cognitive labor force attached to the group, the employed plus the cognitive-origin unemployed above their normal pool. The wage actually paid, $w_{C,t}$, closes only part of its gap to $w^c_{C,t}$ each month. This partial adjustment is a real-wage rigidity of the kind studied by {cite:t}`blanchard2007real`:

```{math}
:label: eq-sticky-wage
:enumerator: 30
\frac{w_{C,t}}{w_t} = \left( \frac{w_{C,t-1}}{w_{t-1}} \right)^{\xi_m} \left( \frac{w^c_{C,t}}{w_t} \right)^{1 - \xi_m}, \qquad \xi_m = \xi^{1/12}.
```

Here $w_t$ is the common wage of the potential economy, and $\xi$, which lies in $[0, 1)$, is the annual rigidity of the cognitive wage, 0.5 in every scenario. At $\xi = 0$ the wage clears the group every month; as $\xi$ approaches one it stays at the common wage. The rigid object is the cognitive discount $w_{C,t}/w_t$, which the reproduction updates in logs as a weighted average with weight $\xi^{1/12}$ on last month's discount. At the sticky wage, firms demand fewer cognitive workers than are attached to the group, so quits from surplus positions go unreplaced and layoffs remove the rest, as in the paper's Equation (31).

A worker searching outside the group of origin is at a disadvantage. With unemployment pools $U_{C,t}$ and $U_{N,t}$ by origin, the effective search directed at each group is $S_{C,t} = U_{C,t} + \mu U_{N,t}$ and $S_{N,t} = \mu U_{C,t} + U_{N,t}$ as in the paper's Equation (33), where the scenario's search discount $\mu$ lies in $(0, 1]$. Hires into group $j$ follow the matching function of {cite:t}`denhaan2000job`:

```{math}
:label: eq-matching
:enumerator: 34
H_{j,t} = \chi \, \frac{S_{j,t} \, v_{j,t}}{\big( S_{j,t}^{\iota} + v_{j,t}^{\iota} \big)^{1/\iota}}, \qquad j \in \{C, N\},
```

where $v_{j,t}$ is the flow of job openings, the curvature $\iota$ is 1.27, and the efficiency of matching $\chi$ is at most 1. Hires never exceed the searchers or the openings, so this form does not need a bound. Before evaluating it, the reproduction divides the numerator and the denominator by the larger of $S_{j,t}$ and $v_{j,t}$, a rescaling that leaves the value unchanged.

Each month the reproduction solves the paper's System (39) three times. With employment $(\ell_{C,t}, \ell_{N,t})$ held fixed, the system collects the price index, the two groups' labor demands, and the supply of capital:

```{math}
:label: eq-actual-economy
:enumerator: 39
\begin{aligned}
& s_{L,t_0} \Lambda_{C,t} \, e^{(1-\sigma) \Delta \ln w_{C,t}} + s_{N,t_0} \, e^{(1-\sigma) \Delta \ln w_{N,t}} + B_t \, e^{(1-\sigma) \Delta \ln r_t} = 1, \\
& \frac{\ell_{C,t}}{\ell_{C,t_0}} = \frac{\Lambda_{C,t}}{s_{C,t_0}/s_{L,t_0}} \, e^{\Delta \ln (Y_t/\tilde{L}) - \sigma \Delta \ln w_{C,t}}, \qquad \frac{\ell_{N,t}}{\ell_{N,t_0}} = e^{\Delta \ln (Y_t/\tilde{L}) - \sigma \Delta \ln w_{N,t}}, \\
& \Delta \ln K_t = \varepsilon \, \Delta \ln r_t.
\end{aligned}
```

In the first line, the surviving mass of cognitive task instances is $\Lambda_{C,t} \equiv s_{C,t_0}/s_{L,t_0} - m_t d_t [1 - \rho \psi_t - (1 - \psi_t) e^{-(1-\sigma) a_t}]$, the all-other group's base income share is $s_{N,t_0}$, and $B_t$ is the bracketed term of the labor share in Equation (14). In the second line, $\tilde{L}$ is the labor force $L$ less the normal unemployment pool $\bar{U}$. Both wages, $w_{C,t}$ and $w_{N,t}$, enter deflated by the ideas stock $A_t$. Evaluated at the attached cognitive force, the system gives the clearing wage $w^c_{C,t}$; solved for $\ell_{C,t}$ at the sticky wage, it gives cognitive labor demand; and at realized employment, it gives the actual economy's GDP, all-other wage, rental rate, capital stock, and labor share. The reproduction closes the capital row with the capital demanded as in Equation (17), $\ln\big((1 - s_{L,t})/s_{K,t_0}\big) + \Delta \ln Y_t - \Delta \ln r_t$ at the system's labor share, and finds the rental-rate gap by the same bisection (`production.py`, `simulate.py`). Before AI arrives, the normal-times steady state of Equation (38) sets the unemployment pools, quit rates, vacancy-filling rates, and the efficiency of matching (`labor.py`).

### Ideas

AI also speeds up research. The economy produces ideas from research input $R_t$, a fixed fraction of GDP along both paths, so research input rises one for one with the GDP gap: $\Delta \ln R_t = \Delta \ln Y_t$, the paper's Equation (22). Log-differencing the semi-endogenous ideas production function against the no-AI path, we obtain the gap in the growth rate of the ideas stock, the paper's Equation (42):

```{math}
:label: eq-ideas
:enumerator: 42
\Delta g_t = g \left[ e^{\lambda \Delta \ln R_t - (1 - \phi_R) \Delta \ln A_t} - 1 \right] \approx g \left[ \lambda \Delta \ln R_t - (1 - \phi_R) \Delta \ln A_t \right].
```

Here $g$, the no-AI growth rate of the labor-augmenting ideas stock $A_t$, is 0.0167; the return to research input $\lambda$ is 1; and the fishing-out term $1 - \phi_R$, equal to 2.86, makes each further idea harder to find as the stock grows. The reproduction evaluates the exact middle expression with the actual economy's GDP gap and advances the stock one month at a time, $\Delta \ln A_{t+1} \approx \Delta \ln A_t + h\, \Delta g_t$ with a step $h$ of 1/12 year, as in Table A.1. The ideas stock feeds back into the level of output through the wage of Proposition 1 and through measured TFP.

### The Code

| Paper | Module |
|---|---|
| Table 1 and its data sources, the scenarios | `calibration.py` |
| Equations (8) and (8'), the scenario paths and their slopes | `paths.py` |
| Proposition 1, Equations (14) to (18) and (45) | `production.py` |
| Equations (34) to (38), the normal-times steady state | `labor.py` |
| Appendix A steps 1 to 9, Table A.1 | `simulate.py` |
| Table 3 and the tables built from it | `report.py` |
| The explorer's quiz; Table B.1 | `quiz.py`, `survey.py` |

The whole model is in `code/econ_scenarios`, a small Python package whose only dependency is numpy. The cell below runs the three scenarios to 2030:

```{code-cell} python
from econ_scenarios import EXTREME, MODEST, SUBSTANTIAL, simulate

runs = {s.name: simulate(s) for s in (MODEST, SUBSTANTIAL, EXTREME)}
pages.readouts_table(
    runs,
    (
        ("gdp", "GDP, pct. above the no-AI path"),
        ("wage_avg", "average wage, pct. above the no-AI path"),
        ("labor_share", "labor share, pct. of income"),
        ("employment_C", "cognitive employment, pct. change since mid-2026"),
        ("unemployment", "unemployment rate, pct."),
    ),
)
```

(sec-numbers)=
## The Published Numbers

Below, each published number that public inputs can reproduce sits beside the reproduction's value for it. A number counts as reproduced when the reproduction rounds to it at the paper's printed precision. To show how close each value lies to its rounding boundary, the reproduction's column carries two more digits than the paper's.

### Summary

The table below counts the published numbers by source. A number is "predicted" when the paper's text fixes how it is computed, so that matching it tests the reproduction. The 15 "fitted" numbers are those for which a definition or an unstated parameter had to be taken from the explorer or inferred by matching. Agreement on a fitted number shows that the reading is consistent, a weaker test than a prediction.

```{code-cell} python
import pages
from validation.published import cached_runner, checks

run = cached_runner()
results = checks(run)
pages.summary(results)
```

### Table 3

Table 3 gives each scenario's values in 2030, most of them as gaps from the path without AI.

```{code-cell} python
pages.table3(run)
```

### Tables 5 and 6

Table 5 reruns the substantial and extreme scenarios at other elasticities of capital supply, and Table 6 at other rigidities of the cognitive wage.

```{code-cell} python
:tags: [hide-output]
pages.checks_table(results, ("Table 5", "Table 6"))
```

### Footnote 14, the Normal-Times Labor Market, and the Text

The remaining outputs come from Footnote 14's alternative scenario, the normal-times labor market of Section 2.3.2, and the numbers quoted in Sections 2.1.3, 2.2.1, 4.2, and 4.3.

```{code-cell} python
pages.checks_table(results, ("Footnote 14", "Section 2.3.2", "Section 2.1.3", "Section 2.2.1", "Section 4.2", "Section 4.3"))
```

### Inputs: Table 1, Table A.2, and the Survey Coding

These are the 43 numbers the model takes as given: the calibration shares of Table 1, the logistic slopes of Table A.2, the coding of survey answers into model parameters (Table B.1 and Appendix B.3), and the normal-times search discount implied by the switching odds of Section 3.2. Because no error in the model's dynamics could move them, [](#sec-validation) counts them separately.

```{code-cell} python
:tags: [hide-output]
pages.checks_table(results, ("Table 1", "Table A.2", "Table B.1", "Appendix B.3", "Section 3.2"))
```

### The Explorer Page

The explorer's page states 14 numbers of its own: GDP in 2030 in dollars, how the substantial scenario moves workers between groups, what a typical survey respondent's answers imply, and how fast the extreme economy grows. Because only the explorer's code defines the dollar scaling, the worker split, and the mapping from survey answers to parameters, the numbers that rest on them count as fitted.

```{code-cell} python
pages.checks_table(results, ("Explorer page",))
```

(sec-figures)=
## The Paper's Figures and a Worker's View

Figures 2 to 4 of {cite:t}`korinek2026scenarios` are regenerated below from the reproduction with `code/figures.py`, under the paper's numbering, with the four panels of its Figure 3 drawn as two figures of two. Each line ends at its January 2030 value, with the economy without AI drawn as a dashed line.

:::{figure} figures/figure-2.png
:label: fig-2
GDP above the path without AI, and GDP growth, in the three scenarios (the paper's Figure 2).
:::

:::{figure} figures/figure-3a.png
:label: fig-3a
The average wage and the wage in cognitive occupations (the first two panels of the paper's Figure 3).
:::

:::{figure} figures/figure-3b.png
:label: fig-3b
The net return to capital and the labor share (the last two panels of the paper's Figure 3).
:::

:::{figure} figures/figure-4.png
:label: fig-4
Cognitive employment since mid-2026, the unemployment rate of cognitive workers, and the unemployment rate of all workers (the paper's Figure 4).
:::

The same drawing code runs inside this page, where the cell below recomputes the three scenarios and redraws [](#fig-4):

```{code-cell} python
from econ_scenarios import EXTREME, MODEST, SUBSTANTIAL, simulate
from explore import png
from figures import build, figure_panels

runs = {s.name: simulate(s) for s in (MODEST, SUBSTANTIAL, EXTREME)}
png(build(figure_panels(runs["modest"])["figure-4"], runs))
```

### A Cognitive Worker's View

Because the model tracks every worker's monthly transitions between employment and unemployment in each group, the same paths also describe the odds an individual worker faces. [](#fig-worker) reads four of them off the monthly transition matrices: the chance of quitting, the chance of being laid off, the expected length of a spell of unemployment for a worker from cognitive work who is unemployed that month, and the chance that a worker employed in cognitive work is unemployed a year later. Neither the paper nor the explorer displays these odds. A household model needs them, because a worker choosing how much to save must know the chance of losing the job and how long a spell of unemployment would last.

:::{figure} figures/validation-4.png
:label: fig-worker
A cognitive worker's monthly chance of separating, by quit or layoff, with the layoff chance alone dotted and the quit chance the distance between the two, its expected unemployment spell, and its chance of being unemployed twelve months later, read off the transition matrices. The paths run to 2040 so that the forward-looking measures have their full window.
:::

The script `code/exhibits.py` draws [](#fig-worker). The table below gives two of these measures for a cognitive worker in January 2029, without AI and in each scenario.

```{code-cell} python
import pages

long_runs = {s.name: simulate(s, horizon=2040.0) for s in (MODEST, SUBSTANTIAL, EXTREME)}
pages.worker_table(long_runs, year=2029.0)
```

(sec-checks-detail)=
## The Two Checks in Detail

The article's [](#sec-validation) states the two checks, their setup, and their results, with the explorer comparison in [](#fig-agreement). Three sections below recompute every published number at its rounding, run the planted errors at full strength, and show which published numbers bind. The script `code/validation/oracle.py` downloads and checks the explorer's bundle. Its outputs are recorded in `code/validation/explorer_record.json.gz`, keyed by configuration.

### The Published Numbers at Their Rounding

The code below recomputes all 226 published numbers and checks each at its printed rounding:

```{code-cell} python
from collections import Counter

from validation.published import cached_runner, checks

results = checks(cached_runner())
for key in ("basis", "role"):
    for value, n in Counter(getattr(c, key) for c in results).items():
        missed = sum(not c.ok for c in results if getattr(c, key) == value)
        print(f"{value:10s} {n:4d} numbers, {missed} outside their rounding")
```

The 211 predicted and 15 fitted numbers are those of the summary table above, the 43 inputs those of the inputs subsection, and the 183 outputs what the simulation produces. Six numbers come closest to their rounding boundary:

```{code-cell} python
for c in sorted(results, key=lambda c: c.slack)[:6]:
    print(f"{c.slack:.4f}  {c.source}: {c.label}: paper {c.published}, here {c.model:.4f}")
```

### Planted Errors at Full Strength

The four planted errors of [](#sec-detection) each fail both checks at full strength, with the gaps to the explorer the article reports. The code below runs the tables' half of that test and counts the published numbers each error moves outside their rounding.

```{code-cell} python
from validation.plants import DESCRIPTIONS, PLANTS, planted
from validation.published import failures

for plant in PLANTS:
    with planted(plant) as run:
        missed = failures(cached_runner(run))
    print(f"{DESCRIPTIONS[plant]:36s} {len(missed):3d} published numbers outside their rounding")
```

### The Binding Published Numbers

The published numbers closest to their rounding boundary decide what the second check can detect. [](#fig-binding) shows every output's margin and the numbers that fail first as each planted error is strengthened. The article's [](#sec-detection) names the numbers that set the tables' thresholds, which the left panel marks.

:::{figure} figures/validation-2.png
:label: fig-binding
Left: every model output's margin inside its rounding band, and the numbers that fail first as each planted error is strengthened. Right: the share of each group of outputs that each planted error, at full strength, moves outside its rounding.
:::

(sec-notes-detail)=
## Further Notes on the Paper and Its Data

The article's inventory lists the twelve inputs, definitions, and orderings the reproduction had to supply. [](#fig-open-choices) draws the two that move published numbers, the rounded inputs of the paper's Table 1 and the order in which quit fractions are split and converted to rates, which the tables cannot separate from the responsive quit share. Four more choices, below, set parameters and definitions that only matching the published numbers or reading the explorer's code identifies. Code cells then compute the small differences between the text and the tables that the article reports. A last section points to the code behind the article's recheck of the calibration's public data.

:::{figure} figures/validation-5.png
:label: fig-open-choices
:width: 100%
Left: residuals of the 183 published outputs when the model runs on the printed, rounded inputs of the paper's Table 1 in place of the unrounded ones in the explorer's calibration record, in half-units of the last printed digit. The band is the printed rounding. Right: the number of the 226 published numbers the model reproduces at each responsive share of normal quits, from 0.535 to 0.560, when quit fractions are split before Appendix A's conversion to continuous rates and when they are converted first.
:::

In the right panel, each order reproduces every number on a window of shares that includes values the paper's Table 1 would print as 0.55, though neither does so at 0.55 itself. The explorer's 6/11 lies in the window of splitting first.

### Further Choices Taken from the Explorer

1. System (39) values cognitive labor at its marginal product at realized employment, while the reproduction records the sticky wage actually paid separately. That difference leaves cognitive employers a profit of at most 0.31 percent of GDP along every path.
2. The alternative scenario of Footnote 14 needs two parameters the footnote does not state. A posting speed $\theta_H$ of 0.25 and a wage rigidity $\xi$ of 0.5 reproduce its numbers, while a posting speed of 0.5 does not. Its transfer also needs a base for cognitive employment, discussed below.
3. On the explorer page, GDP in dollars scales the substantial path's 2025 average to \$30.76 trillion and grows it at 2 percent a year; the worker split compares January 2026 with January 2030; and the typical respondent runs Table 2's median answers through the explorer's quiz. These definitions exist only in the explorer's code.
4. Like the explorer, the reproduction bisects the rental-rate gap 100 times and the normal-times steady state 200 times. The explorer's quiz also bounds the log gain at $\ln 30$ and the logistic slopes at 3, which `econ_scenarios` offers but does not apply to the paper's scenarios.

### Small Differences between the Text and the Tables

Three passages of the text and the tables disagree. The article gives the likely reading of each. The cells below compute the numbers behind them.

#### Cognitive Unemployment in Mid-2026

The cell below prints the substantial scenario's cognitive unemployment rate in 2024, mid-2026, and 2030 beside Section 4.2's "from 2.9 percent in mid-2026 to 4.5 percent in 2030", and the rise measured from each base.

```{code-cell} python
from validation.published import cached_runner, text_table_differences

run = cached_runner()
for c in text_table_differences(run):
    print(f"{c.source}: {c.label}: paper {c.published}, model {c.model:.3f}\n  {c.note}")
```

#### Two Channels in Section 2.1.3

The cell below evaluates Section 2.1.3's three potential-economy numbers with and without the ideas gain $\Delta \ln A$: the wage includes it, the TFP gain leaves it out, and the rental rate rounds to 4.6 either way.

```{code-cell} python
import math

from econ_scenarios import SUBSTANTIAL, Calibration
from econ_scenarios.paths import ScenarioPaths
from econ_scenarios.production import potential, tfp_base_weight

cal = Calibration()
sim = run(SUBSTANTIAL)
k = sim.index(cal.t_read)
x = ScenarioPaths(SUBSTANTIAL, cal).at(cal.t_read)
for label, dlnA in (("with the ideas gain", sim["dlnA"][k]), ("without it", 0.0)):
    p = potential(x, dlnA, cal)
    print(
        f"{label:20s} wage {100 * math.expm1(p.lnW):.2f}, rental rate {100 * math.expm1(p.dlnr):.2f},"
        f" TFP gain {tfp_base_weight(x, dlnA, cal):.3f}"
    )
print(f"{'paper':20s} wage 1.9, rental rate 4.6, TFP gain 0.029")
```

#### The Base of Footnote 14's Transfer

The reproduction recovers Footnote 14's transfer of 84 percent of the GDP gain when it counts cognitive employment from mid-2026, and 87 percent from the 2024 base of Table 3's labor income rows. The footnote's number is the mid-2026 figure.

(sec-notation)=
#### Two Points of Notation

The reproduction and the explorer start the log gain's line at the mid-2026 anchor where Table 1 reports $a_0$, though Equation (8) writes it from the base year $t_0$ of Table A.2, and the reproduction follows Table A.1's wage row, which includes the ideas term that Proposition 1's Equation (16) omits. The article discusses both.

### The Public Data behind the Calibration

The article's [](#tbl-public-data) recomputes every calibration input that comes from public data from its original source. The code for every row is in `code/validation/upstream_*.py`. When a source file is missing, its tests fail rather than skip.

(sec-explore)=
## Interactive Scenarios

A small version of the authors' [scenario explorer](https://www.anthropic.com/institute/econ-scenarios) runs below on the reproduction. Start the compute environment with the button at the top of the page and then run the cells. The sliders set a scenario's assumptions from Table 1 of {cite:t}`korinek2026scenarios`, plus two calibration numbers (the rigidity of the cognitive wage and the elasticity of capital supply). After each change the cell reruns the model month by month from 2024 and redraws three of the paper's panels, in which the three published scenarios stay in the background at the paper's calibration. Before the kernel starts, the cell shows a still of the explorer's first view, the substantial scenario.

```{code-cell} python
import explore

if sys.platform == "emscripten":
    display(explore.Explorer().widget)
else:  # a page built without a browser shows the explorer's first view as a still
    explore.still()
```

Each slider keeps its assumption inside the range in which the model's paths are defined, which for the 2030 affected mass lies between its mid-2026 anchor (0.14) and its ceiling (0.624), and for the 2030 diffusion share between 0.10 and 1.

Every number in this section comes from `econ_scenarios.simulate`, the same function that [](#sec-validation) checks against the explorer. The module `code/explore.py` maps the sliders to a scenario and draws the result.
