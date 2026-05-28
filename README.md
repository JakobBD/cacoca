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

Routes (technology chains) are defined in `config/posted_routes.yml`. Adding a new sector there is possible without any Python changes. The active config is `config/posted_config_slides.yml`.

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


