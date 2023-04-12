import plotly as pl
import pandas as pd


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


def show_and_save(fig: pl.graph_objs.Figure, base_name: str = None):
    fig.show()
    if base_name:
        dir_path = '/mnt/c/Users/jakobdu/data/projects/ccfd/ueckerdt_folie/figures/'
        fig.write_image(dir_path + base_name + '.png')
