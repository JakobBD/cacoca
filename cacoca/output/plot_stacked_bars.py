import os
import plotly as pl
import pandas as pd
import numpy as np
from .plot_tools import show_and_save
from .plot_tools import display_name as dn


# The dict prescribes colors and ordering in the plot (from bottom to top):
colors = {
    # 1. FINANCIALS & EMISSIONS (Gray)
    'CO2 Cost': '#333333',              # Dark Grey
    'Effective CO2 Price': '#333333',   # Dark Grey
    'CAPEX annuity': '#666666',         # Mid-Grey
    'Additional OPEX': '#B3B3B3',       # Light Grey
    'OM Fixed': '#7F8C8D',              # Grey-green (TEAM)
    'OM Variable': '#95A5A6',           # Light grey-green (TEAM)

    # 2. FEEDSTOCK INPUTS
    'Iron Ore': '#A04000',
    'DRI-Pellets': "#C0703B",
    'Scrap Steel': "#68839E",

    # 3. ENERGY & CARBON INPUTS
    'Coking Coal': '#42032E',
    'Injection Coal': "#5E3360",
    'Coal': '#1A252F',                  # Generic coal (TEAM)
    'Oxygen': '#8B4513',                # Saddle brown (TEAM)
    'Naphta': '#E67E22',
    'Biomass': '#229954',
    'Biomethane': '#1ABC9C',            # Teal (TEAM)
    'Natural Gas': '#2980B9',
    'Hydrogen': '#00BCD4',
    'Electricity': '#F1C40F',
}

def plot_stacked_bars_multi(projects: pd.DataFrame, config: dict, project_names: list[str],
                      project_ref: str = None, cost_per: str = 'product',
                      emission_diff: bool = False, export_csv: bool = False, csv_dir: str = None):
    """
    Plot stacked bar charts for multiple projects and a single reference.
    
    Parameters:
    -----------
    projects : pd.DataFrame
        DataFrame containing project data
    config : dict
        Configuration dictionary
    project_names : list[str]
        List of project names to include in the plot
    project_ref : str
        Name of the project whose reference will be used as the common reference.
        If None, no reference is shown.
    cost_per : str
        'product' or 'em_savings' to determine the y-axis unit
    emission_diff : bool
        If True, plot co2 costs difference on the reference bar.
    export_csv : bool
        If True, export the data used for plotting to a CSV file.
    csv_dir : str
        Directory to save the CSV file if export_csv is True. If None, saves to current directory.
    """
    if cost_per == 'product':
        yunit = '€/t Produkt'
        co2pricename = 'CO2 Cost'
    elif cost_per == 'em_savings':
        yunit = '€/t CO2'
        co2pricename = 'Effective CO2 Price'
    else:
        raise Exception(f'Invalid parameter cost_per={cost_per}')

    # Filter for the specified projects
    all_projects = project_names.copy()
    if project_ref is not None and project_ref not in all_projects:
        all_projects.append(project_ref)

    projects = projects[projects['Project name'].isin(all_projects)].copy()

    years = [2025, 2030, 2035, 2040, 2045]
    years = np.intersect1d(years, projects['Period'].values)
    query_str = " | ".join(f"Period == {y}" for y in years)
    projects = projects.query(query_str).drop_duplicates()

    # Process CO2 price data
    if emission_diff:
        if project_ref is not None:
            projects = projects.assign(**{
                co2pricename + '_ref': lambda df: df['Effective CO2 Price'] * -df['Emissions_diff'],
                co2pricename: 0.})
        else:
            projects = projects.assign(**{co2pricename: 0.})
    else:
        if project_ref is not None:
            projects = projects.assign(**{
                co2pricename + '_ref': lambda df: df['CO2 Price'] * (df['Emissions_ref'] - df['Free Allocations_ref']),
                co2pricename: lambda df: df['CO2 Price'] * (df['Emissions'] - df['Free Allocations'])
            })
        else:
            projects = projects.assign(**{
                co2pricename: lambda df: df['CO2 Price'] * (df['Emissions'] - df['Free Allocations'])
            })

    variables = ['CAPEX annuity', 'Additional OPEX'] \
        + [cn for cn in projects.columns if str(cn).startswith('cost_')
           and not str(cn).endswith(('_variance', '_diff', '_ref', '_upper', '_lower'))]

    variables.append(co2pricename)

    if cost_per == 'em_savings':
        for vn in variables:
            projects[vn] /= -projects['Emissions_diff']
            if project_ref is not None:
                projects[vn + '_ref'] /= -projects['Emissions_diff']

    pmax = projects.max()
    if project_ref is not None:
        variables = [vn for vn in variables if max(pmax[vn], pmax[vn + '_ref']) > 1.e-6]
    else:
        variables = [vn for vn in variables if pmax[vn] > 1.e-6]

    width = 0.9
    fig = pl.graph_objs.Figure()

    # Export CSV if requested (for all projects, only columns that are plotted)
    if export_csv:
        # Only include _ref columns for the reference project, and normal columns for the others
        export_rows = []
        for pname in project_names:
            df_proj = projects[projects['Project name'] == pname]
            if not df_proj.empty:
                row = df_proj[['Project name', 'Period'] + variables].copy()
                export_rows.append(row)
        if project_ref is not None:
            df_ref = projects[projects['Project name'] == project_ref]
            if not df_ref.empty:
                ref_cols = ['Project name', 'Period'] + [vn + '_ref' for vn in variables]
                row = df_ref[ref_cols].copy()
                row['Project name'] = 'Referenz'
                # Rename _ref columns to match normal variable names for clarity
                row = row.rename(columns={vn + '_ref': vn for vn in variables})
                export_rows.append(row)
        if export_rows:
            export_df = pd.concat(export_rows, ignore_index=True)
            filename = f'stacked_bars_multi_{len(project_names)}_projects'
            if project_ref is not None:
                filename += f'_ref_{project_ref}'
            filename += '.csv'
            if csv_dir is not None:
                filename = os.path.join(csv_dir, filename)
            export_df.to_csv(filename, index=False)

    def yzero():
        return 0. * projects['CAPEX annuity']

    class Bar():
        def __init__(self, name, projects: pd.DataFrame, linecolor=None, reversed=False, base=None):
            self.name = name
            self.projects = projects
            self.vnames = set(self.projects.columns) - {'Period'}
            self.linecolor = linecolor
            self.dir = -1 if reversed else 1
            self.base = yzero() if base is None else base

    def add_placeholder(id: int):
        fig.add_bar(
            name='',
            x=[projects['Period'].to_list(), [' ' * id for _ in years]],
            y=yzero(),
            offsetgroup=id,
            base=0.,
            width=width,
            showlegend=False
        )

    add_placeholder(0)

    legend_vars = set()

    # First add the reference if specified
    offsetgroup = 0
    if project_ref is not None:
        ref_data = projects.query(f"`Project name` == '{project_ref}'")

        if not ref_data.empty:
            def yzero():
                return 0. * ref_data['CAPEX annuity']

            # Extract reference data
            ref_projects = ref_data \
                .filter(['Period'] + [vn + '_ref' for vn in variables]) \
                .rename(columns=lambda cn: str(cn).replace('cost_', '').replace('_ref', ''))

            # Create reference bar
            ref = Bar(name='Referenz',
                      projects=ref_projects,
                      linecolor='black')

            # Add reference bars
            for vn in ref.vnames:
                if vn not in colors:
                    raise Exception(f"Variable {vn} not found in colors dict")

            ref.pos_base = ref.base.copy()
            ref.neg_base = ref.base.copy()

            for vn, color in list(colors.items())[::ref.dir]:
                if vn not in ref.vnames:
                    continue

                values = ref.dir * ref.projects[vn]
                effective_base = ref.pos_base.where(values >= 0, ref.neg_base)

                fig.add_bar(
                    name=dn(vn),
                    x=[ref.projects['Period'].to_list(), [ref.name for _ in years]],
                    y=values,
                    base=effective_base,
                    marker_color=color,
                    width=width,
                    offsetgroup=offsetgroup,
                    showlegend=vn not in legend_vars
                )
                legend_vars.add(vn)
                ref.pos_base += values.clip(lower=0)
                ref.neg_base += values.clip(upper=0)

            if ref.linecolor:
                fig.add_scatter(
                    x=[ref.projects['Period'].to_list(), [ref.name for _ in years]],
                    y=ref.pos_base + ref.neg_base,
                    mode='lines+markers',
                    line=dict(color=ref.linecolor, width=2, dash='solid'),
                    showlegend=False,
                )

            offsetgroup += 1

    # Process each project
    for i, project_name in enumerate(project_names):
        # Don't skip the reference project - allow it to be plotted as a regular project too
        # The only reference data we're using is from project_ref

        project_data = projects.query(f"`Project name` == '{project_name}'")

        if project_data.empty:
            continue

        def yzero():
            return 0. * project_data['CAPEX annuity']

        # Extract project data
        projects_new = project_data \
            .filter(['Period'] + variables) \
            .rename(columns=lambda cn: str(cn).replace('cost_', ''))

        # Project name for display in the plot
        display_project_name = dn(project_name)

        # Create project bar
        new = Bar(name=f'{display_project_name}',
                  projects=projects_new,
                  linecolor='#D81B60')

        bars = [new]

        # Add bars for each project
        for bar in bars:
            for vn in bar.vnames:
                if vn not in colors:
                    raise Exception(f"Variable {vn} not found in colors dict")

            bar.pos_base = bar.base.copy()
            bar.neg_base = bar.base.copy()

            for vn, color in list(colors.items())[::bar.dir]:
                if vn not in bar.vnames:
                    continue

                # For multi-project, we'll add the project name to the bar name for clarity
                display_name = f"{dn(vn)} ({bar.name})" if vn in legend_vars else dn(vn)

                values = bar.dir * bar.projects[vn]
                effective_base = bar.pos_base.where(values >= 0, bar.neg_base)

                fig.add_bar(
                    name=display_name,
                    x=[bar.projects['Period'].to_list(), [bar.name for _ in years]],
                    y=values,
                    base=effective_base,
                    marker_color=color,
                    width=width,
                    offsetgroup=offsetgroup,
                    showlegend=vn not in legend_vars
                )
                legend_vars.add(vn)
                bar.pos_base += values.clip(lower=0)
                bar.neg_base += values.clip(upper=0)

            if bar.linecolor:
                fig.add_scatter(
                    x=[bar.projects['Period'].to_list(), [bar.name for _ in years]],
                    y=bar.pos_base + bar.neg_base,
                    mode='lines+markers',
                    line=dict(color=bar.linecolor, width=2, dash='solid'),
                    showlegend=False,
                )

        offsetgroup += 1

    add_placeholder(1)

    # Final layout updates
    fig.update_yaxes(title=yunit)
    project_names_display = ', '.join([dn(name) for name in project_names])
    ref_text = f" (Ref: {dn(project_ref)})" if project_ref is not None else ""
    fig.update_layout(
        legend_traceorder="reversed",
        title=f"Kostenvergleich: {project_names_display}{ref_text}",
        barmode="relative"
    )

    # Save and show the figure
    filename = f'stacked_bars_multi_{len(project_names)}_projects'
    if project_ref is not None:
        filename += f'_ref_{project_ref}'
    show_and_save(fig, config, filename)

def plot_stacked_bars(projects: pd.DataFrame, config: dict, project_name: str,
                      cost_per: str = 'product', emission_diff: bool = False, export_csv: bool = False, csv_dir: str = None):

    if cost_per == 'product':
        yunit = '€/t Produkt'
        co2pricename = 'CO2 Cost'
    elif cost_per == 'em_savings':
        yunit = '€/t CO2'
        co2pricename = 'Effective CO2 Price'
    else:
        raise Exception(f'Invalid parameter cost_per={cost_per}')

    projects = projects.query(f"`Project name` == '{project_name}'")

    years = [2025, 2030, 2035, 2040, 2045]
    years = np.intersect1d(years, projects['Period'].values)
    query_str = " | ".join(f"Period == {y}" for y in years)
    projects = projects.query(query_str).drop_duplicates()

    # Hack: Bring Effective CO2 Price in form to be added to reference, divided by emissions diff
    if emission_diff:
        # Emission cost: difference only plotted for reference
        projects = projects.assign(**{
            co2pricename + '_ref': lambda df: df['Effective CO2 Price'] * -df['Emissions_diff'],
            co2pricename: 0.})
    else:
        # Emission cost: plotted for both project and reference
        projects = projects.assign(**{
            co2pricename + '_ref': lambda df: df['CO2 Price'] * (df['Emissions_ref'] - df['Free Allocations_ref']),
            co2pricename: lambda df: df['CO2 Price'] * (df['Emissions'] - df['Free Allocations'])
        })

    variables = ['CAPEX annuity', 'Additional OPEX'] \
        + [cn for cn in projects.columns if str(cn).startswith('cost_')
           and not str(cn).endswith(('_variance', '_diff', '_ref', '_upper', '_lower'))]

    variables.append(co2pricename)

    if cost_per == 'em_savings':
        for vn in variables:
            projects[vn] /= -projects['Emissions_diff']
            projects[vn + '_ref'] /= -projects['Emissions_diff']

    pmax = projects.max()
    variables = [vn for vn in variables if max(pmax[vn], pmax[vn + '_ref']) > 1.e-6]

    width = 0.9

    # Export CSV if requested (only columns that are plotted)
    if export_csv:
        export_cols = ['Project name', 'Period'] + variables + [vn + '_ref' for vn in variables]
        export_df = projects[export_cols].copy()
        export_df = export_df.loc[:, (export_df != 0).any(axis=0)]
        filename = f'stacked_bars_{project_name}.csv'
        if csv_dir is not None:
            filename = os.path.join(csv_dir, filename)
        export_df.to_csv(filename, index=False)

    fig = pl.graph_objs.Figure()

    def yzero():
        return 0. * projects['CAPEX annuity']

    def add_placeholder(id: int):
        fig.add_bar(
            name='',
            x=[projects['Period'].to_list(), [' ' * id for _ in years]],
            y=yzero(),
            offsetgroup=id,
            base=0.,
            width=width,
            showlegend=False
        )

    add_placeholder(0)

    legend_vars = set()

    projects_new = projects \
        .filter(['Period'] + variables) \
        .rename(columns=lambda cn: str(cn).replace('cost_', ''))
    projects_ref = projects \
        .filter(['Period'] + [vn + '_ref' for vn in variables]) \
        .rename(columns=lambda cn: str(cn).replace('cost_', '').replace('_ref', ''))

    class Bar():
        def __init__(self, name, projects: pd.DataFrame, linecolor=None, reversed=False, base=None):
            self.name = name
            self.projects = projects
            self.vnames = set(self.projects.columns) - {'Period'}
            self.linecolor = linecolor
            self.dir = -1 if reversed else 1
            self.base = yzero() if base is None else base

    new = Bar(name='Vorhaben',
                projects=projects_new,
                linecolor='#D81B60')
    ref = Bar(name='Referenz',
                projects=projects_ref,
                linecolor='black')
    bars = [new, ref]

    for bar in bars:

        for vn in bar.vnames:
            if vn not in colors:
                raise Exception(f"Variable {vn} not found in colors dict")

        bar.pos_base = bar.base.copy()
        bar.neg_base = bar.base.copy()

        for vn, color in list(colors.items())[::bar.dir]:

            if vn not in bar.vnames:
                continue

            values = bar.dir * bar.projects[vn]
            effective_base = bar.pos_base.where(values >= 0, bar.neg_base)

            fig.add_bar(
                name=dn(vn),
                x=[bar.projects['Period'].to_list(), [bar.name for _ in years]],
                y=values,
                base=effective_base,
                marker_color=color,
                width=width,
                showlegend=vn not in legend_vars
            )
            legend_vars.add(vn)
            bar.pos_base += values.clip(lower=0)
            bar.neg_base += values.clip(upper=0)

        if bar.linecolor:
            fig.add_scatter(
                x=[bar.projects['Period'].to_list(), [bar.name for _ in years]],
                y=bar.pos_base + bar.neg_base,
                mode='lines+markers',
                line=dict(color=bar.linecolor, width=2, dash='solid'),
                showlegend=False,
            )

    add_placeholder(1)

    fig.update_yaxes(title=yunit)
    fig.update_layout(legend_traceorder="reversed",
                      title=f"Kostenvergleich {dn(project_name)}")
    fig.update_layout(barmode="relative")
    show_and_save(fig, config, 'stacked_bars_' + project_name)
