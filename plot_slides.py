# %%
from main import run


config, projects_uf, cost_and_em_actual = run(config_filepath='config/config_UF.yml')


# %% SECTOR COMPARISON  ============================================================================

from src.output.plot_project_cost_time_curves import plot_project_cost_time_curves
from main import run


if 'cost_and_em_actual' not in globals():
    config, projects_uf, cost_and_em_actual = run(config_filepath='config/config_UF.yml')

project_names = [
    'DUMMY INSERT PROJECT NAMES']
plot_project_cost_time_curves(cost_and_em_actual, print_name='compare_sectors',
                              **{'Project name': project_names})


# %% ALL PROJECTS  =================================================================================

import copy
from src.setup.read_input import read_config
from main import run
from src.output.plot_project_cost_time_curves import plot_project_cost_time_curves


if 'config' not in globals():
    config = read_config(filepath='config/config_UF.yml')

config_all = copy.deepcopy(config)
config_all['projects_file'] = 'config/Projects_ALL.xlsx'
config_all, projects_all, cost_and_em_all = run(config=config_all)

plot_project_cost_time_curves(cost_and_em_all, print_name='all_projects', color_by='Industry')


# %% STEEL PROJECT COMPARISON  =====================================================================

from src.output.plot_project_cost_time_curves import plot_project_cost_time_curves
from main import run


if 'cost_and_em_actual' not in globals():
    from main import run
    config, projects_uf, cost_and_em_actual = run(config_filepath='config/config_UF.yml')

project_names = [
    'DUMMY INSERT PROJECT NAMES']
plot_project_cost_time_curves(cost_and_em_actual, print_name='steel_IPCEI',
                              **{'Project name': project_names})


# %% STACKED BARS  =================================================================================

from src.output.plot_project_cost_time_curves import plot_project_cost_time_curves
from src.output.plot_stacked_bars import plot_stacked_bars
from main import run


if 'cost_and_em_actual' not in globals():
    config, projects_uf, cost_and_em_actual = run(config_filepath='config/config_UF.yml')

project_names = [
    'DUMMY INSERT PROJECT NAMES']
for project_name in project_names:
    plot_stacked_bars(cost_and_em_actual, project_name=project_name, cost_per='product')
    # plot_stacked_bars(cost_and_em_actual, project_name=project_name, cost_per='em_savings',
    #                   is_diff=True)


# %% PRICE SCENARIOS  ==============================================================================

from src.output.plot_price_scenarios import plot_price_scenarios
from main import run


if 'cost_and_em_actual' not in globals():
    config, projects_uf, cost_and_em_actual = run(config_filepath='config/config_UF.yml')

project_names = [
    'DUMMY INSERT PROJECT NAMES']
plot_price_scenarios(config, projects_uf, project_names)

# %% INFLUENCE OF H2 SHARE  ========================================================================

from src.output.plot_project_cost_time_curves import plot_project_cost_time_curves
from main import run


if 'cost_and_em_actual' not in globals():
    config, projects_uf, cost_and_em_actual = run(config_filepath='config/config_UF.yml')

project_names = [
    'DUMMY INSERT PROJECT NAMES']
plot_project_cost_time_curves(cost_and_em_actual, print_name='h2share_influence',
                              **{'Project name': project_names})


# %% INFLUENCE OF UNCERTAINTIES  ===================================================================

import copy
from main import run
from src.setup.read_input import read_config
from src.output.plot_project_cost_time_curves import plot_project_cost_time_curves


if 'config' not in globals():
    config = read_config(filepath='config/config_UF.yml')

project_names_dict = {
    'lowh2': 'DUMMY INSERT PROJECT NAMES'
}

sens_scenarios = {
    "all": {
        "Hydrogen": 0.1,
        "Natural Gas": 0.1,
        "Electricity": 0.1,
        "CO2": 0.2
    },
    "h2": {
        "Hydrogen": 0.1
    },
    "ng": {
        "Natural Gas": 0.1
    },
    "elec": {
        "Electricity": 0.1
    }
}

for scen_name, sens_dict in sens_scenarios.items():

    config_sens = copy.deepcopy(config)
    config_sens['relative_standard_deviation'] = {}
    for component, rel_std in sens_dict.items():
        config_sens['relative_standard_deviation'][component] = rel_std

    _, projects_sens, cost_and_em_sens = run(config=config_sens)

    for h2name, project_name in project_names_dict.items():
        plot_project_cost_time_curves(cost_and_em_sens,
                                      print_name=f'sensitivity_{scen_name}_{h2name}',
                                      **{'Project name': [project_name]})


# %%
