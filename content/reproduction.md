---
title: Reproducing “Economic Scenarios for Transformative AI”
short_title: Reproduction
subtitle: Everything It Takes to Rerun the Monthly Model of Korinek et al. (2026), as an Econ-ARK REMARK
 # The catalog abstract: the cut copies it into REMARK.md and CITATION.cff (export_remark), and
 # the site build writes it into the page's meta tags. The abstract below is the paper's own.
description: "An Econ-ARK REMARK that reimplements the monthly model of Korinek, Jones, Sacher, Cotter, and McCrory (2026) and documents the twelve inputs, definitions, and orderings that a transparent reproduction requires and the paper leaves unstated. The reproduction agrees with the authors' scenario explorer in every series and month to within 3.5e-14 and reproduces all 226 published numbers within the paper's printed rounding. One script fails when any number stops reproducing."
 # The three the materials block names. They live on the page because the cut's project front
 # matter is DERIVED from it, and because project-level `downloads` never reaches the Typst
 # export, which left the fourth column missing (measured 2026-09-18).
github: https://github.com/econ-ark/econ-scenarios
binder: https://econ-ark.github.io/econ-scenarios/reproduction-appendix/
downloads:
  - title: Latest PDF
    url: https://github.com/econ-ark/econ-scenarios/blob/main/content/exports/reproduction.pdf
 # The report alone as a PDF; its supplement is online only. Clean the template first: the theme
 # is fetched from main, and a cached clone renders a well-formed PDF from whatever it last held.
 # uv run myst clean --templates -y && SOURCE_DATE_EPOCH=1789689600 FORCE_SOURCE_DATE=1 uv run myst build content/reproduction.md --pdf
exports:
  - format: typst
    template: https://github.com/econ-ark/econ-ark-myst.git
    output: exports/reproduction.pdf
    kind: REMARK
    # Links the paper's REMARK on econ-ark.org from the PDF's materials block, live once the
    # submission to the REMARK catalog is accepted.
    remark: econ-scenarios
    # Heads the binder column, whose address is the supplement. "Run online" would undersell a
    # page whose cells the reader edits and re-runs.
    binder_label: Run the cells
    # Fields this page leaves unset fall back to the project front matter in myst.yml, which
    # describes the repository as a whole and not this article, so the PDF sets its own.
    subtitle: null
    short_title: Reproducing the AI Scenarios
    keywords:
      - artificial intelligence
      - macroeconomic scenarios
      - labor reallocation
      - reproduction
      - Econ-ARK
 # The same export as Typst source, so a reader can rebuild or edit the typesetting without
 # reconstructing it, and so MyST writes the bibliography it resolved beside it.
  - format: typst
    template: https://github.com/econ-ark/econ-ark-myst.git
    output: exports/reproduction.typ
    kind: REMARK
    remark: econ-scenarios
    binder_label: Run the cells
    subtitle: null
    short_title: Reproducing the AI Scenarios
    # Repeated from the block above, and not a stylistic choice: leaving them out made MyST
    # fall back to the project keywords for BOTH exports, which changed the PDF's keyword line
    # to include "household saving" (measured 2026-09-18).
    keywords:
      - artificial intelligence
      - macroeconomic scenarios
      - labor reallocation
      - reproduction
      - Econ-ARK
 # JEL codes, printed under the keywords.
tags:
  - C63
  - C88
  - E17
  - O33
keypoints: |
  - Run on Table 1 as printed, the model reproduces 163 of the 183 published outputs. The other 20 need that table at the precision the authors' browser explorer holds in its calibration record.
  - With twelve inputs, definitions, and orderings the text leaves open, each sourced and tested, the reproduction matches the explorer to within $3.5 \times 10^{-14}$ and all 226 published numbers.
  - Four errors planted in the reproduction's code show that the explorer comparison detects errors 8 to 9 orders of magnitude weaker than the published tables detect.
  - The package is a REMARK whose script fails when any published number stops reproducing.
abstract: |
  {cite:t}`korinek2026scenarios` publish three scenarios for AI's effect on output, wages, and employment through 2030, from a monthly model and a browser explorer that runs it. I reimplement the model and document every input, definition, and ordering that a transparent reproduction requires and the paper leaves unstated, twelve in all. With Table 1 as printed and the other items in place, the model reproduces 163 of the 183 outputs, all 183 at the precision the explorer's code holds. The explorer's paths fix one open ordering in the quit equation. One published number fixes two parameters of Footnote 14. The reproduction agrees with the explorer in every series and month within rounding error and reproduces all 226 published numbers. Every published result stands. The package is an Econ-ARK REMARK, a form that makes reproducing every result a mandate, enforced by one script that fails when any number stops reproducing.
---

:::{raw:typst}
// The table fragment carries a raw LaTeX float, which MyST parses and renders here as well, and a
// raw Typst twin. Drop the parsed copies (kind "table", a string), which the rule names by
// label because the public-data table is a MyST table with no twin and must print, and give
// their count back, since a dropped figure still steps the counter; the link rule below prints
// a reference to a dropped label as its text, which MyST has already numbered.
#show figure.where(kind: "table"): it => {
  let twinned = (<tbl-inventory>, <tbl-published-numbers>)
  if twinned.contains(it.at("label", default: none)) {
    counter(figure.where(kind: "table")).update(n => n - 1)
  } else { it }
}
// The twins carry the table function as their kind, a counter of their own; give them the
// parsed tables' kind so that one counter numbers every table in the order MyST does.
#show figure.where(kind: table): it => figure(it.body, caption: it.caption, kind: "table", supplement: it.supplement)
// The template's tablex counts rows, so the public-data table, which MyST lays out, closes with
// a bottom rule like the twin.
#import "econark.typ": arkTablex
#let tablex = arkTablex.with(tablex)
// The supplement is online only, so its labels and the site's pages do not exist in this PDF.
// Print such a reference as its text, linked to the site once site-url names where it is served.
#let site-url = none
#let supplement-path = "/reproduction-appendix"
#show link: it => context {
  let page = type(it.dest) == str and it.dest.starts-with("/")
  let absent = type(it.dest) == label and query(it.dest).len() == 0
  if not (page or absent) { it } else if site-url == none { it.body } else if page {
    link(site-url + it.dest, it.body)
  } else { link(site-url + supplement-path + "#" + str(it.dest), it.body) }
}
:::

## Introduction

How much could artificial intelligence change output, wages, and employment by 2030? {cite:t}`korinek2026scenarios` answer with three scenarios, modest, substantial, and extreme, from a monthly model of how the labor market adjusts to AI. In the extreme scenario GDP grows 15.4 percent a year and the unemployment rate of cognitive workers reaches 17.9 percent in 2030. The authors publish the model as a scenario explorer at [anthropic.com/institute/econ-scenarios](https://www.anthropic.com/institute/econ-scenarios), a web page that runs the model in the reader's browser, prints numbers of its own, and lets the reader change the scenario through a quiz and choose among data sources. The explorer is the authors' only published code, a compiled JavaScript bundle without a license, which this report reads for what the paper does not print and runs as a reference solution. Anyone who wants to build on the scenarios needs the model in a form that can be rerun, checked equation by equation, and extended. This report puts the model in that form. Its main work is to recover every input, definition, and ordering that a transparent reproduction of the paper's results requires and that the paper does not state, twelve in all, each sourced and held under test.

Reproducing published results has repeatedly proved harder than reading the articles suggests. Given one textbook probit, five statistical packages declared convergence to five different solutions {cite:p}`mccullough2003verifying`. In a journal archive that required authors to deposit their data and code, fewer than 15 of more than 150 empirical articles could be replicated {cite:p}`mccullough2006lessons`. Replication files reproduce the key result of about a third of 67 papers from 13 journals without the authors' help, and of about half with it {cite:p}`chang2022replicable`. {cite:t}`christensen2018transparency` and {cite:t}`vilhuber2020reproducibility` survey that evidence and the practices that have followed, from sharing data and code to journals verifying reproducibility themselves. Those studies ask whether an article's deposited data and code reproduce its estimates, under journal policies that require the deposit. The paper here is a research report outside any journal's deposit policy. Its authors published an explorer instead. This report asks more of the paper than a deposit policy would. The paper prints 43 inputs, its calibration, and 183 outputs that the calibration produces through the model's equations, 226 numbers in all. Do the printed inputs reproduce the printed outputs at full precision?

To answer that question I reimplement the model in plain Python and numpy from the paper's Appendix A, the 44 equations of its Table A.1, and the calibration of its Table 1. Throughout, reproduction names the outcome, the paper's numbers regenerated from code, and reimplementation the act of writing that code from the paper's description. Where the text leaves a detail open, the reproduction takes it from one of two further sources, or records that none exists. The explorer's code holds the calibration record, the list of Table 1's inputs at full precision, and the definitions behind the numbers on the explorer's page. Matching, against the explorer's monthly paths or against one published number, recovers what neither the text nor the explorer states. The paper's survey of US adults has no public source, since its microdata are confidential. [](#tbl-inventory) lists the twelve items this took, with the source of each and what turns on it, and a test in the replication package checks each. Two checks then test the reproduction. The first runs the explorer's code as a reference solution and compares every series in every month. The second compares every number the paper and the explorer's page print with the reproduction's value. A number counts as reproduced when the reproduction's value rounds to the printed one. To measure what each check can reject, I plant four plausible misreadings of the paper in the reproduction's code, deliberate errors of the kind mutation testing seeds in a program to measure its tests {cite:p}`demillo1978hints`, and weaken each until a check no longer rejects it.

Run on Table 1 as printed, with the other eleven items in place, the model reproduces 163 of the 183 published outputs. The 20 it misses fall in Tables 3, 5, and 6, in Section 2.3.2's normal-times steady state, which describes the labor market before AI arrives, and on the explorer's page, all in the substantial and extreme scenarios and none in the modest one. Run on the printed monthly job-loss hazards alone, 0.84 and 1.84 percent in place of the calibration record's 0.8359 and 1.8379, the model misses three of the 20. With all twelve items in place the reproduction agrees with the explorer's code in every series and every month, with a largest absolute gap of $3.5 \times 10^{-14}$, across 25 configurations, among them the three scenarios, the robustness settings of the paper's Tables 5 and 6, seven sets of answers to the explorer's quiz, its five data options, and runs as long as 2040. The reproduction also matches every number the paper and the explorer's page print that public inputs allow, 226 in all, within the paper's printed rounding. Each published result survives both checks. The text and the tables differ in three small places, none of which moves a result. Of the thirteen calibration inputs that come from public data, eleven match their sources or come within a few percent, and two differ by more.

Two of the twelve items move published numbers. The first is Table 1 at the precision the calibration record holds, which accounts for all 20 misses. The second, a reading of the model's quit equation, moves six numbers. At issue is whether each quit fraction is converted to a continuous rate before or after it is split into the part that responds to job prospects and the rest. The text does not fix the order. Nor can the tables, since the quit share they are read against is itself printed rounded. The reproduction uses the order that matches the explorer's paths, which the other order misses by up to $4 \times 10^{-4}$. Footnote 14's alternative scenario, another of the twelve, needs a vacancy-posting speed and a wage rigidity. The footnote does not give them, but its own numbers identify both.

Planting errors measures what each check can detect. An error's strength is the weight placed on the erroneous computation, 1 at full strength. The explorer comparison detects the four errors at strengths as low as $1.8 \times 10^{-11}$ to $10^{-9}$, the published tables only at strengths of 0.01 to 0.18, so the tables need each error 8.3 to 9.0 orders of magnitude stronger. An error strong enough to move the monthly paths by several thousandths can leave every published number inside its rounding. Even the strongest error the tables miss changes a published number by at most 0.07 in the units the paper prints. Agreement with the published tables therefore establishes that a reimplementation is close. Establishing that it is the authors' model takes agreement with the explorer's code in every month.

A reproduction therefore has to replay that agreement under a rule that lets it stand only while the replay does. This one is an Econ-ARK REMARK (Reproductions and Explorations Made using ARK), a public repository built around one such rule: a script whose failure means the reproduction has failed. That rule makes the reproduction of every result a requirement of the form itself. The authors' publication is diligent, with an explorer that is more than most papers offer, but diligence does not make a publication airtight in that sense, whereas the REMARK form is by construction. Here that script checks every table, figure, and quoted number of this report. An online [supplement](reproduction-appendix.md) holds the model's equations, every published number beside the reproduction's value, the paper's figures regenerated, the details of both checks, and a small version of the explorer whose cells run when the site is built. Nine of the twelve items could be stated in the paper's text in a sentence each. A statement in a document, though, holds only until the code moves, which a script catches and a sentence cannot. Econ-ARK, the open-source project behind the HARK toolkit for models of optimizing households {cite:p}`carroll2018econark`, will build such models on this reproduction, which supplies the monthly transitions between employment and unemployment that those models need and that neither the paper nor the explorer displays.

The next section sets out the model and the explorer. [](#sec-findings) is the heart of the report, the twelve items of [](#tbl-inventory) and the two that move published numbers. The notes on the paper's text and its public data follow it. [](#sec-validation) and [](#sec-detection) give the two checks and what the planted errors show each can detect. The package and what the paper's results now rest on close the report.

## The Model and Its Reimplementation

Section 2 and Appendix A of {cite:t}`korinek2026scenarios` are the model's authoritative description. The supplement's [section on the model](#sec-model) states every equation the reproduction evaluates, with the module that evaluates it. This section gives the parts a reader needs to follow the inventory and the checks.

AI enters through three scenario paths: the affected mass $m_t$, the fraction of the economy's tasks that AI can perform; the diffusion share $d_t$, the fraction of those tasks' instances performed with AI; and the log gain $a_t$ in productivity on each such instance. The first two follow logistic curves and the gain a straight line, the paper's Equation (8),

```{math}
:label: eq-main-paths
m_t = \frac{\bar{m}}{1 + e^{-\kappa_m (t - t_m)}}, \qquad d_t = \frac{\bar{d}}{1 + e^{-\kappa_d (t - t_d)}}, \qquad a_t = a_0 + g_a (t - t_0),
```

where the affected mass rises toward the cognitive occupations' share of the wage bill, which at the common wage is their share of employment, $\bar{m} = 0.624$, and diffusion toward $\bar{d} = 1$. The three scenarios share the mid-2026 anchors $m_{2026} = 0.14$ and $d_{2026} = 0.10$ and differ in their 2030 values, which fix the slopes $\kappa_m$ and $\kappa_d$ and the midpoints $t_m$ and $t_d$. Each scenario also sets the automation share $\psi$, the fraction of AI-performed instances that capital performs outright, the reinstatement ratio $\rho$, the mass of new labor tasks created per unit of automated tasks, the search discount $\mu$ on workers who look for work outside their occupation group, and the speed at which firms post vacancies.

Given the rental rate of capital, a potential economy in which workers move freely between cognitive and all other occupations has a closed-form solution, the paper's Proposition 1, for the labor share, the common wage, output per worker, and the capital stock, with tasks gross complements at an elasticity of substitution $\sigma$ of 0.5. The rental rate clears a capital market in which supply rises with the return at an elasticity of 3, a root the reproduction brackets and bisects. That capital-supply schedule takes the place of saving, which the authors set aside deliberately: the model, in their words, "does not explicitly model" it, and with some capital possibly "financed from abroad," their Footnote 5 notes, the split of output between consumption and investment need not be specified. Research input, a fixed fraction of GDP, raises the stock of labor-augmenting ideas $A_t$ through a semi-endogenous growth equation with a fishing-out term, the paper's Equation (42), and the ideas stock feeds back into the wage and into measured TFP.

The actual economy follows the two groups of workers through quits, layoffs, and matching. Part of normal quitting responds to job prospects. A worker in group $o$, cognitive or all other, quits at the rate

```{math}
:label: eq-main-quit
q_{o,t} = q_o^X + q_o^T \, \frac{f_{o,t-1}}{\bar{f}_o},
```

where $q_o^X$ is an exogenous base rate and $q_o^T$ scales the part that moves with the group's job-finding rate last month, $f_{o,t-1}$, relative to its normal value $\bar{f}_o$; the paper's Table 1 prints the responsive part as 0.55 of normal quits, while the explorer's calibration record holds it as 6/11. On the model's monthly grid, Appendix A converts every per-period fraction into a continuously compounded rate, so that a quit fraction $\hat{q}$ enters as $q = -\ln(1 - \hat{q})$. Whether that conversion applies before or after the split into the two parts is the one open reading of the equations that moves a published number, taken up in [](#sec-findings). The cognitive wage adjusts gradually. The wage actually paid closes only part of its log gap each month to the wage that would clear the cognitive labor force attached to the group,

```{math}
:label: eq-main-sticky
\frac{w_{C,t}}{w_t} = \left( \frac{w_{C,t-1}}{w_{t-1}} \right)^{\xi_m} \left( \frac{w^c_{C,t}}{w_t} \right)^{1 - \xi_m}, \qquad \xi_m = \xi^{1/12},
```

where $w_t$ is the common wage of the potential economy, $w^c_{C,t}$ the clearing wage, and $\xi$ the annual rigidity of the cognitive wage, 0.5 in every scenario, a real-wage rigidity of the kind studied by {cite:t}`blanchard2007real`. At the sticky wage, firms demand fewer cognitive workers than are attached to the group, so quits from surplus positions go unreplaced and layoffs remove the rest. The unemployed search with the discount $\mu$ outside their group of origin, and hires follow the matching function of {cite:t}`denhaan2000job`. Each month the reproduction solves the paper's System (39) three times: at the attached cognitive force, for the clearing wage; at the sticky wage, for cognitive labor demand; and at realized employment, for the actual economy's GDP, all-other wage, rental rate, capital stock, and labor share. Before AI arrives, the normal-times steady state sets the unemployment pools, quit rates, vacancy-filling rates, and the efficiency of matching.

I implement the monthly recursion of the paper's Appendix A over the 44 equations of its Table A.1, the calibration of its Table 1, and the explorer's alternative data sources and quiz. The whole model is about 1,300 lines of Python whose only dependency is numpy. One scenario runs to 2030 in a fraction of a second. Where the text leaves a detail open, such as a numerical bracket or the order of steps within a month, I read the explorer's source for the calibration record, the page's definitions, and the numerical brackets, match the explorer's paths for the rest, and record the item in [](#tbl-inventory).

The explorer is the authors' only published code. It is a JavaScript bundle served by anthropic.com, compiled and minified for delivery, so its names are shortened, and published without a license. The bundle holds three things the paper does not print: the model's code, the calibration record behind Table 1 at full precision, and the definitions behind the numbers on the explorer's page, its dollar GDP, its split of workers, and its typical survey respondent. The reproduction uses the bundle in two ways. It runs the bundle's model code under Node.js as a reference solution, once for every configuration the comparison of [](#sec-validation) uses, and it reads the bundle for the record and the definitions. Because the bundle has no license, the repository holds none of its code. It holds a record of the bundle's outputs, indexed by configuration and by a checksum of the bundle, which the comparison reads.

The authors' survey of US adults and its microdata, which are not public, underlie the paper's Table 2, the columns of its Table 4 that describe US adults, its Figure 1, and the explorer page's statement about the share of survey respondents. I reproduce everything else in the paper and on the explorer page from public inputs.

(sec-findings)=
## What Reproduction Required

The reproduction had to supply twelve items the text leaves open. [](#tbl-inventory) lists them, with where the paper stops on each, where the reproduction took it from, and what turns on it. I include the items that leave every published number where it is, because a reader cannot know in advance which those are. Six come from the explorer's code, the calibration record among them, one from matching the explorer's paths, one from the paper's Table 1 confirmed by the explorer, two from matching a published number, one from Table A.1 read against Equation (16), and the last, the survey microdata, is not public. Two of the twelve move published numbers, the unrounded inputs behind the paper's Table 1 and the one open reading of the model's equations.

1. The paper's Table 1 prints its data inputs rounded, but the published tables come from the unrounded values in the explorer's calibration record. The monthly job-loss hazards, for example, are 0.8359 and 1.8379 percent in the two groups. With the printed 0.84 and 1.84, the reproduction misses three published numbers. Run on all of that table's printed shares, search pool, relative separation rates, and quit share, it misses 20 of the 183 published outputs, as the left panel of the supplement's [](#fig-open-choices) shows. One more printed digit in that table would let a reader reproduce the paper's tables from the paper alone.
2. Appendix A converts quoted quit fractions into continuous rates, $q = -\ln(1 - \hat q)$. The reproduction splits each group's normal quit fraction into the part that responds to job prospects, a share of 6/11 that the paper's Table 1 prints as 0.55, and the rest, and then converts the month's combined fraction. Converting before splitting, which the text also allows, moves the paths by up to $4 \times 10^{-4}$ and pushes 6 of the 226 published numbers out of their rounding. They are four distinct values. The extreme scenario's average wage, printed 9.7 in Tables 3, 5, and 6, becomes 9.6476. Table 5's extreme capital stock with perfectly elastic capital, printed 82.2, becomes 82.2543. Table 6's extreme cognitive and all-other wages at $\xi = 0$, printed {math}`-42.2` and 70.1, become {math}`-42.1401` and 70.0120, the last 0.088 away against a band of 0.05. At the explorer's quit share of 6/11, the published tables therefore require splitting first, the order the explorer's paths also select.

The tables cannot separate the quit order from the quit share. In the right panel of the supplement's [](#fig-open-choices), each order's count of reproduced numbers moves with the share. Converting first reproduces all 226 numbers at shares from 0.552 to 0.5545, which the paper's Table 1 also prints as 0.55, while splitting first needs shares from 0.5435 to 0.547. At exactly 0.55, the value Section 3.2 gives, neither order reproduces the tables. At 0.545, the share printed to one more digit, only splitting first does. Converting first misses the explorer's paths by up to $4 \times 10^{-4}$. The paths therefore decide the order where the tables cannot. That order decides six numbers at the explorer's 6/11 and none at 0.553, inside the window where converting first also reproduces the tables, and the two readings the tables accept differ by at most 0.011 in any published number. The second implementation of [](#sec-validation), written from the paper's text alone, took the other reading.

```{include} fragments/reproduction-inventory.md
```

The supplement's [notes on the paper and its data](#sec-notes-detail) give the four choices in the lower half of [](#tbl-inventory) in more detail, among them the two parameters Footnote 14 does not state, which the footnote's numbers identify by matching, and the definitions of the explorer page's numbers that exist only in its code.

## Notes on the Paper and Its Data

Two kinds of note remain beyond the twelve items. In three passages the paper's text and its tables differ, each with a likely cause, and thirteen of the calibration's inputs come from public data that can be recomputed. The results do not depend on any of them.

### Small Differences between the Text and the Tables

Three passages of the text and the tables disagree.

Section 4.2 describes the substantial scenario's cognitive unemployment rate as rising "from 2.9 percent in mid-2026 to 4.5 percent in 2030, more than a 50 percent increase." The reproduction gives 2.85 percent in 2024, 3.06 percent in mid-2026, and 4.53 percent in 2030, so the 4.5 percent in 2030 matches. The mid-2026 rate, which the explorer also gives, is above the 2024 one because Appendix A applies the scenario's search discount from 2024, which raises unemployment a little before any displacement begins. Measured from mid-2026, the date the sentence gives, the rise is 48 percent, just under 50. However, the 2.9 percent is the 2024 rate, the normal-times steady state of Section 2.3.2, so the sentence most likely measures from that starting level. On that base the rise is 59 percent, so the claim of more than 50 percent holds.

Section 2.1.3 illustrates the substantial scenario in 2030 with three numbers from the potential economy, a rental rate 4.6 percent above normal, a wage 1.9 percent above the path without AI, and an exact TFP gain of 0.029. The three do not come from one treatment of the stock of ideas. The wage of 1.9 percent includes the gain in that stock, the TFP gain of 0.029 leaves it out, and the rental rate rounds to 4.6 either way.

Footnote 14 reports that a transfer of 84 percent of the GDP gain would hold cognitive workers' income at its level without AI. The reproduction recovers the 84 when it counts cognitive employment from mid-2026, the base Section 4.3 uses when it describes the extreme scenario's cognitive jobs. With employment counted from 2024, the base of Table 3's labor income rows, the same transfer is 87 percent. The footnote's number is the mid-2026 figure. Its wording, which compares income with its level without AI, reads more naturally on the 2024 base.

Two points of notation remain, both rows of [](#tbl-inventory). Equation (8) writes the log gain as $a_t = a_0 + g_a (t - t_0)$, with the base year $t_0$ set to 2024 in Table A.2, but the paper's Table 1 gives the gain at the mid-2026 anchor, and its implied 2030 values of 0.30, 0.45, and 0.80 equal the anchor value plus three and a half years of slope, so the reproduction and the explorer start the line at mid-2026. Proposition 1's wage, Equation (16), omits the ideas term that Table A.1's wage row includes. The reproduction follows Table A.1, whose version also gives Section 2.1.3 its wage of 1.9 percent.

A date for the starting rate, a word on which channel each number includes, and the employment base behind the 84 would let a reader check each passage directly.

### The Public Data behind the Calibration

For every input that comes from public data, the reproduction recomputes the value from its original source, in [](#tbl-public-data). "Matches" means the recomputation reproduces the printed value at its rounding. "Consistent" means the public source measures a close cousin of the paper's statistic, such as seasonally adjusted gross flows in place of matched IPUMS records, and falls within a few percent. "Open" means the recomputation differs by more than that and I have not pinned down why. Of the thirteen inputs, eleven match or are consistent and two remain open.

:::{table} The calibration's public inputs recomputed from their original sources. The paper's job-finding and separation statistics come from matched IPUMS-CPS records, which require an account to download. The BLS flows and the replication files of {cite:t}`carrillo2023unemployment` give public cross-checks that fall within a few percent.
:label: tbl-public-data

| Input | Paper | Public recomputation | Source | Status |
|---|---|---|---|---|
| Cognitive share of employment | 0.624 | 0.6235 | CPS 2025 annual averages, BLS Table 11 | matches |
| Normal search pool, share of the labor force | 0.038 | 0.0384 | CPS 2025 annual averages, BLS Tables 11 and 25 | matches |
| Vacancy filling | 4.0 percent a working day, 26 days, 0.65 within a month | 3.987 percent, 25.92 days, 0.6528 | JOLTS, following {cite:t}`davis2013vacancies` | matches |
| Firm use of AI | 18 percent of firms, 32 employment-weighted; 23 with worker task use | the same | {cite:t}`bonney2026microstructure` | matches |
| Automation share of AI use | about half on Claude.ai, three quarters on the API | the same | {cite:t}`appel2025index` | matches |
| Rated feasibility of cognitive work | 2030 affected mass between 0.2 and 0.5 | 0.4334, employment-weighted | {cite:t}`eloundou2024gpts` | consistent |
| Job finding from unemployment, per month | 0.219 | 0.2243 | BLS gross flows, 2010-19 | consistent |
| Job loss from employment, per month | 1.22 percent | 1.2547 percent | BLS gross flows, 2010-19 | consistent |
| Separation rate, other relative to cognitive | 2.20 | 2.0968 | BLS short-term unemployment by last occupation, 2011-19 | consistent |
| Job finders changing group: from cognitive, from other, all | 18.7, 11.2, 14.3 percent | 18.31, 11.32, 14.26 percent | {cite:t}`carrillo2023replication`, IPUMS-CPS excerpt, 2010-19 | consistent |
| Normal search discount $\bar\mu$ | 0.17 | 0.1692 | from the switching shares above | consistent |
| Elasticity of quits to job finding | 0.53 | 0.5279 and 0.5286 in two monthly specifications, 0.5379 in the standard one | JOLTS quits and CPS flows, 2001-19 | open |
| Observed exposure, mid-2026: cognitive, other, overall | 0.22, 0.01, 0.14 | 0.1888, 0.0097, 0.1212 | {cite:t}`massenkoff2026exposure`, CPS weights | open |
:::

For observed exposure, the gap most likely comes from how occupation-level scores are aggregated onto the CPS's occupation lines. Where one line combines several detailed occupations, the recomputation averages them without weights, since no sub-weights are published. The code for every row is in the tests that download each source, which fail rather than skip when a source file is missing.

(sec-validation)=
## The Checks

The first check runs the explorer's code as a reference solution and compares full monthly paths. The validation script downloads the bundle from the authors' site, checks it against a recorded SHA-256 checksum, and runs its model code under Node.js with the same scenario and calibration as the reproduction, once for every configuration the comparison uses. Every series the explorer reports enters the comparison, in every month. The left panel of [](#fig-agreement) shows the result for the 25 configurations its caption lists. At its widest the gap is $3.5 \times 10^{-14}$, against a tolerance of $10^{-12}$ that lies well above the rounding error that series of order one accumulate over 72 to 132 monthly steps and some 500 bisections. Every configuration lies inside the tolerance.

The second compares the published numbers with the reproduction at the paper's printed rounding. A number counts as reproduced when the reproduction rounds to it at the precision the paper prints. Of the 226 numbers, 211 are predicted, in that the paper's text fixes how each is computed before any comparison, so that matching it tests the reproduction. The other 15 are fitted, in that I had to take a definition or an unstated parameter from the explorer or infer it by matching, a weaker test. Split the other way, as the introduction splits them, 43 are inputs the model takes as given, which no error in its dynamics could move, and 183 are outputs the simulation produces. [](#tbl-published-numbers) counts them by source. The right panel of [](#fig-agreement) places all 226 inside their rounding.

:::{figure} figures/validation-3.png
:label: fig-agreement
:width: 100%
Left: the largest gap between the reproduction and the explorer, over every series and every month, for 25 configurations. They cover the three scenarios, the robustness settings of Tables 5 and 6, first-order mode, in which the first-order rows of Table A.1 replace the exact ones, two points away from the calibration run to 2032 and 2035, seven sets of answers to the explorer's quiz, its five data options, and two runs to 2040. Right: each of the 226 published numbers' residual in half-units of its last printed digit, with the printed rounding, the range within which a number prints exactly as published, shaded. Hollow dots mark the 15 fitted numbers.
:::

```{include} fragments/reproduction-published-numbers.md
```

The numbers that lie closest to the edge of their band decide what the second check can detect. Cognitive unemployment in the extreme scenario, 17.94905 in the reproduction and printed as 17.9, lies only 0.00095 below its rounding boundary at 17.95. The supplement's [](#fig-binding) shows every output's margin.

Beside the two checks, a third comparison tests the reading rather than the arithmetic. Claude Code, running Opus 5 and restricted to the paper's text, wrote a second implementation of the model with the explorer's code and this reproduction's code withheld from it. Once the restriction was lifted, I verified that it uses only the paper's printed inputs. The second implementation is independent of the explorer and of this reproduction, though not of the author. From a list of 211 targets transcribed by hand from the paper, drawn up apart from the 226 numbers here, it reaches 199 under the best readings of the text it could find. Its misses trace to the printed calibration it runs on, to the quit order, and to the mid-2026 rate the notes take up. On the quit order it converts before splitting. Appendix A says the rows of Table A.1 hold exactly given their right-hand sides. The quit row holds that way, in the rate actually applied, only when quits are converted first, which makes converting first the more natural reading of the text alone. Given the same data inputs as this reproduction, its monthly paths come within $7 \times 10^{-5}$ to $4 \times 10^{-4}$ of this reproduction's, depending on the case, and the whole gap comes from the quit order. With that order aligned, the two implementations agree to $6 \times 10^{-14}$. Gaps of that size are roughly the resolution of the published tables, which separate the two readings only at the explorer's quit share. The comparison covers the model's monthly paths. It leaves out how numbers are reported, Footnote 14, and the explorer's page.

(sec-detection)=
## Detection Thresholds

To measure what each check can reject, I plant four errors in the reproduction's own code, the mutation-testing check of the introduction. Each is a plausible misreading of the paper whose effect on the 2030 aggregates is modest:

- quits enter the flow equations as the quoted monthly fraction, never converted to the continuous rate $-\ln(1 - \hat q)$ of Appendix A;
- the flow block takes its gaps against this month's targets instead of next month's, a one-month timing offset;
- the first-order rows of Table A.1 replace the exact ones;
- the normal-times steady state is solved at the scenario's search discount instead of the normal-times one.

At full strength every planted error fails both checks. The largest gaps to the explorer run from $1.4 \times 10^{-3}$ to $7.9 \times 10^{-2}$. Each error moves between 8 and 72 published numbers outside their rounding.

How weak an error can each check still detect? A planted error at strength $s$ blends the correct computation with the erroneous one, so that each planted quantity is $1 - s$ times its correct value plus $s$ times the error's. I sweep $s$ over twelve orders of magnitude to find the weakest version of each error that each check detects.

:::{raw:typst}
// Three panels in a row take the margin rail as well as the text column.
#widenNextFigure()
:::

:::{figure} figures/validation-1.png
:label: fig-sweep
Left: the full-strength gaps, labeled with the series where each is largest, against the 25 correct comparisons. Middle: published outputs outside their rounding at full strength, counted over all outputs and over the modest scenario's column alone. Right: for each planted error, in the same row order, the span of strengths that passes every published number and still fails the explorer comparison. The explorer's threshold is the path tolerance divided by the error's full-strength gap, rounded up to the sweep's grid of four points per order of magnitude, because a weak error's gap grows in proportion to its strength.
:::

The explorer comparison detects the four planted errors from strengths between $1.8 \times 10^{-11}$ and $10^{-9}$. The published numbers detect them only from strengths between 0.01 and 0.18, for each error 8.3 to 9.0 orders of magnitude above the explorer's threshold. A planted error can therefore be strong enough to shift monthly paths by several thousandths and still leave every published number inside its rounding.

A few numbers set the tables' thresholds. For three of the four planted errors, the extreme scenario's cognitive unemployment, the number closest to its boundary, is the first to fail. The fourth error, the steady state solved at the scenario's search discount, first moves extreme GDP growth (15.445, printed 15.4) and the substantial scenario's wage in all other occupations (5.863, printed 5.9), which responds strongly to the search discount. Nearly every rejection comes from the extreme scenario's columns. On its own, the modest column rejects between none and three published numbers per error.

The strongest version of each error that still passes every published number does not change any of them by more than 0.07 in the units the paper prints, against 0.13 to 2.5 at full strength. Agreement with the published tables therefore establishes a reimplementation to within economically negligible differences. Only agreement with the explorer's code in every month establishes that it is the authors' model.

## The Package

Agreement with printed tables cannot establish a reproduction. A package that claims one therefore has to hold the authors' own output and replay it, under a standard that makes the replay a condition of the claim. An Econ-ARK REMARK is a public repository indexed in the Econ-ARK catalog under a standard with one operative rule, which makes the reproduction of every result a requirement of the form. It carries a script, `reproduce.sh`, and in the standard's words, "if this script fails, your reproduction is assumed to not have worked." Around that script the standard requires a Dockerfile that runs it in a fixed environment, a README, a license, a tagged release, and, at its highest tier, a Zenodo DOI (a permanent identifier for an archived snapshot) bound to one commit. Each package chooses which results its script checks. I chose to check everything the report says.

Running the script installs the fixed environment, downloads the public data behind the calibration recheck from its original sources, runs the test suite, and builds the site. In that suite the table fragments of the report and the supplement, [](#tbl-inventory) included, must equal what the reproduction computes now, and each of the 226 published numbers must print as published at its rounding. It replays the explorer's outputs, recorded under a SHA-256 checksum of the authors' bundle, against the reproduction in every series and every month, runs the four planted errors at full strength and at their thresholds, and recomputes the calibration's public inputs from their sources, failing when a source file is missing instead of skipping it. Because the site build executes the supplement's cells, its tables are outputs of the same code. The second implementation, written from the paper's text alone, is part of the package too, with the test that compares the two and isolates the quit order as their only difference.

The authors' publication is diligent by the field's standards. An explorer that runs the model in the reader's browser is more than most papers offer. This report's strongest check depends on it. The publication is not, though, complete and airtight in the way the REMARK form requires, since it has no single script whose failure disqualifies the result, run in a fixed environment against a fixed commit. The calibration record and the definitions behind the page's numbers exist only in the explorer's bundle, which a paper cannot ask its readers to open, and Footnote 14's parameters appear in no public source. A document can state such an item, but it cannot keep the item true once the code moves. This reproduction supplies all three and keeps them under test, since a later change to the code that moved a published number, or a redeployment of the explorer that moved a recorded path, fails the script.

## Conclusion

Every published result of {cite:t}`korinek2026scenarios` stands. The monthly model can be reimplemented from its Appendix A once the twelve inputs, definitions, and orderings of [](#tbl-inventory) are in hand. The text leaves them open. This report recovers each and holds it under test. With them the reproduction matches the explorer's own code to within $3.5 \times 10^{-14}$ and all 226 published numbers within their rounding. The match to the tables establishes less than the match to the explorer, as it would for any paper. No table printed to a few digits can reject errors that shift the monthly paths by several thousandths. Nor can the tables by themselves decide the one open reading of the model's equations that moves a published number, which the explorer's paths decide at once. Nine of the twelve items could be stated in the paper's text in a sentence each, one of them a single extra printed digit in its Table 1. Three belong elsewhere: the explorer page's own definitions, its quiz bounds, and the confidential survey. Even a paper that stated all nine would not be a reproduction, because a statement in a document cannot fail when the code moves. As a robustness check, the reproduction tests how far the paper's results depend on how its text is read. The paper's own Tables 5 and 6 vary the elasticity of capital supply and the rigidity of the cognitive wage without varying the reading. The results hardly depend on it, since the two readings of its quit equation that the tables accept differ by no more than 0.011 in any published number, and the planted errors the tables miss do not change any by more than 0.07. Every input needed to say so is now in the open and under test.

Econ-ARK will use this reproduction to develop models in which household saving, which the authors set aside deliberately, supplies the economy's capital. That turns the capital stock into an outcome of the scenario and measures its distributional effects, household by household. The monthly transitions recovered here, which neither the paper nor the explorer displays, are the income risk those households would face.

+++ {"part": "acknowledgments"}

I thank the authors for a paper detailed enough to reimplement and for an explorer that makes every scenario easy to see, and Christopher Carroll for comments on this report and on the household work that builds on it.

+++ {"part": "data_availability"}

The reproduction's code and tests are in its replication package, under `code/econ_scenarios/` and `code/validation/`. Because the explorer is published without a license, the package holds a record of the explorer's outputs and none of its code, with the script that downloads the authors' bundle and regenerates the record. The scripts `code/validation/upstream_*.py` download the public data behind the recheck of the calibration from their original sources. The matched IPUMS-CPS records require an account.

+++ {"part": "declaration"}

This reproduction is independent work, done in good faith and out of admiration for the original. It is not an Anthropic product. Neither Anthropic nor the paper's authors have reviewed or endorsed it. The model and its ideas belong to the authors; any mistake in the reproduction is mine.

During the preparation of this work the author used Claude Code (Anthropic) to assist in editing and revising the prose and the code, and in checking the numerical claims in the text against the reproduction's code. The second implementation of [](#sec-validation) is the tool's own work: Claude Code wrote it from the paper's text alone, with the explorer's code and the reproduction's code withheld, and the author then verified that it uses only the paper's printed inputs. After using this tool, the author reviewed and edited the content as needed and takes full responsibility for the content of the publication.

+++
