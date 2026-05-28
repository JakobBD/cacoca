import pandas as pd

from cacoca.setup.read_input import read_raw_scenario_data
from cacoca.setup.select_scenario_data import select_prices


# Mapping from CaCoCa price component names to TEAM variable names and units.
# Only components listed here are passed to TEAM; others are silently skipped.
CACOCA_TO_TEAM_PRICE_MAP = {
    "CO2":            ("GHG Price",             "EUR_2024/t CO2eq"),
    "Electricity":    ("Price|Electricity",      "EUR_2024/MWh"),
    "Hydrogen":       ("Price|Hydrogen",         "EUR_2024/kg_H2"),
    "Natural Gas":    ("Price|Natural Gas",      "EUR_2024/MWh_NG_LHV"),
    "Coking Coal":    ("Price|Coking Coal",      "EUR_2024/MWh_coal_LHV"),
    "Injection Coal": ("Price|Injection Coal",   "EUR_2024/MWh_coal_LHV"),
    "Iron Ore":       ("Price|Iron Ore",         "EUR_2024/t"),
    "DRI-Pellets":    ("Price|DRI-Pellets",      "EUR_2024/t"),
    "Scrap Steel":    ("Price|Scrap Steel",      "EUR_2024/t"),
    "Naphta":         ("Price|Naphta",           "EUR_2024/MWh"),
    "Biomass":        ("Price|Biomass",          "EUR_2024/MWh"),
}

# Mapping from TEAM component names (after varsplit) to CaCoCa column names.
# Must cover every component that appears in the TEAM output; unknown names raise ValueError.
COMPONENT_MAP = {
    # Capital / OPEX (TEAM uses "Capital" for what CaCoCa calls "CAPEX annuity")
    "Capital":                  "CAPEX annuity",
    "CAPEX annuity":            "CAPEX annuity",
    "Additional OPEX":          "Additional OPEX",
    "OM Fixed":                 "OM Fixed",
    "OM Variable":              "OM Variable",
    # Energy and feedstock inputs
    "Input Cost|Electricity":   "Electricity",
    "Input Cost|Natural Gas":   "Natural Gas",
    "Input Cost|Hydrogen":      "Hydrogen",
    "Input Cost|Iron Ore":      "Iron Ore",
    "Input Cost|Coking Coal":   "Coking Coal",
    "Input Cost|Injection Coal":"Injection Coal",
    "Input Cost|Scrap Steel":   "Scrap Steel",
    "Input Cost|DRI-Pellets":   "DRI-Pellets",
    "Input Cost|Coal":          "Coal",
    "Input Cost|Biomethane":    "Biomethane",
    "Input Cost|Naphta":        "Naphta",
    "Input Cost|Biomass":       "Biomass",
}


def prices_from_config(config: dict, include_ghg: bool = True) -> pd.DataFrame:
    """
    Load CaCoCa price scenarios selected by config['scenarios_actual'] and convert
    to the TEAM assumptions format (columns: variable, value, unit, period).

    Parameters
    ----------
    config : dict
        CaCoCa config dict (must have 'scenarios_dir' and 'scenarios_actual').
    include_ghg : bool
        If True (default), include the GHG Price (CO2 price). Set to False when
        passing assumptions to TEAM's perform_multi — TEAM would otherwise embed
        GHG costs as GHG Pricing|... components inside LCOX, which would
        double-count CO2 cost against CaCoCa's own CO2 cost computation.

    Components not in CACOCA_TO_TEAM_PRICE_MAP are silently ignored.
    """
    prices_raw, _, _, _ = read_raw_scenario_data(dirpath=config["scenarios_dir"])
    prices = select_prices(prices_raw, config["scenarios_actual"])
    prices = prices.dropna(subset=["Price"])

    rows = []
    for _, row in prices.iterrows():
        component = row["Component"]
        if component not in CACOCA_TO_TEAM_PRICE_MAP:
            continue
        team_variable, team_unit = CACOCA_TO_TEAM_PRICE_MAP[component]
        if not include_ghg and team_variable == "GHG Price":
            continue
        rows.append({
            "variable": team_variable,
            "value":    row["Price"],
            "unit":     team_unit,
            "period":   int(row["Period"]),
        })

    return pd.DataFrame(rows)


def team_to_cacoca(
    df_calc: pd.DataFrame,
    assumptions: pd.DataFrame,
    component_map: dict = None,
) -> pd.DataFrame:
    """
    Convert TEAM calculation output to the cost_and_em DataFrame format expected by
    CaCoCa's plot_stacked_bars / plot_stacked_bars_multi.

    Parameters
    ----------
    df_calc : pd.DataFrame
        TEAM output after varsplit / varcombine / unit_to.
        Must have columns: 'variable', 'route', 'period', 'component', 'value'.
        LCOX values must be in EUR_2024/t (product), GHGI in t CO2eq/t (product).
    assumptions : pd.DataFrame
        TEAM assumptions DataFrame as returned by prices_from_config, used to
        extract the GHG Price (CO2 price) per period.
    component_map : dict, optional
        Override for the module-level COMPONENT_MAP.

    Returns
    -------
    pd.DataFrame
        Columns: 'Project name', 'Period', 'CAPEX annuity', 'Additional OPEX',
        'cost_<X>' for each energy/feedstock component, 'Emissions',
        'Free Allocations', 'CO2 Price'.
    """
    if component_map is None:
        component_map = COMPONENT_MAP

    # --- LCOX components ---
    df_lcox = df_calc.query("variable == 'LCOX'").copy()

    df_lcox["component_mapped"] = df_lcox["component"].map(component_map)
    unknown = df_lcox.loc[df_lcox["component_mapped"].isna(), "component"].unique()
    if len(unknown) > 0:
        raise ValueError(
            f"TEAM components not found in component_map: {sorted(unknown)}\n"
            "Add them to COMPONENT_MAP in run_posted.py and to the colors dict in "
            "cacoca/output/plot_stacked_bars.py."
        )

    # Sum over processes: group by route / period / component
    df_grouped = (
        df_lcox
        .groupby(["route", "period", "component_mapped"], as_index=False)["value"]
        .sum()
    )

    # Separate structural columns (CAPEX annuity, Additional OPEX) from cost_ columns
    _structural = ["CAPEX annuity", "Additional OPEX"]
    is_structural = df_grouped["component_mapped"].isin(_structural)

    df_cost = df_grouped[~is_structural]
    df_structural = df_grouped[is_structural]

    # Pivot cost components → cost_<X> columns
    if not df_cost.empty:
        cost_pivot = (
            df_cost
            .pivot_table(
                index=["route", "period"],
                columns="component_mapped",
                values="value",
                fill_value=0.0,
            )
            .infer_objects(copy=False)
            .reset_index()
        )
        cost_pivot.columns.name = None
        cost_cols = [c for c in cost_pivot.columns if c not in ("route", "period")]
        cost_pivot = cost_pivot.rename(columns={c: f"cost_{c}" for c in cost_cols})
    else:
        cost_pivot = df_grouped[["route", "period"]].drop_duplicates()

    # Pivot structural columns → CAPEX annuity, Additional OPEX columns
    if not df_structural.empty:
        structural_pivot = (
            df_structural
            .pivot_table(
                index=["route", "period"],
                columns="component_mapped",
                values="value",
                fill_value=0.0,
            )
            .infer_objects(copy=False)
            .reset_index()
        )
        structural_pivot.columns.name = None
        for col in _structural:
            if col not in structural_pivot.columns:
                structural_pivot[col] = 0.0
    else:
        structural_pivot = (
            df_grouped[["route", "period"]].drop_duplicates().copy()
        )
        for col in _structural:
            structural_pivot[col] = 0.0

    # --- GHGI → Emissions ---
    df_ghgi = df_calc.query("variable == 'GHGI'")
    if not df_ghgi.empty:
        emissions = (
            df_ghgi
            .groupby(["route", "period"], as_index=False)["value"]
            .sum()
            .rename(columns={"value": "Emissions"})
        )
    else:
        emissions = (
            df_grouped[["route", "period"]].drop_duplicates().copy()
        )
        emissions["Emissions"] = 0.0

    # --- CO2 price per period ---
    co2_price = (
        assumptions
        .query("variable == 'GHG Price'")
        [["period", "value"]]
        .rename(columns={"value": "CO2 Price", "period": "Period"})
        .drop_duplicates(subset=["Period"])
    )

    # --- Merge everything ---
    result = (
        cost_pivot
        .merge(structural_pivot, on=["route", "period"], how="left")
        .merge(emissions, on=["route", "period"], how="left")
        .rename(columns={"route": "Project name", "period": "Period"})
        .merge(co2_price, on="Period", how="left")
    )

    result["Free Allocations"] = 0.0

    # Fill any remaining NaN cost columns with 0
    cost_cols = [c for c in result.columns if c.startswith("cost_")]
    result[cost_cols] = result[cost_cols].fillna(0.0)

    return result
