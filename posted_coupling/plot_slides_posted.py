"""
Steel LCOx analysis using POSTED + TEAM data, plotted with CaCoCa tools.

Run from the cacoca project root:
    python posted_coupling/plot_slides_posted.py

Routes (projects) are defined inline below. Add or remove entries in
ROUTES_BFBOF and adjust the ProcessChain / aggregate calls for new technologies.
"""
import types

import pandas as pd
from cet_units import ureg, Q

from posted import TEDF
from team.tools import ProcessChain, calc_LCOX_pc, calc_GHGI_pc, calc_emissions

from cacoca.setup.read_input import read_config
from cacoca.output.plot_stacked_bars import plot_stacked_bars_multi
from cacoca.output.plot_price_scenarios import plot_price_scenarios
from cacoca.output.plot_tools import change_output_subdir_by_filename

from posted_coupling.run_posted import COMPONENT_MAP, prices_from_config, team_to_cacoca


# =============================================================================
# CONFIGURATION
# =============================================================================

config = read_config("config/config_slides.yml")

ureg.define_flows(["H2", "NG", "CH4", "coal"])

var_units = {
    "LCOX": "EUR_2024 / t",
    "GHGI": "t CO2eq / t",
}

# =============================================================================
# LOAD DATA FROM POSTED
# =============================================================================

# Emission factors (supply-chain emissions for electricity and hydrogen)
emi_factors_posted = TEDF.load("Emission Factor").select(with_parent=True)
emi_factors_custom = pd.DataFrame.from_records([
    {"variable": "Emission Factor|Electricity|Supply Chain",
     "value": 20.0, "unit": "g CO2eq / kWh"},
    {"variable": "Emission Factor|Hydrogen|Supply Chain",
     "value": 40.0, "unit": "g CO2eq / kWh_H2_LHV"},
])
emi_factors = pd.concat([emi_factors_posted, emi_factors_custom], ignore_index=True)

tech_bfbof = (
    TEDF.load("Tech|Integrated Blast Furnace and Basic Oxygen Furnace")
    .aggregate(
        carbon_capture=["No Capture", "End-of-pipe"],
        units={
            "Output Capacity|Steel Hot-rolled Coil": "t/yr",
            "Output|Steel Hot-rolled Coil": "t",
        },
        append_references=True,
    )
    .assign(variable=lambda df: "Tech|Int-BF-BOF|" + df["variable"])
)

tech_dri = (
    TEDF.load("Tech|Direct Reduction of Iron")
    .aggregate(append_references=True)
    .team.perform(calc_emissions, using=emi_factors, only_new=False)
    .assign(variable=lambda df: "Tech|Direct Reduction of Iron|" + df["variable"])
)

tech_eaf = (
    TEDF.load("Tech|Electric Arc Furnace")
    .aggregate(
        mode="Primary",
        reheating="w/o reheating",
        append_references=True,
    )
    .team.perform(calc_emissions, using=emi_factors, only_new=False)
    .assign(variable=lambda df: "Tech|Electric Arc Furnace|" + df["variable"])
)

tech_cast = (
    TEDF.load("Tech|Steel Casting")
    .aggregate(append_references=True)
    .team.perform(calc_emissions, using=emi_factors, only_new=False)
    .assign(variable=lambda df: "Tech|Steel Casting|" + df["variable"])
)

tech_roll = (
    TEDF.load("Tech|Steel Hot Rolling")
    .aggregate(append_references=True)
    .team.perform(calc_emissions, using=emi_factors, only_new=False)
    .assign(variable=lambda df: "Tech|Steel Hot Rolling|" + df["variable"])
)

# =============================================================================
# DEFINE ROUTES  (add new routes here)
# =============================================================================

route_bfbof = ProcessChain(
    "Int-BF-BOF -> Steel Hot-rolled Coil",
    name="BF-BOF",
)

route_dreaf = ProcessChain(
    "Direct Reduction of Iron -> Direct Reduced Iron => "
    "Electric Arc Furnace -> Steel Liquid => "
    "Steel Casting -> Steel Slab => "
    "Steel Hot Rolling -> Steel Hot-rolled Coil",
    name="DR-EAF",
)

# =============================================================================
# BUILD ASSUMPTIONS FROM CACOCA SCENARIOS
# =============================================================================

# Full price assumptions including GHG Price — used only by team_to_cacoca
# to extract CO2 Price per period for CaCoCa's CO2 cost computation.
assumptions = pd.concat([
    prices_from_config(config),
    pd.DataFrame.from_records([
        {"variable": "Price|Biomethane", "value": 50.0, "unit": "EUR_2024/MWh_NG_LHV"},
    ]),
], ignore_index=True)

# Tech-only assumptions for TEAM's perform_multi — GHG Price excluded so TEAM
# does not embed CO2 costs as GHG Pricing|... components inside LCOX (those
# would double-count against CaCoCa's own CO2 cost bar).
tech_assumptions = pd.concat([
    prices_from_config(config, include_ghg=False),
    pd.DataFrame.from_records([
        {"variable": "Price|Biomethane", "value": 50.0, "unit": "EUR_2024/MWh_NG_LHV"},
    ]),
], ignore_index=True)

# =============================================================================
# TEAM CALCULATIONS
# =============================================================================

df_calc_bfbof = (
    tech_bfbof
    .team.perform(
        route_bfbof.calc_scaling,
        func_unit={"Int-BF-BOF": {"Steel Hot-rolled Coil": Q("1t")}},
    )
    .team.perform_multi(
        [
            dict(func=calc_GHGI_pc, name="BF-BOF",
                 reference="Int-BF-BOF|Steel Hot-rolled Coil"),
            dict(func=calc_LCOX_pc, name="BF-BOF",
                 reference="Int-BF-BOF|Steel Hot-rolled Coil",
                 interest_rate=0.08, book_lifetime="20 years"),
        ],
        using=tech_assumptions,
        only_new=True,
    )
    .team.varsplit("?variable|?route|?process|*component")
    .assign(carbon_capture=lambda df: df["carbon_capture"].map(
        {"No Capture": "Conv", "End-of-pipe": "CCS"}
    ))
    .team.varcombine("{route}-{carbon_capture}", var_col="route")
    .team.unit_to(var_units)
)

df_calc_dreaf = (
    pd.concat([tech_dri, tech_eaf, tech_cast, tech_roll], ignore_index=True)
    .team.perform(
        route_dreaf.calc_scaling,
        func_unit={"Steel Hot Rolling": {"Steel Hot-rolled Coil": Q("1t")}},
    )
    .team.perform_multi(
        [
            dict(func=calc_GHGI_pc, name="DR-EAF",
                 reference="Steel Hot Rolling|Steel Hot-rolled Coil"),
            dict(func=calc_LCOX_pc, name="DR-EAF",
                 reference="Steel Hot Rolling|Steel Hot-rolled Coil",
                 interest_rate=0.08, book_lifetime="20 years"),
        ],
        using=tech_assumptions,
        only_new=True,
    )
    .team.varsplit("?variable|?route|?process|*component")
    .team.varcombine("{mode}-{route}", var_col="route")
    .team.unit_to(var_units)
)

df_calc = pd.concat([df_calc_bfbof, df_calc_dreaf], ignore_index=True)

# =============================================================================
# CONVERT TO CACOCA FORMAT
# =============================================================================

cost_and_em = team_to_cacoca(df_calc, assumptions, COMPONENT_MAP)

# =============================================================================
# PLOTTING
# =============================================================================

change_output_subdir_by_filename(config, __file__)
config["show_figs_in_browser"] = True
config["save_figures"] = False  # kaleido binary not available; set True for final output

# Price scenario overview (reuses CaCoCa's existing plot)
plot_price_scenarios(types.SimpleNamespace(config=config))

# Stacked bar comparison — list the route names produced by varcombine above
project_names = ["BF-BOF-Conv", "BF-BOF-CCS", "H2-DR-EAF"]
plot_stacked_bars_multi(
    cost_and_em,
    config,
    project_names=project_names,
    cost_per="product",
)
