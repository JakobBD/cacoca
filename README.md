# CaCoCa

CaCoCa (The Carbon Contracts Calculator) is a tool to model carbon contracts for difference (CCfDs) for industrial decarbonization projects. Abatement cost time curves can be calculated, and auctions of such carbon contracts (where the projects bidding the lowest carbon price are awarded contracts) can be modeled.

The techno-economic input data provided in this repository is incomplete and not to be relied upon. It only serves as an example for the functionality of the code. It is advised to use your own data.

## Installation

The Python version and packages are managed using [PEP 621](https://peps.python.org/pep-0621/). Packages are listed in the file [pyproject.toml](pyproject.toml). Detailed instructions for installation can be found in the [documentation](doc/100_getting_started.md).

## Quick start

Runs are configured using a YAML input file. Example input files are located in the `config` folder.

**Auction simulation** — multi-round bidding with budget caps:
```
uv run python cacoca.py config/config.yml
```

**Cost/emissions analysis and plotting** — using CaCoCa's native tech data:
```
uv run python plot_slides.py
```

Both commands should be run from the repository root.

## POSTED Coupling

CaCoCa integrates with the [POSTED](https://github.com/PhilippVerpoort/posted) techno-economic database as an alternative data source. POSTED is installed automatically as a dependency via `uv sync`.

To run an analysis using POSTED data:
```
uv run python posted_coupling/plot_slides_posted.py
```

The script loops over a list of products (e.g. `steel`, `cement`). For each product it reads a config file, computes LCOX and GHGI for all routes, and calls `plot_stacked_bars_multi` to produce the output slides. Each product requires two files described below.

### Config file (`config/posted_config_<product>.yml`)

Controls financial parameters, output settings, and which price scenario to use for each input commodity.

```yaml
default_wacc: 0.08        # weighted average cost of capital
book_lifetime: 25         # economic lifetime in years

routes_file: config/posted_routes_<product>.yml
project_names:            # route labels shown in the bar chart, in order
  - RouteA
  - RouteB

show_figures: true
show_figs_in_browser: true
save_figures: false
output_dir: output/plot_slides_posted
filename_prefix: <product>

scenarios_dir: data/scenarios/basic/
scenarios_actual:
  prices:                 # component name → scenario name in prices_fuels.csv
    Electricity: 'EEX Jahresfuture_DE'
    CO2: 'PIKExpertGuess-CO2'
    # ... all commodities consumed by any tech in the routes file
```

`project_names` must match the route labels produced by `varcombine` (see below). Only components listed under `scenarios_actual.prices` that are also present in `CACOCA_TO_TEAM_PRICE_MAP` in `posted_coupling/routes.py` are passed to TEAM; unknown ones are silently ignored. If a listed scenario name does not exist in `prices_fuels.csv`, a `ValueError` is raised at startup with the available scenario names.

### Routes file (`config/posted_routes_<product>.yml`)

Defines one or more technology chains. Each top-level key is a route name.

```yaml
routes:
  MyRoute:
    chain: "ProcessA -> OutputFlow => ProcessB -> FinalProduct"
    techs:
      - process_name: "ProcessA"
        tedf: "Tech|ProcessA"        # optional; defaults to Tech|<process_name>
        aggregate:
          some_filter: ["Option1", "Option2"]   # passed to TEDF.aggregate()
          units:
            "Output Capacity|Flow": "t/yr"      # unit overrides for aggregate()
        calc_emissions: false        # set true to compute scope 1+2 via emission factors
      - process_name: "ProcessB"
        calc_emissions: true
    func_process: "ProcessB"         # process that defines the functional unit
    func_flow: "FinalProduct"        # flow that defines the functional unit (1 t)
    varcombine: "{route}-{some_filter}"   # template for route label in output
    rename:                               # optional: map filter values to display names
      some_filter:
        "Option1": "Conv"
        "Option2": "CCS"
```

Key fields:

- **`chain`**: ProcessChain diagram string. `->` connects a process to its output flow; `=>` passes a flow as input to the next process.
- **`techs`**: ordered list of process steps. Each step's data is loaded from POSTED as `Tech|<process_name>` (or the explicit `tedf` path) and aggregated. The `aggregate` dict is forwarded verbatim to `TEDF.aggregate()` — use it to filter by field values (e.g. `carbon_capture: ["No Capture", "End-of-pipe"]`) or to override output units.
- **`calc_emissions`**: if `true`, emissions are computed for that step using the emission factors defined in `plot_slides_posted.py`, or standard emission factors from POSTED. Required for any process that consumes electricity, hydrogen, or other carriers with non-zero supply-chain emissions.
- **`func_process` / `func_flow`**: identify the reference process and flow for normalisation (functional unit = 1 t of `func_flow`).
- **`varcombine`**: Jinja-style template that assembles the route label from the route name and any filtered field columns (e.g. `{route}-{carbon_capture}`). The resulting labels must match `project_names` in the config file.
- **`rename`**: remaps field values to shorter display names before `varcombine` is applied.

### Adding a new product

1. Create `config/posted_routes_<product>.yml` with at least one route.
2. Create `config/posted_config_<product>.yml`. List all commodities consumed across your routes under `scenarios_actual.prices`, picking a scenario name from `data/scenarios/basic/prices_fuels.csv` for each.
3. Add `'<product>'` to the `for product in [...]` list in `posted_coupling/plot_slides_posted.py`.
4. If any process step uses `calc_emissions: true`, add emission factors for its input flows to the `emi_factors` DataFrame in `plot_slides_posted.py` (zero is acceptable as a placeholder).
5. Add any commodity not yet in `CACOCA_TO_TEAM_PRICE_MAP` in `posted_coupling/routes.py`, specifying the TEAM variable name and the unit that matches the price data in `prices_fuels.csv`.

### Adding a new route to an existing product

Add a new entry under `routes:` in the relevant routes YAML. Then append its label(s) to `project_names` in the config YAML. No changes to Python code are required unless the route introduces a new commodity type.

## Contributors

The authors of CaCoCa are:

Jakob Dürrwächter\
Robin Blömer\
Philipp Verpoort\
Bennet Weiss\
Paul Effing\
Johannes Eckstein\
Falko Ueckerdt

## License

CaCoCa is Copyright (C) 2023, Jakob Dürrwächter, Robin Blömer, Johannes Eckstein and Falko Ueckerdt and is released under the terms of the
GNU General Public License v3.0. For the full license terms see
the included [`LICENSE` file](LICENSE).

## Reference / Please cite

To cite CaCoCa, please use:

J. Dürrwächter, R.Blömer, P. Verpoort, B. Weiss, P. Effing, J. Eckstein, F. Ueckerdt (2023). _CaCoCa: The Carbon Contracts Calculator._ Version 2.0.0, <https://github.com/JakobBD/cacoca>.

A BibTeX entry for LaTeX users is:

 ```latex
@Manual{,
  title = {CaCoCa: The Carbon Contracts Calculator},
  author = {Jakob Dürrwächter and Robin Blömer and Philipp Verpoort and Bennet Weiss and Paul Effing and Johannes Eckstein and Falko Ueckerdt},
  year = {2023},
  note = {Version 2.0.0},
  url = {https://github.com/JakobBD/cacoca},
}
```

## Documentation

Further documentation can be found in the [`doc/` folder](doc/).


