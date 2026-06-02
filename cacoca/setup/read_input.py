import yaml
import os
import pandas as pd


def read_config(filepath: str):
    with open(filepath, 'r') as f:
        file_content = f.read()
    config = yaml.load(file_content, Loader=yaml.CLoader)
    return config


def read_projects(config: dict):
    projects = pd.read_csv(config['projects_file'])
    # projects = pd.read_excel(filepath, sheet_name='Projects')
    projects = projects.query("Active == 1")
    projects = projects.fillna({'WACC': config['default_wacc']})
    if config['do_overwrite_project_start_year']:
        projects['Time of investment'] = config['project_start_year_overwrite']
    if not projects['Project name'].is_unique:
        raise Exception('Duplicate project names are prohibited.')
    return projects


def read_techdata(dir_path: str, filenames_base: list):
    techdata = [
        pd.read_csv(
            os.path.join(dir_path, fnb + '.csv')
        ) for fnb in filenames_base
    ]
    non_empty_techdata = []
    for df, fnb in zip(techdata, filenames_base):
        if df.dropna(how='all').empty:
            continue
        df.insert(0, "Industry", fnb, True)
        non_empty_techdata.append(df)
    techdata = pd.concat(non_empty_techdata, ignore_index=True)

    reference_tech = pd.read_csv(
        os.path.join(dir_path, 'technology_reference_mapping.csv')
    )

    return techdata, reference_tech


def read_raw_scenario_data(dirpath: str):
    co2prices = pd.read_csv(os.path.join(dirpath, 'prices_co2.csv'))
    co2prices.insert(0, 'Component', 'CO2', True)
    fuel_prices = pd.read_csv(os.path.join(dirpath, 'prices_fuels.csv'))
    prices = pd.concat([co2prices, fuel_prices])
    h2share = pd.read_csv(os.path.join(dirpath, 'h2share.csv'))
    free_allocations = pd.read_csv(os.path.join(dirpath, 'free_allocations.csv'))
    absolute_standard_deviations = pd.read_csv(os.path.join(dirpath, 'standard_deviations.csv'))
    # cbam_factor = pd.read_csv(os.path.join(dirpath,'cbam_factor.csv'))
    return prices, free_allocations, h2share, absolute_standard_deviations
