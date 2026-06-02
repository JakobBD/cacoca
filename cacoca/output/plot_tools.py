import plotly as pl
import pandas as pd
import os


# define colors to use
def add_color(projects: pd.DataFrame = None, by_column: str = None):

    colors = projects.filter([by_column]).drop_duplicates()
    colors['color'] = get_color(colors[by_column].values.tolist())
    projects = projects.merge(colors, how='left', on=[by_column])

    return projects


def get_color(variables: list):
    n_scen = len(variables)
    if n_scen <= 10:
        cmap = pl.colors.qualitative.D3
    elif n_scen <= 24:
        cmap = pl.colors.qualitative.Dark24
    else:
        cmap = pl.colors.sample_colorscale('Viridis', n_scen + 1, colortype='rgb')

    return cmap[:n_scen]


def set_yrange_min_zero(fig: pl.graph_objs.Figure):
    all_y = [
        v for trace in fig.data
        if hasattr(trace, 'y') and trace.y is not None
        for v in trace.y if v is not None
    ]
    if not all_y:
        return
    ymax = max(all_y)
    yrange = [-0.04 * ymax, 1.04 * ymax]
    fig.update_yaxes(range=yrange)


def show_and_save(fig: pl.graph_objs.Figure, config: dict, base_name: str = None):
    if config['show_figures']:
        if config['show_figs_in_browser']:
            pl.io.renderers.default = "browser"
        fig.show()
    if base_name and config['save_figures']:
        dir_path = config['output_dir']
        filename_prefix = config.get('filename_prefix', '')
        if filename_prefix:
            base_name = f"{filename_prefix}_{base_name}"
        if config['crop_figures']:
            fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), title='')
        fig.update_layout(width=1000, height=600, font=dict(size=18))
        fig.write_image(os.path.join(dir_path, base_name + '.png'))


display_names = {
    'steel_dri': 'Stahl DRI',
    'cement': 'Zement',
    'other_industries': 'Andere',
    'glass_and_ceramics': 'Glass',
    'basic_chemicals': 'Grundstoff-Chemie',
    'Effective CO2 Price': 'CO2-Preis (effektiv)',
    'Industry': 'Sektor',
    'Project name': 'Projekt',
    'compare_sectors': 'Sektorvergleich',
    'Abatement_cost': 'Vermeidungskosten',
    'Additional OPEX': 'Sonstige OPEX',
    'CAPEX annuity': 'CAPEX Annuität',
    'h2share_influence': 'Einfluss des H2-Anteils',
    'ccsshare_influence': 'Einfluss des CCS-Anteils',
    'all': 'kombiniert',
    'h2': 'H2',
    'ng': 'Erdgas',
    'elec': 'Strom',
    'ccoal': 'Kokskohle',
    'lowh2': '10-30% H2',
    'varyh2': '0-100% H2',
    'onlyh2': '100% H2',
    'prices': 'Preisannahmen',
    'Hydrogen': 'Wasserstoff',
    'Natural Gas': 'Erdgas',
    'Electricity': 'Strom',
    'Iron Ore': 'Eisenerz',
    'Injection Coal': 'Einblaskohle',
    'Scrap Steel': 'Stahlschrott',
    'Coking Coal': 'Kokskohle',
    'H2 Share': 'Anteil Wasserstoff',
    'all_projects': 'Alle Projekte',
    'CO2 Cost': 'CO₂ Emissionskosten (ETS)',
    'OM Fixed': 'Sonstige OPEX (fix)',
    'OM Variable': 'Sonstige OPEX (variabel)',
    'Coal': 'Kohle',
    'Biomethane': 'Biomethan',
    'DRI-Pellets': 'DRI-Pellets',
    'BF-BOF-Conv': 'BF-BOF konventionell',
    'BF-BOF-CCS': 'BF-BOF mit CCS',
    'H2-DR-EAF': 'H₂-DR-EAF',
    '': '',
    '': ''
}


def display_name(varname: str):
    if str(varname).startswith('sensitivity'):
        _, scen_name, h2name = varname.split('_')
        return f"Preisunsicherheit {display_name(scen_name)}, {display_name(h2name)}"
    else:
        return display_names.get(varname, varname)


def to_rgba(color: str, alpha: float):
    if isinstance(color, tuple):
        rgba = f"rgba{color + (alpha,)}"
    elif color.startswith("#"):
        rgba = f"rgba{pl.colors.hex_to_rgb(color) + (alpha,)}"
    else:
        rgba = color.replace("rgb", "rgba").replace(")", f", {alpha})")
    return rgba


def change_output_subdir_by_filename(config: dict, filename):
    subdirname = os.path.basename(filename)
    subdirname = os.path.splitext(subdirname)[0]
    if subdirname == os.path.split(config['output_dir'])[1]:
        return
    subdir = os.path.join(config['output_dir'], subdirname)
    if not os.path.exists(subdir):
        os.makedirs(subdir)
    config['output_dir'] = subdir
    return
