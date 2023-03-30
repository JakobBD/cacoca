import pandas as pd


def calc_strike_price(opex_and_em: pd.DataFrame, capex: pd.DataFrame, projects: pd.DataFrame):

    # NPV of OPEX difference and Emissions savings
    data = opex_and_em \
        .merge(
            projects.filter(['Project name', 'WACC', 'Time of investment', 'Project duration [a]']),
            how='left',
            on=['Project name']
        ) \
        .assign(
            **{'CumInterest': lambda df:
               (1.+df['WACC'])**(df['Period']-df['Time of investment'])}
        ) \
        .assign(
            **{'OPEX_NPV': lambda df:
               (df['CumInterest']-df['OPEX_diff']) / df['Project duration [a]']}
        ) \
        .assign(
            **{'Emissions_NPV': lambda df:
               (df['CumInterest']-df['Emissions_diff']) / df['Project duration [a]']}
        ) \
        .groupby(['Project name']) \
        .agg({'OPEX_NPV': 'sum', 'Emissions_NPV': 'sum'})

    # NPV(Cost_diff - SP*Emission_diff) = 0,
    # so  SP = NPV(Cost_diff)/NPV(Emission_diff)
    data = data \
        .merge(
            capex.filter(['Project name', 'Allocated CAPEX']),
            how='left',
            on=['Project name']
        ) \
        .assign(
            **{'Strike Price': lambda df:
               (-df['OPEX_NPV']+df['Allocated CAPEX']) / df['Emissions_NPV']}
        ) \
        .filter(['Project name', 'Strike Price'])

    return data


def calc_ccfd(opex_and_em: pd.DataFrame, capex: pd.DataFrame, projects: pd.DataFrame):

    pr_size = projects \
        .rename(columns={
            'Planned production volume p.a.': 'Size'
            # 'Project size/Production capacity [Mt/a] or GW': 'Size'
            }) \
        .filter(['Project name', 'Size'])

    opex_and_em = opex_and_em \
        .assign(
            **{"Effective CO2 Price": lambda df:
                (df["Emissions_diff"] - df["Free Allocations_diff"])
                / df["Emissions_diff"]
                * df["CO2 Price"]}
        )

    total_em_savings = opex_and_em \
        .groupby(['Project name']) \
        .agg({'Emissions_diff': 'sum'}) \
        .merge(
            pr_size,
            how='left',
            on=['Project name']
        ) \
        .assign(
            **{"Total Emissions savings": lambda df:
                df["Emissions_diff"] * df['Size']}
        ) \
        .filter(['Project name', "Total Emissions savings"])

    opex_and_em = opex_and_em \
        .assign(
            **{"Difference Price": lambda df:
                df["OPEX_diff"]
                / -df["Emissions_diff"]
                - df["Effective CO2 Price"]}
        )

    opex_and_em = opex_and_em \
        .merge(
            pr_size,
            how='left',
            on=['Project name']
        ) \
        .assign(
            **{"Payout": lambda df:
                df["Difference Price"] * -df["Emissions_diff"] * df["Size"]}
        )

    return opex_and_em, total_em_savings
