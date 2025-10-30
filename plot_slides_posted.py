
# %% STACKED BARS  =================================================================================

from cacoca.output.plot_stacked_bars import plot_stacked_bars
from cacoca.run import run
from cacoca.output.plot_tools import change_output_subdir_by_filename


if 'cost_and_em_actual' not in globals():
    setup, cost_and_em_actual = run(config_filepath='config/config_posted.yml')
    change_output_subdir_by_filename(setup.config, __file__)

project_names = [
    'Zement Posted'
]
for project_name in project_names:
    plot_stacked_bars(cost_and_em_actual, setup.config, project_name=project_name,
                      cost_per='product')
    # plot_stacked_bars(cost_and_em_actual, config, project_name=project_name,
    #                   cost_per='em_savings', is_diff=True)

