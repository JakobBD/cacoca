import pandas as pd
import numpy as np
import numpy_financial as npf
from ..setup.setup import Setup
from ..tools.common_merges import add_tech_and_industry


def calc_cost_and_emissions(setup: Setup, keep_components: bool = False):

    # three different operation modes
    data_old, data_new, data_ref = split_technology_names(setup)

    data_new = calc_single_opmode(data_new, setup, keep_components)
    data_old = calc_single_opmode(data_old, setup, keep_components)
    data_ref = calc_single_opmode(data_ref, setup, keep_components)

    # data old and new are combined vial fuel mix
    data_all, variables = merge_operation_modes(data_old, data_new, setup.h2share)

    # cost incl capex is determined by new technology, so its calculated only here
    data_all = calc_cost_wit_capex(data_all)
    data_ref = calc_cost_wit_capex(data_ref)

    data_all = merge_with_reference(data_all, data_ref, variables)

    data_all = add_co2_price(data_all, setup.prices)

    return data_all


def split_technology_names(setup: Setup):

    data_all = add_tech_and_industry(
        setup.projects_current.filter(['Project name', 'Technology']),
        setup
    ) \
        .merge(
            setup.reference_tech,
            how='left',
            on="Technology"
    )

    # used for reference cost
    data_ref = data_all \
        .drop(columns=["Industry", "Technology"]) \
        .rename(columns={"Reference Technology": "Technology"})

    # generate "new" and "old" cost to blend via fuel mix/h2share
    # for steel_dri, the new Technology name gets '-H2' added, while the old
    # Technology is the new (not the Reference!) with -NG added.
    data_all.loc[data_all['Industry'] == 'steel_dri', 'Reference Technology'] \
        = data_all.loc[data_all['Industry'] == 'steel_dri', 'Technology'] + "-NG"
    data_all.loc[data_all['Industry'] == 'steel_dri', 'Technology'] += "-H2"

    data_old = data_all \
        .drop(columns=["Industry", "Technology"]) \
        .rename(columns={"Reference Technology": "Technology"})
    data_new = data_all \
        .drop(columns=["Industry", "Reference Technology"])

    return data_old, data_new, data_ref


def calc_single_opmode(data_in: pd.DataFrame, setup: Setup, keep_components: bool = False):
    """
    Calc cost and emissions for one set of specific energy demands
    """

    data_in = calc_capex(data_in, setup)

    yearly_data = expand_by_years(data_in, setup)

    yearly_data = calc_cost_single_opmode(yearly_data, setup, keep_components)

    yearly_data = calc_emissions_single_opmode(yearly_data, setup)

    return yearly_data


def calc_capex(data_in: pd.DataFrame, setup: Setup):

    needed_project_info = [
        'Share of high CAPEX',
        'WACC',
        'Technical lifetime',
        'Project size/Production capacity [Mt/a] or GW',
        'Planned production volume p.a.'
    ]

    data_in = data_in \
        .merge(
            setup.projects_current.filter(['Project name'] + needed_project_info),
            how='left',
            on=['Project name']
        )

    def single_tech_param(name: str):
        return setup.techdata.query(f"Type=='{name}'") \
            .filter(["Technology", "Value"]) \
            .rename(columns={"Value": name})

    data_in = data_in \
        .merge(single_tech_param('High CAPEX'), how='left', on='Technology') \
        .merge(single_tech_param('Low CAPEX'), how='left', on='Technology') \
        .assign(
            **{'CAPEX total': lambda df:
                df['Share of high CAPEX'] * df['High CAPEX'].fillna(0.).astype(float)
                + (1. - df['Share of high CAPEX']) * df['Low CAPEX'].fillna(0.).astype(float)}
        ) \
        .drop(columns=['High CAPEX', 'Low CAPEX'])

    data_in = data_in \
        .assign(
            **{"CAPEX annuity": lambda df:
                # NB: npf.pmt already divides by lifetime to get cost per t of product
                npf.pmt(df['WACC'], df['Technical lifetime'], -df['CAPEX total'])
                * df['Project size/Production capacity [Mt/a] or GW']
                / df['Planned production volume p.a.']}
        ) \
        .drop(columns=needed_project_info)

    # projects = projects \
    #     .assign(
    #         **{'Invest Volume (M EUR)': lambda df:
    #             df['CAPEX'] * df['Project size/Production capacity [Mt/a] or GW']}
    #     )

    return data_in


def expand_by_years(data_in: pd.DataFrame, setup: Setup):

    # expand projects by calendar years of operation
    data_in = data_in \
        .merge(
            setup.projects_current.filter(['Project name', 'Time of investment']),
            how='left',
            on=['Project name']
        ) \
        .merge(
            setup.all_years,
            how='cross'
        )
    yearly_data = data_in \
        .query("Period >= `Time of investment` &"
               + f" Period <= `Time of investment` + {setup.config['ccfd_duration']}") \
        .drop(columns=['Time of investment'])
    return yearly_data


def calc_cost_single_opmode(yearly_data: pd.DataFrame, setup: Setup, keep_components: bool = False):
    """
    Calc yearly cost for one set of specific energy demands
    """

    columns_keep = np.setdiff1d(yearly_data.columns, ['Project name', 'Period'])

    # expand by unique list of all occuring components of energy demand
    materials_in = setup.techdata \
        .query("Type=='Energy demand' | Type=='Feedstock demand'") \
        .filter(["Component"]) \
        .drop_duplicates()
    yearly_data = yearly_data.merge(materials_in, how='cross')

    # get specific energy demand from techdata, accessed by technology and component
    # This is done after expanding by year to later enable time-dependent eneryg demands
    yearly_data = yearly_data \
        .merge(
            setup.techdata
            .query("Type=='Energy demand' | Type=='Feedstock demand'")
            .filter(["Technology", "Type", "Component", "Value"]),
            how='left',
            on=['Technology', 'Component']
        ) \
        .rename(columns={"Value": "Material demand"})
    yearly_data["Material demand"] = yearly_data["Material demand"].fillna(0.0)

    # add prices to df and calculate cost = en.demand * price
    yearly_data = yearly_data \
        .merge(
            setup.prices.drop(columns=["Source Reference", "Unit"]),
            how='left',
            on=['Component', 'Period']
        ) \
        .assign(**{'cost': lambda df: df['Material demand'] * df['Price']})

    if keep_components:
        component_cost = yearly_data \
            .pivot_table(values='cost', index=['Project name', 'Period'], columns='Component') \
            .rename(columns=lambda cn: 'cost_' + cn) \
            .reset_index()

    yearly_data = yearly_data \
        .groupby(['Project name', 'Period', 'Type'], as_index=False) \
        .agg({'cost': 'sum'} | {cname: 'first' for cname in columns_keep})

    energy_cost = yearly_data \
        .query("Type=='Energy demand'") \
        .filter(['Project name', 'Period', 'cost']) \
        .rename(columns={'cost': 'Energy cost'})

    yearly_data = yearly_data \
        .groupby(['Project name', 'Period'], as_index=False) \
        .agg({'cost': 'sum'} | {cname: 'first' for cname in columns_keep}) \
        .merge(energy_cost, how='left', on=['Project name', 'Period'])

    if keep_components:
        yearly_data = yearly_data \
            .merge(
                component_cost,
                how='left',
                on=['Project name', 'Period']
            )

    # add additional OPEX and CAPEX
    yearly_data = yearly_data \
        .merge(
            setup.techdata
            .query("Type=='OPEX'")
            .filter(["Technology", "Value"]),
            how='left',
            on=['Technology']
        ) \
        .rename(columns={"Value": "Additional OPEX"})
    yearly_data["Additional OPEX"] = yearly_data["Additional OPEX"].fillna(0.0)
    return yearly_data


def calc_cost_wit_capex(yearly_data: pd.DataFrame):

    yearly_data = yearly_data \
        .assign(**{'cost': lambda df: df['cost'] + df['Additional OPEX'] + df['CAPEX annuity']})

    return yearly_data


def calc_emissions_single_opmode(yearly_data: pd.DataFrame, setup: Setup):
    """
    Calc emission prices for one set of specific energy demands
    """

    # Add emissions to df
    yearly_data = yearly_data \
        .merge(
            setup.techdata
            .query("Type=='Emissions' & Component == 'CO2'")
            .filter(["Technology", "Value"]),
            how='left',
            on=['Technology']
        ) \
        .rename(columns={"Value": "Emissions"})

    # add free allocations to df
    yearly_data = yearly_data \
        .merge(
            setup.free_allocations
            .filter(["Technology", "Period", "Free Allocations"]),
            how='left',
            on=['Technology', 'Period']
        )
    yearly_data["Free Allocations"] = pd.to_numeric(
        yearly_data["Free Allocations"], errors='coerce'
    ).fillna(0.0)

    return yearly_data


def merge_operation_modes(data_old: pd.DataFrame, data_new: pd.DataFrame, h2share: pd.DataFrame):

    variables = np.setdiff1d(
        np.intersect1d(data_old.columns, data_new.columns),
        ['Project name', 'Period', 'Technology']
    )

    # merge old and new dataframes
    # (CAPEX is not blended, but 100 % new technology, therefore dropped in old df)
    data_all = data_old \
        .drop(columns=['CAPEX annuity']) \
        .merge(
            data_new.drop(columns=['Technology']),
            how='left',
            on=['Project name', 'Period']
        ) \
        .merge(
            h2share,
            how='left',
            on=['Project name', 'Period']
        )

    # blend cost and emissions of old and new operation mode to overall cost
    for vname in variables:
        if vname == 'CAPEX annuity':
            continue
        data_all = data_all \
            .assign(**{vname: lambda df:
                       (1. - df['H2 Share']) * df[vname + '_x']
                       + df['H2 Share'] * df[vname + '_y']})
        data_all = data_all.drop(columns=[vname + '_x', vname + '_y'])

    data_all = data_all \
        .drop(columns=['H2 Share'])

    return data_all, variables


def merge_with_reference(data_all: pd.DataFrame, data_ref: pd.DataFrame, variables: list):

    # add '_ref' to reference varable names
    data_ref = data_ref \
        .rename(columns={v: v + '_ref' for v in variables}) \
        .drop(columns=['Technology'])
    # merge and calculate difference for all variables in input list
    data_all = data_all \
        .merge(
            data_ref,
            how='left',
            on=['Project name', 'Period']
        )
    for vname in variables:
        data_all = data_all \
            .assign(**{vname + '_diff': lambda df: df[vname] - df[vname + '_ref']})

    return data_all


def add_co2_price(yearly_data: pd.DataFrame, prices: pd.DataFrame):
    co2prices = prices \
        .query("Component == 'CO2'") \
        .filter(["Period", "Price"]) \
        .rename(columns={"Price": "CO2 Price"})
    yearly_data = yearly_data \
        .merge(
            co2prices,
            how='left',
            on=['Period']
        )
    return yearly_data
