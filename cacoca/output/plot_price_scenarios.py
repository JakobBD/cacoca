import plotly as pl
import pandas as pd
from ..setup.read_input import read_raw_scenario_data
from ..setup.setup import Setup
from ..setup.select_scenario_data import years_to_rows
from .plot_project_cost_time_curves import plot_project
from .plot_tools import add_color, show_and_save, set_yrange_min_zero
from .plot_tools import display_name as dn
# from tools.sensitivities import sensitivity_to_bounds


def plot_price_scenarios(setup: Setup, do_emphasize: bool = True):

    scen_dir_path = setup.config['scenarios_dir']

    prices_raw, _, _, _ = read_raw_scenario_data(dirpath=scen_dir_path)

    prices = years_to_rows(prices_raw, year_name="Period", value_name="Price")
    prices = prices.drop(columns='Source Reference')

    plot_scenarios(prices, setup.config, 'prices', do_emphasize)


def plot_h2share_scenarios(setup: Setup, project_names: list, share_kind: str,
                           print_prefix: str = "", do_emphasize: bool = True):

    scen_dir_path = setup.config['scenarios_dir']

    _, _, h2share_raw, _ = read_raw_scenario_data(dirpath=scen_dir_path)

    # Hack to make it fit in price plotting scheme below
    h2share = years_to_rows(h2share_raw, year_name="Period", value_name="Price")

    h2share_scens = []
    for project_name in project_names:
        h2share_scen = setup.projects_all \
            .query(f"`Project name` == '{project_name}'")["H2 Share Scenario"] \
            .values[0]
        h2share_scens.append(h2share_scen)

    h2share["Component"] = share_kind
    h2share["Unit"] = share_kind

    plot_scenarios(h2share, setup.config, print_prefix, do_emphasize, h2share_scens)


def plot_scenarios(prices: pd.DataFrame, config: dict, print_prefix: str,
                   do_emphasize: bool = True, highlighted_scenarios: list = None):

    print_other = True

    for component_name, cdf in prices.groupby('Component'):

        fig = pl.graph_objs.Figure()

        cdf = add_color(
            cdf,
            by_column='Scenario'
        )

        for scenario_name, sdf in cdf.groupby('Scenario'):
            color = sdf['color'].values[0]
            legend_name = scenario_name

            if not do_emphasize:
                emphasize = 'all_equal'
            else:
                if highlighted_scenarios:
                    is_emphasized = scenario_name in highlighted_scenarios
                else:
                    is_emphasized = \
                        config['scenarios_actual']['prices'].get(component_name) == scenario_name
                emphasize = 'main' if is_emphasized else 'other'

            if emphasize == 'other' and not print_other:
                continue

            plot_project(fig,
                         sdf,
                         vname='Price',
                         legend_name=legend_name,
                         hovername=scenario_name,
                         color=color,
                         emphasize=emphasize)

        fig.update_layout(legend=dict(title='Szenario'),
                          title=f"{dn(print_prefix)} {dn(component_name)}")
        # fig.update_xaxes(title='Jahr')

        set_yrange_min_zero(fig)
        fig.update_yaxes(title=dn(sdf['Unit'].values[0]))

        show_and_save(fig, config, print_prefix + "_" + component_name)
