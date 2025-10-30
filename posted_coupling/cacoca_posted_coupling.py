import pandas as pd
from pathlib import Path
from typing import Union

from posted.noslag import DataSet

# TODO heat emission factor?!
# TODO Hydrogen could be both energy and feedstock, same for Natural Gas
# TODO handle CAPEX annualized
ENERGY_TYPES = ["Electricity", "Coal", "Natural Gas", "Heat", "Hydrogen"]
FEEDSTOCK_TYPES = ["Oxygen", "Iron Ore", "Scrap Steel", "Water", "Ammonia", "Captured CO2",
                   "Steel Slab", "Steel Liquid", "Cooling Water", "Methanol",
                   "Alloys", "Directly Reduced Iron", "Graphite Electrode", "Lime",
                   "Nitrogen", "Steel Scrap"]
EMISSION_TYPES = ["CO2"]
ALLOWED_TYPES = {
    "High CAPEX",
    "Low CAPEX",
    "Energy demand",
    "Feedstock demand",
    "OPEX",
    "Emissions",
}
EXPECTED_REMOVAL_TYPES = {
        # specified in project description
        "Lifetime",
        "OCF",
        "Output Capacity",
        "Output", # TODO remove also Output|...
        "Total Output Capacity",

        "Capture Rate", # already in tech name
        "Total Input Capacity", # TODO what do do with this?
        "Storage Capacity", # TODO what do do with this?
        "Total Production Expenditure", # TODO what do do with this?
        "CAPEX Annualised", # TODO what do do with this?
    }
POSTED_OPEX_COMPONENTS = ['OPEX Variable', 'OPEX Fixed']
ALLOWED_COMPONENTS = [
    "CAPEX",
    "Additional OPEX",
]
TRANSLATION = {"Fossil Gas": "Natural Gas"}
EXCLUDED_TECHNAMES = [
    "Methanol Synthesis with Reforming", # POSTED issue: uses LVH/a unit that Posted does not know
    "Naphtha Steam Cracking", # POSTED issue: kilogram / second' ([mass] / [time]) to 'metric_tonne" failed
    "NGL to Olefins", # POSTED issue: concatenation fails
]


# TODO add low capex
# TODO get emissions via emissions factor
# TODO sort by Technology

def generate_cacoca_input(target_folder: Path, posted_technames: Union[str, list] = None, posted_datafolder: Path = None):

    # determine technames to process
    if posted_technames is not None:
        technames = posted_technames if isinstance(posted_technames, list) else [posted_technames]
    elif posted_datafolder is not None:
        technames = find_posted_technames(posted_datafolder)
        if not technames:
            raise ValueError(f"No Posted technology files found in folder: {posted_datafolder}")
        technames = [name for name in technames if name not in EXCLUDED_TECHNAMES]
    else:
        raise ValueError("Either posted_datafolder or posted_technames must be provided.")
    
    for techname in technames:
        print(f"Processing Posted technology file: {techname}")
        df_posted, posted_parent_variable = get_posted_df(techname)
        df_cacoca = translate_posted_df_to_cacoca_df(df_posted, posted_parent_variable)
        save_cacoca_dataframe(df_cacoca, target_folder, techname)

def find_posted_technames(posted_datafolder: Path):
    """Find available Posted technology files in the given folder."""
    return [f.stem for f in posted_datafolder.glob("*.csv")]

def get_posted_df(posted_techname):
    posted_parent_variable = f"Tech|{posted_techname}"
    teds = DataSet(posted_parent_variable)
    df_posted = teds.aggregate(region="World", period=2025) 
    df_posted.drop(columns=["region"], inplace=True) # region is redundant
    return df_posted, posted_parent_variable

def translate_posted_df_to_cacoca_df(df_posted: pd.DataFrame, posted_parent_variable: str) -> pd.DataFrame:
    df_cacoca = initiate_cacoca_dataframe(df_posted, posted_parent_variable)
    df_cacoca = aggregate_opex(df_cacoca)
    df_cacoca = filter_cacoca_dataframe(df_cacoca)
    return df_cacoca

def initiate_cacoca_dataframe(df_posted: pd.DataFrame, posted_parent_variable: str) -> pd.DataFrame:
    variable_extraction = df_posted["variable"].apply(lambda v: variable_translation(v, posted_parent_variable))
    type_list = [d["Type"] for d in variable_extraction]
    component_list = [d["Component"] for d in variable_extraction]

    tech = df_posted["subtech"] if "subtech" in df_posted.columns else posted_parent_variable.split("|")[-1]
    # if additional differentiation exists, it is added to technology
    used_columns = ["subtech", "variable", "mode", "period", "value", "unit"]
    unused_columns = [col for col in df_posted.columns if col not in used_columns]
    if unused_columns:
        for col in unused_columns:
            tech += "|" + df_posted[col].astype(str)

    # translate Posted columns to CaCoCa columns
    df_cacoca = pd.DataFrame({
        "Technology": tech,
        "Mode": df_posted["mode"] if "mode" in df_posted.columns else None,
        "Type": type_list,
        "Component": component_list,
        "Subcomponent": None, # that's ok
        "Region": None, #that's ok
        "Period": df_posted["period"],
        "Usage": None, #that's ok
        "Value": df_posted["value"],
        "Uncertainty": None, #that's ok
        "Unit": df_posted["unit"], # ok
        "Non-unit conversion factor": None, # ok
        "Value and uncertainty comment": None, # ok
        "Source reference": f"Posted {posted_parent_variable}",
        "Source comment": None, #ok
    })

    return df_cacoca

def variable_translation(variable: str, parent_variable: str):
    """Translate Posted variable to CaCoCa Type and Component."""

    # remove parent variable prefix
    variable = variable.replace(f"{parent_variable}|", "")

    # split variable by "|"
    if "|" in variable:
        type_, component = variable.split("|", 1)
    else:
        type_ = variable
        component = variable

    component = TRANSLATION.get(component, component)

    if type_ == "CAPEX":
        type_ = "High CAPEX"

    elif type_ in POSTED_OPEX_COMPONENTS:
        component = type_ # variable and fixed opex will later be combined to additional opex
        type_ = "OPEX"
    
    elif type_ ==  "Input":
        if component in ENERGY_TYPES:
            type_ = "Energy demand"
        elif component in FEEDSTOCK_TYPES:
            type_ = "Feedstock demand"
    
    return {"Type": type_, "Component": component}
            
def aggregate_opex(df_cacoca: pd.DataFrame) -> pd.DataFrame:
    # TODO Warning: This assumes OPEX and CAPEX have compatible unit!
    is_opex_mask = df_cacoca['Component'].isin(POSTED_OPEX_COMPONENTS)
    df_opex = df_cacoca[is_opex_mask].copy()
    df_other = df_cacoca[~is_opex_mask]

    if not df_opex.empty:
        # sort (as OPEX Variable should be the master for other columns): 
        df_opex['Component'] = pd.Categorical(df_opex['Component'], categories=POSTED_OPEX_COMPONENTS, ordered=True)
        df_opex = df_opex.sort_values("Component")

        # aggregate OPEX components
        grouping_cols = [col for col in df_cacoca.columns if col not in ['Component', 'Value', 'Unit']]
        agg_logic = {'Value': 'sum', 'Unit': 'first'}
        aggregated_opex = df_opex.groupby(grouping_cols, as_index=False, dropna=False).agg(agg_logic)
        aggregated_opex['Component'] = 'Additional OPEX'

        # add aggregated OPEX back to CaCoCa dataframe
        df_cacoca = pd.concat([df_other, aggregated_opex], ignore_index=True)
    
    return df_cacoca

def filter_cacoca_dataframe(df_cacoca: pd.DataFrame) -> pd.DataFrame:
    all_allowed_components = ALLOWED_COMPONENTS + ENERGY_TYPES + FEEDSTOCK_TYPES + EMISSION_TYPES
    
    # Find rows in df_translated with new types/components
    mask_type = df_cacoca["Type"].isin(ALLOWED_TYPES)
    mask_component = df_cacoca["Component"].isin(all_allowed_components)
    mask_valid = mask_type & mask_component

    # Warn about dropped rows
    dropped_rows = df_cacoca[~mask_valid]
    unexpected_dropped = dropped_rows[~dropped_rows["Type"].isin(EXPECTED_REMOVAL_TYPES)]
    if not unexpected_dropped.empty:
        unique_dropped = unexpected_dropped[["Type", "Component"]].drop_duplicates()
        print("Warning: Unexpected unique Type/Component combinations are dropped:")
        print(unique_dropped)

    # Keep only valid rows
    df_cacoca = df_cacoca[mask_valid]

    return df_cacoca

def save_cacoca_dataframe(df_cacoca: pd.DataFrame, target_folder: Path, posted_filename: str):
    # ensure target folder exists
    target_folder.mkdir(parents=True, exist_ok=True)

    df_cacoca_path = target_folder / f"{posted_filename}.csv"
    df_cacoca.to_csv(df_cacoca_path, index=False)
