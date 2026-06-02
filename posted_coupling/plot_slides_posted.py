"""
Steel and Cement LCOx analysis using POSTED + TEAM data, plotted with CaCoCa tools.

Routes are defined in config/posted_routes_steel.yml and config/posted_routes_cement.yml.
Run from the cacoca project root:
    python posted_coupling/plot_slides_posted.py
"""
import types
import os

import pandas as pd
from cet_units import ureg

from posted import TEDF

from cacoca.setup.read_input import read_config
from cacoca.output.plot_stacked_bars import plot_stacked_bars_multi
from cacoca.output.plot_price_scenarios import plot_price_scenarios

from posted_coupling.routes import load_routes, calc_posted_routes


# =============================================================================
# CONFIGURATION
# =============================================================================

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
# CALCULATION & PLOTTING FOR EACH CONFIG
# =============================================================================

for product in ['steel', 'cement']:
    print(f"\n{'='*60}")
    print(f"Processing {product.upper()}")
    print(f"{'='*60}")
    
    try:
        config = read_config(f"config/posted_config_{product}.yml")
        os.makedirs(config["output_dir"], exist_ok=True)
        
        routes = load_routes(config["routes_file"])
        cost_and_em = calc_posted_routes(routes, config, emi_factors, extra_assumptions)
        
        plot_price_scenarios(types.SimpleNamespace(config=config))
        
        plot_stacked_bars_multi(
            cost_and_em,
            config,
            project_names=config["project_names"],
            cost_per="product",
        )
        
        print(f"{product.upper()} processing complete!")
    
    except Exception as e:
        print(f"WARNING: {product.upper()} processing failed with error:")
        print(f"  {type(e).__name__}: {str(e)[:200]}")
        print(f"  Skipping {product}...")
        continue

print(f"\n{'='*60}")
print("Processing complete!")
print(f"{'='*60}")
