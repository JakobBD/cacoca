from src.input.read_config import read_config
from src.input.read_projects import read_projects
from src.input.read_techdata import read_techdata
from src.input.read_scenario_data import read_scenario_data
from src.calc_costs.calc_capex import calc_capex
from src.calc_costs.calc_opex_and_emissions import calc_opex_and_emissions
from src.calc_costs.calc_ccfd import calc_ccfd, calc_strike_price


# import sys
# config_filepath = sys.argv[1]
# config_filepath = 'config/config_all.yml'
config_filepath = 'config/config.yml'

config = read_config(config_filepath)

projects = read_projects(
    config['projects_file'],
    config['default_wacc']
)

techdata, reference_tech = read_techdata(
    config['techdata_dir'],
    config['techdata_files']
)

# techdata = expand_by_years(techdata,
#                            config['years'])

opex_and_em_actual, opex_and_em_bidding, h2share = read_scenario_data(
    config['scenarios_dir'],
    config['scenarios_actual'],
    config['scenarios_bidding'],
    projects
)

capex = calc_capex(projects, techdata)

opex_and_em_actual = calc_opex_and_emissions(projects, techdata, reference_tech,
                                             opex_and_em_actual, h2share, config)
opex_and_em_bidding = calc_opex_and_emissions(projects, techdata, reference_tech,
                                              opex_and_em_bidding, h2share, config)

strike_price = calc_strike_price(opex_and_em_bidding, capex, projects)


opex_and_em_actual, total_em_savings_actual = calc_ccfd(opex_and_em_actual, capex, projects)
opex_and_em_bidding, total_em_savings_bidding = calc_ccfd(opex_and_em_bidding, capex, projects)

# calc_lcop() # sum(opex)/duration + capex / auslastungsfaktor
# calc_abatement_cost() # npv( lcop_t - lcop_ref ) / npv( e_t - e_ref ), all per t of product
# calc_strike_price()
# calc_eff_co2_price()
# calc_total_emission_saving()
# calc_cap()

print()
