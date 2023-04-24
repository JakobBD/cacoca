from src.setup.setup import Setup
from src.calc.calc_cost_and_emissions import calc_cost_and_emissions
from src.calc.calc_derived_quantities import calc_derived_quantities
from src.calc.calc_auction_quantities import calc_auction_quantities
from src.calc.auction import set_projects_ar, auction
# from tools.sensitivities import
from src.tools.tools import log


def run(config_filepath: str = None, config: dict = None):

    setup = Setup(config_filepath, config)

    mode = setup.config['mode']
    if mode == 'auction':
        run_auction(setup)
        return
    elif mode == 'analyze_cost':
        cost_and_em = run_analyze(setup)
        return setup.config, setup.projects_all, cost_and_em


def run_auction(setup: Setup):

    all_chosen_projects = []

    for config_ar_specific in setup.config['auction_rounds']:

        config_ar = setup.config['auction_round_default'] | config_ar_specific

        log(f"Enter auction round {config_ar['name']}...")

        set_projects_ar(setup, all_chosen_projects, config_ar)

        setup.select_scenario_data('scenarios_bidding')
        setup.select_h2share(auction_year=config_ar['year'])

        cost_and_em_bidding = calc_cost_and_emissions(setup)
        yearly = calc_derived_quantities(cost_and_em_bidding, setup)
        yearly, aggregate = calc_auction_quantities(yearly, setup, config_ar)

        chosen_projects = auction(aggregate, setup, config_ar)
        all_chosen_projects += chosen_projects

        # TODO:
        # adjust size by Auslastungsfaktor where necessary
        # calc_payout(chosen_projects)

    return all_chosen_projects


def run_analyze(setup: Setup):

    setup.select_scenario_data(scenarios='scenarios_actual')
    setup.select_h2share()

    cost_and_em = calc_cost_and_emissions(setup, keep_components=True)
    yearly = calc_derived_quantities(cost_and_em, setup)

    return yearly


if __name__ == '__main__':
    config_filepath = 'config/config_all.yml'
    run(config_filepath)
