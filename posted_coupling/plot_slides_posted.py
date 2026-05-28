"""
Steel LCOx analysis using POSTED + TEAM data, plotted with CaCoCa tools.

Run from the cacoca project root:
    python posted_coupling/plot_slides_posted.py
"""
import types

import pandas as pd
from cet_units import ureg

from posted import TEDF

from cacoca.setup.read_input import read_config
from cacoca.output.plot_stacked_bars import plot_stacked_bars_multi
from cacoca.output.plot_price_scenarios import plot_price_scenarios
from cacoca.output.plot_tools import change_output_subdir_by_filename

from posted_coupling.run_posted import TEDFSpec, RouteSpec, calc_posted_routes


# =============================================================================
# CONFIGURATION
# =============================================================================

config = read_config("config/config_slides_posted.yml")

ureg.define_flows(["H2", "NG", "CH4", "coal"])

# =============================================================================
# EMISSION FACTORS AND EXTRA ASSUMPTIONS
# =============================================================================

emi_factors = pd.concat([
    TEDF.load("Emission Factor").select(with_parent=True),
    pd.DataFrame.from_records([
        {"variable": "Emission Factor|Electricity|Supply Chain",
         "value": 20.0, "unit": "g CO2eq / kWh"},
        {"variable": "Emission Factor|Hydrogen|Supply Chain",
         "value": 40.0, "unit": "g CO2eq / kWh_H2_LHV"},
    ]),
], ignore_index=True)

extra_assumptions = pd.DataFrame.from_records([
    {"variable": "Price|Biomethane", "value": 50.0, "unit": "EUR_2024/MWh_NG_LHV"},
])

# =============================================================================
# ROUTES
# =============================================================================

routes = [
    RouteSpec(
        name="BF-BOF",
        chain="Int-BF-BOF -> Steel Hot-rolled Coil",
        techs=[
            TEDFSpec(
                "Int-BF-BOF",
                tedf="Tech|Integrated Blast Furnace and Basic Oxygen Furnace",
                aggregate={
                    "carbon_capture": ["No Capture", "End-of-pipe"],
                    "units": {
                        "Output Capacity|Steel Hot-rolled Coil": "t/yr",
                        "Output|Steel Hot-rolled Coil": "t",
                    },
                },
            ),
        ],
        func_process="Int-BF-BOF",
        func_flow="Steel Hot-rolled Coil",
        varcombine="{route}-{carbon_capture}",
        rename={"carbon_capture": {"No Capture": "Conv", "End-of-pipe": "CCS"}},
    ),
    RouteSpec(
        name="DR-EAF",
        chain=(
            "Direct Reduction of Iron -> Direct Reduced Iron => "
            "Electric Arc Furnace -> Steel Liquid => "
            "Steel Casting -> Steel Slab => "
            "Steel Hot Rolling -> Steel Hot-rolled Coil"
        ),
        techs=[
            TEDFSpec("Direct Reduction of Iron", calc_emissions=True),
            TEDFSpec(
                "Electric Arc Furnace",
                aggregate={"mode": "Primary", "reheating": "w/o reheating"},
                calc_emissions=True,
            ),
            TEDFSpec("Steel Casting", calc_emissions=True),
            TEDFSpec("Steel Hot Rolling", calc_emissions=True),
        ],
        func_process="Steel Hot Rolling",
        func_flow="Steel Hot-rolled Coil",
        varcombine="{mode}-{route}",
    ),
]

# =============================================================================
# CALCULATION
# =============================================================================

cost_and_em = calc_posted_routes(routes, config, emi_factors, extra_assumptions)

# =============================================================================
# PLOTTING
# =============================================================================

change_output_subdir_by_filename(config, __file__)

plot_price_scenarios(types.SimpleNamespace(config=config))

project_names = ["BF-BOF-Conv", "BF-BOF-CCS", "H2-DR-EAF"]
plot_stacked_bars_multi(
    cost_and_em,
    config,
    project_names=project_names,
    cost_per="product",
)
