import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import numpy as np
from dash.dependencies import Output, Input
from datetime import datetime
import sqlite3
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import dash_table
import matplotlib.cm
from scipy.stats import chi2_contingency

# !!!! ATENÇÃO !!!!
# Dados originalmente obtidos do Crime Open Database ( https://osf.io/zyaqn/ ) e convertidos para um banco de dados
# sqlite utilizando o código csv2sqlite.py
# O arquivo code_data.sqlite deve estar presente na pasta CODE_Data
#
# Link do repositório do projeto:
# https://github.com/lmreia/Crimes-CODE

# Create a SQL connection to our SQLite database
conn = sqlite3.connect("CODE_Data/code_data.sqlite", check_same_thread=False)

# Adquirindo os valores possíveis para cada coluna do banco
dateparse = lambda x: datetime.strptime(x, '%Y-%m-%d %H:%M:%S')
min_date = dateparse(pd.read_sql_query("SELECT min(date_single) FROM code_data", conn).values[0, 0])
max_date = dateparse(pd.read_sql_query("SELECT max(date_single) FROM code_data", conn).values[0, 0])
possible_offenses = np.sort(
    pd.read_sql_query("SELECT DISTINCT offense_type FROM code_data ORDER BY offense_type", conn).offense_type.unique())
possible_cities = np.sort(
    pd.read_sql_query("SELECT DISTINCT city_name FROM code_data ORDER BY city_name", conn).city_name.unique())
possible_years = np.sort(np.unique(
    pd.read_sql_query("SELECT DISTINCT strftime('%Y',date_single) FROM code_data ORDER BY date_single", conn).values))


# Pré-calculando alguns parâmetros da aba de correlação entre cidades---------------------------------------------------
def pre_calculo_correlacao():
    # Adquirindo a contagem de ocorrência de cada combinação cidade-crime
    filtered_data = pd.read_sql_query(
        "SELECT city_name,offense_type,Count(*) FROM code_data GROUP BY city_name,offense_type ORDER BY city_name,offense_type",
        conn)

    contingency_table = pd.crosstab(filtered_data['city_name'], filtered_data['offense_type'],
                                    filtered_data['Count(*)'], aggfunc='mean')

    contingency_table.fillna(0, inplace=True)

    chi2, p_value, dof, expected = chi2_contingency(contingency_table)

    # Adquirindo a latitude e longitude média de cada cidade
    cities_positions = pd.read_sql_query(
        "SELECT city_name,avg(latitude),avg(longitude) FROM code_data GROUP BY city_name ORDER BY city_name",
        conn)

    # --- Extraindo lista de crimes e cidades para calcular a correlação
    cidades = filtered_data["city_name"].unique()
    crimes = filtered_data["offense_type"].unique()
    # --- Criando dataframe
    E = pd.DataFrame()
    # --- Percorrendo as cidades
    for city in cidades:
        # --- Filtrando dataframe
        d = filtered_data[filtered_data["city_name"] == city].reset_index(drop=True)

        # --- Criando vetor
        y = []
        # --- Percorrendo vetor de crimes
        for crime in crimes:
            try:
                y.append(d[d["offense_type"] == crime]["Count(*)"].values[0])
            except:
                y.append(0)
        # --- Adicionando coluna no dataframe
        E[city] = y

    # Calculando a correlação entre cidades
    CorrTable = E.corr()

    return E, CorrTable, cities_positions, chi2, p_value


vetores_cidades, corr_table, posicoes_cidades, chi2, p_value = pre_calculo_correlacao()
# -----------------------------------------------------------------------------------------------------------------------

# para pegar a contagem de cada crime diretamente em sql
# pd.read_sql_query("SELECT offense_type,COUNT(offense_code) FROM code_data GROUP BY offense_code ORDER BY COUNT(offense_code)", conn)

external_stylesheets = [
    {
        "href": "https://fonts.googleapis.com/css2?family=Lato:wght@400;700&display=swap",
        "rel": "stylesheet",
    },
    dbc.themes.BOOTSTRAP
]
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
server = app.server
app.title = "Crimes CODE"

app.layout = html.Div(
    children=[
        dcc.ConfirmDialog(
            id='confirm_resumo',
            message='Nenhuma ofensa registrada',
        ),
        dcc.ConfirmDialog(
            id='confirm_resumo_crime',
            message='Nenhuma ofensa registrada',
        ),
        dcc.ConfirmDialog(
            id='confirm_geo',
            message='Nenhuma ofensa registrada',
        ),
        html.Div(
            children=[
                html.H1(
                    children="Dados sobre crimes com base no Crime Open Database (CODE)", className="header-title"
                ),
                html.P(
                    children="Análise de ofensas cometidas em cidades dos EUA",
                    className="header-description",
                ),
            ],
            className="header",
        ),
        dcc.Tabs(id='main-tabs', value='tab_cidade', className="tab_bar", children=[
            dcc.Tab(label='Resumo sobre Cidade', value='tab_cidade', children=[
                html.Div(children="Cidade:", className="menu-title"),
                dcc.Dropdown(
                    id="filtro-cidade-resumo",
                    options=[
                        {"label": region, "value": region}
                        for region in possible_cities
                    ],
                    value=possible_cities[0],
                    clearable=False,
                    className="dropdown",
                ),
                dcc.Loading(
                    id="loading-resumo",
                    type="default",
                    children=[
                        html.Div(
                            children=dcc.Graph(
                                id="cidade-histograma-crimes",
                                # config={"displayModeBar": False},
                            ),
                            className="card",
                        ),
                        html.Div(
                            children=dcc.Graph(
                                id="cidade-histograma-anos",
                                # config={"displayModeBar": False},
                            ),
                            className="card",
                        ),
                        html.Div(
                            children=dcc.Graph(
                                id="cidade-boxplot-meses",
                                # config={"displayModeBar": False},
                            ),
                            className="card",
                        ),
                        html.Div(
                            children=[
                                "Padrões identificados: de modo geral, os meses correspondentes ao inverno nos Estados Unidos (Dezembro, Janeiro e Fevereiro) apresentam uma quantidade de ocorrência de crimes menor que os meses do verão (Junho, Julho e Agosto). Isto pode indicar que a temperatura do clima possivelmente influencia a ocorrência de crimes."],
                            className="text_card",
                        ),
                    ]
                ),

            ]),
            dcc.Tab(label='Resumo sobre Crime', value='tab_crime', children=[
                html.Div(children="Crime:", className="menu-title"),
                dcc.Dropdown(
                    id="filtro-crime-resumo",
                    options=[
                        {"label": offense, "value": offense}
                        for offense in possible_offenses
                    ],
                    value=possible_offenses[0],
                    clearable=False,
                    className="dropdown",
                ),
                dcc.Loading(
                    id="loading-resumo-crime",
                    type="default",
                    children=[
                        html.Div(
                            children=dcc.Graph(
                                id="crime-histograma-cidades",
                                # config={"displayModeBar": False},
                            ),
                            className="card",
                        ),
                        html.Div(
                            children=dcc.Graph(
                                id="crime-histograma-anos",
                                # config={"displayModeBar": False},
                            ),
                            className="card",
                        ),
                        html.Div(
                            children=dcc.Graph(
                                id="crime-boxplot-meses",
                                # config={"displayModeBar": False},
                            ),
                            className="card",
                        ),
                        html.Div(
                            children=[
                                "Padrões identificados: de modo geral, os meses correspondentes ao inverno nos Estados Unidos (Dezembro, Janeiro e Fevereiro) apresentam uma quantidade de ocorrência de crimes menor que os meses do verão (Junho, Julho e Agosto). Isto pode indicar que a temperatura do clima possivelmente influencia a ocorrência de crimes."],
                            className="text_card",
                        ),
                    ]
                ),
            ]),
            dcc.Tab(label='Visualização Geográfica', value='tab_geo', children=[

                dbc.Row(
                    [
                        dbc.Col(html.Div(
                            children=[
                                html.Div(children="Cidade:", className="menu-title"),
                            ],
                        ), width=2),
                        dbc.Col(html.Div(
                            children=[
                                dcc.Dropdown(
                                    id="filtro-cidade-geo",
                                    options=[
                                        {"label": region, "value": region}
                                        for region in possible_cities
                                    ],
                                    value=possible_cities[0],
                                    clearable=False,
                                    className="dropdown",
                                ),
                            ],
                        ), width=3),
                        dbc.Col(html.Div(
                            children=[
                                html.Div(children="Ano:", className="menu-title"),
                            ],
                        ), width=2),
                        dbc.Col(html.Div(
                            children=[
                                dcc.Dropdown(
                                    id="filtro-data-geo",
                                    options=[
                                        {"label": selected_year, "value": selected_year}
                                        for selected_year in possible_years
                                    ],
                                    value=possible_years[0],
                                    clearable=False,
                                    searchable=False,
                                    className="dropdown",
                                ),
                            ],
                        ), width=2),
                        dbc.Col(html.Div(
                            children=[
                                dcc.RadioItems(
                                    id="geo-radio",
                                    options=[
                                        {'label': 'Scatter', 'value': 'SCATTER'},
                                        {'label': 'Density', 'value': 'DENSITY'},
                                    ],
                                    value='DENSITY',
                                    labelStyle={'display': 'inline-block'}
                                ),
                            ],
                        ), width=3),
                    ]
                ),
                dbc.Row(
                    [
                        dbc.Col(html.Div(
                            children=[
                                html.Div(children="Tipo de ofensa:", className="menu-title"),
                            ],
                        ), width=3),
                        dbc.Col(html.Div(
                            children=[
                                dcc.Dropdown(
                                    id="filtro-ofensa-geo",
                                    options=[
                                        {"label": offense, "value": offense}
                                        for offense in possible_offenses
                                    ],
                                    value=possible_offenses[0],
                                    clearable=False,
                                    searchable=False,
                                    className="dropdown",
                                ),
                            ],
                        ), width=9),
                    ]
                ),
                dcc.Loading(
                    id="loading-geo",
                    type="default",
                    children=html.Div(
                        children=dcc.Graph(
                            id="geo-chart",
                            # config={"displayModeBar": False},,
                            className="geo_card",
                        ),
                        className="geo_card",
                    ),
                ),
            ]),
            dcc.Tab(label='Correlação entre Cidades', value='tab_correlacao', children=[
                dcc.Loading(
                    id="loading-corr",
                    type="default",
                    children=[
                        html.Label(
                            "Contagem total de ocorrências para cada combinação crime-cidade (Tabela de Contingência)",
                            className="text_card"),
                        html.Div(
                            id="count_table",
                            className="card_table",
                        ),
                        html.Div(
                            id="text_chi2",
                            children=[],
                            className="text_card",
                        ),
                        html.Label("Coeficiente de correlação de Pearson entre cidades com base nos vetores de contagem de crimes",
                                   className="text_card"),
                        html.Div(
                            id="corr_table",
                            className="card_table",
                        ),
                        html.Div(
                            children=dcc.Graph(
                                id="corr_image",
                                # config={"displayModeBar": False},
                            ),
                            className="card",
                        ),
                        html.Label("Visualização da correlação entre cidades",
                                   className="text_card"),
                        html.Div(children="Cidade:", className="menu-title"),
                        dcc.Dropdown(
                            id="filtro-cidade-corr",
                            options=[
                                {"label": region, "value": region}
                                for region in possible_cities
                            ],
                            value=possible_cities[0],
                            clearable=False,
                            className="dropdown",
                        ),
                        html.Div(
                            children=dcc.Graph(
                                id="geo_corr",
                                # config={"displayModeBar": False},
                                className="geo_card",
                            ),
                            className="geo_card",
                        ),
                        html.Div(
                            children=[
                                "Os resultados acima permitem identificar que existe uma associação entre a posição geográfica e o padrão de ofensas cometido na cidade. O mapa iterativo mostra os pares de cidades que possuem padrões semelhantes de criminalidade."],
                            className="text_card",
                        ),
                    ],
                ),
            ]),
        ]),
    ]
)


@app.callback(
    [Output("cidade-histograma-crimes", "figure"), Output("cidade-histograma-anos", "figure"),
     Output("cidade-boxplot-meses", "figure"),
     Output('confirm_resumo', 'displayed')],
    [
        Input("filtro-cidade-resumo", "value"),
        Input("main-tabs", "value"),
    ],
)
def update_charts_resumo_cidade(filtro_cidade, tab_value):
    if tab_value != "tab_cidade":
        return go.Figure(), go.Figure(), go.Figure(), False

    filtered_data_crimes = pd.read_sql_query(
        "SELECT offense_type,COUNT(offense_type) FROM code_data WHERE city_name=:region GROUP BY offense_type ORDER BY COUNT(offense_type)",
        conn, params={"region": filtro_cidade})
    histograma_crimes_figure = px.bar(filtered_data_crimes, y="offense_type", x="COUNT(offense_type)",
                                      title="Contagem de ocorrências de cada crime", orientation="h")
    histograma_crimes_figure.layout.yaxis.dtick = 1
    histograma_crimes_figure.layout.height = 1500
    histograma_crimes_figure.layout.yaxis.title = ""
    histograma_crimes_figure.layout.xaxis.title = "Contagem de ocorrências"

    filtered_data_anos = pd.read_sql_query(
        "SELECT strftime('%Y-%m',date_single),COUNT(strftime('%Y-%m',date_single)) FROM code_data WHERE city_name=:region GROUP BY strftime('%Y-%m',date_single) ORDER BY strftime('%Y-%m',date_single)",
        conn, params={"region": filtro_cidade})
    histograma_anos_figure = px.bar(filtered_data_anos, x="strftime('%Y-%m',date_single)",
                                    y="COUNT(strftime('%Y-%m',date_single))",
                                    title="Contagem total de ocorrências de crimes em função do tempo")
    histograma_anos_figure.layout.yaxis.title = "Contagem de ocorrências"
    histograma_anos_figure.layout.xaxis.title = "Meses"

    filtered_data_meses = pd.read_sql_query(
        "SELECT strftime('%m',date_single),COUNT(strftime('%Y-%m',date_single)) FROM code_data WHERE city_name=:region GROUP BY strftime('%Y-%m',date_single) ORDER BY strftime('%m',date_single)",
        conn, params={"region": filtro_cidade})
    boxplot_meses_figure = px.box(filtered_data_meses, x="strftime('%m',date_single)",
                                  y="COUNT(strftime('%Y-%m',date_single))",
                                  title="Ocorrência total de crimes para cada mês")
    boxplot_meses_figure.layout.yaxis.title = "Contagem de ocorrências"
    boxplot_meses_figure.layout.xaxis.title = "Mês"

    return histograma_crimes_figure, histograma_anos_figure, boxplot_meses_figure, (
            filtered_data_crimes.empty or filtered_data_anos.empty or filtered_data_meses.empty)


@app.callback(
    [Output("crime-histograma-cidades", "figure"), Output("crime-histograma-anos", "figure"),
     Output("crime-boxplot-meses", "figure"),
     Output('confirm_resumo_crime', 'displayed')],
    [
        Input("filtro-crime-resumo", "value"),
        Input("main-tabs", "value"),
    ],
)
def update_charts_resumo_crime(filtro_crime, tab_value):
    if tab_value != "tab_crime":
        return go.Figure(), go.Figure(), go.Figure(), False

    filtered_data_cidades = pd.read_sql_query(
        "SELECT city_name,COUNT(city_name) FROM code_data WHERE offense_type=:offense GROUP BY city_name ORDER BY COUNT(city_name)",
        conn, params={"offense": filtro_crime})
    histograma_cidades_figure = px.bar(filtered_data_cidades, y="city_name", x="COUNT(city_name)",
                                       title="Contagem de ocorrências para cada cidade", orientation="h")
    histograma_cidades_figure.layout.yaxis.dtick = 1
    histograma_cidades_figure.layout.height = 1000
    histograma_cidades_figure.layout.yaxis.title = ""
    histograma_cidades_figure.layout.xaxis.title = "Contagem de ocorrências"

    filtered_data_anos = pd.read_sql_query(
        "SELECT strftime('%Y-%m',date_single),COUNT(strftime('%Y-%m',date_single)) FROM code_data WHERE offense_type=:offense GROUP BY strftime('%Y-%m',date_single) ORDER BY strftime('%Y-%m',date_single)",
        conn, params={"offense": filtro_crime})
    histograma_anos_figure = px.bar(filtered_data_anos, x="strftime('%Y-%m',date_single)",
                                    y="COUNT(strftime('%Y-%m',date_single))",
                                    title="Contagem total de ocorrências do crime em função do tempo")
    histograma_anos_figure.layout.yaxis.title = "Contagem de ocorrências"
    histograma_anos_figure.layout.xaxis.title = "Meses"

    filtered_data_meses = pd.read_sql_query(
        "SELECT strftime('%m',date_single),COUNT(strftime('%Y-%m',date_single)) FROM code_data WHERE offense_type=:offense GROUP BY strftime('%Y-%m',date_single) ORDER BY strftime('%m',date_single)",
        conn, params={"offense": filtro_crime})
    boxplot_meses_figure = px.box(filtered_data_meses, x="strftime('%m',date_single)",
                                  y="COUNT(strftime('%Y-%m',date_single))",
                                  title="Ocorrência total de crimes para cada mês")
    boxplot_meses_figure.layout.yaxis.title = "Contagem de ocorrências"
    boxplot_meses_figure.layout.xaxis.title = "Mês"

    return histograma_cidades_figure, histograma_anos_figure, boxplot_meses_figure, (
            filtered_data_cidades.empty or filtered_data_anos.empty or filtered_data_meses.empty)


@app.callback(
    [Output("geo-chart", "figure"),
     Output('confirm_geo', 'displayed')],
    [
        Input("filtro-cidade-geo", "value"),
        Input("filtro-ofensa-geo", "value"),
        Input("filtro-data-geo", "value"),
        Input("geo-radio", "value"),
        Input("main-tabs", "value"),
    ],
)
def update_charts_geo(filtro_cidade, filtro_ofensa, filtro_data, geo_radio, tab_value):
    if tab_value != "tab_geo":
        return go.Figure(), False

    filtered_data = pd.read_sql_query(
        "SELECT date_single,latitude,longitude,offense_type FROM code_data WHERE city_name=:region AND offense_type=:type AND strftime('%Y',date_single)=:date",
        con=conn, params={
            "region": filtro_cidade, "type": filtro_ofensa, "date": filtro_data})

    latcenter = np.mean(filtered_data.latitude)
    longcenter = np.mean(filtered_data.longitude)

    if geo_radio == "SCATTER":
        geo_chart_figure = px.scatter_mapbox(filtered_data,
                                             lat="latitude",
                                             lon="longitude",
                                             # text="offense_code",
                                             hover_name="offense_type",
                                             # color_continuous_scale="Viridis",
                                             # range_color=(0, 12),
                                             mapbox_style="carto-positron",
                                             # zoom=3,
                                             center={"lat": latcenter, "lon": longcenter},
                                             opacity=0.5,
                                             # labels={'unemp': 'unemployment rate'}
                                             )
    else:
        geo_chart_figure = px.density_mapbox(filtered_data,
                                             lat="latitude",
                                             lon="longitude",
                                             # text="offense_code",
                                             hover_name="offense_type",
                                             # color_continuous_scale="Viridis",
                                             # range_color=(0, 12),
                                             mapbox_style="carto-positron",
                                             # zoom=3,
                                             center={"lat": latcenter, "lon": longcenter},
                                             opacity=0.5,
                                             # labels={'unemp': 'unemployment rate'}
                                             radius=10
                                             )

    return geo_chart_figure, filtered_data.empty


@app.callback(
    [Output("count_table", "children"), Output("corr_table", "children"), Output("corr_image", "figure"),
     Output("text_chi2", "children"),],
    [
        Input("main-tabs", "value"),
    ],
)
def update_tables_corr(tab_value):
    if tab_value != "tab_correlacao":
        return "", "", go.Figure(), ""

    # Exibição da tabela com os vetores de ocorrências
    crimes = possible_offenses.copy()
    for i in range(len(crimes)):
        crimes[i] = crimes[i][:20]

    E = vetores_cidades.copy()
    E.insert(0, "Crimes", crimes)

    table_count = dash_table.DataTable(
        id='table',
        columns=[{"name": i, "id": i} for i in E.columns],
        data=E.to_dict('records'),
    )

    # Exibição da imagem com os dados de correlação
    figure_corr = px.imshow(corr_table,
                            # labels=dict(x="city_name", y="Time of Day", color="Productivity"),
                            x=possible_cities,
                            y=possible_cities,
                            title="Correlação entre cidades com base nos vetores de contagem de crimes"
                            )

    # Exibição da tabela de correlações
    CorrTable = corr_table.copy()
    for column in CorrTable:
        CorrTable[column] = CorrTable[column].map('{:,.2f}'.format)

    CorrTable.insert(0, "Cidade", possible_cities)

    table_corr = dash_table.DataTable(
        id='table',
        columns=[{"name": i, "id": i} for i in CorrTable.columns],
        data=CorrTable.to_dict('records'),
    )

    text_chi2 = "Obteve-se um valor de Qui-quadrado de {0} com p-value de {1}. Isto indica existência de associação entre cidade e tipo de ofensa.".format(chi2, p_value)

    return table_count, table_corr, figure_corr, text_chi2


@app.callback(
    [Output("geo_corr", "figure"), ],
    [
        Input("main-tabs", "value"),
        Input("filtro-cidade-corr", "value"),
    ],
)
def update_charts_corr(tab_value, filtro_cidade_geo):
    if tab_value != "tab_correlacao":
        return [go.Figure()]

    # Exibição do gráfico mostrando os links entre cidades
    cmap = matplotlib.cm.get_cmap('plasma')

    geo_corr_figure = go.Figure()
    city1 = filtro_cidade_geo
    for city2 in possible_cities:
        if city1 == city2:
            continue
        city1_lat = posicoes_cidades[posicoes_cidades["city_name"] == city1]['avg(latitude)'].values[0]
        city1_long = posicoes_cidades[posicoes_cidades["city_name"] == city1]['avg(longitude)'].values[0]
        city2_lat = posicoes_cidades[posicoes_cidades["city_name"] == city2]['avg(latitude)'].values[0]
        city2_long = posicoes_cidades[posicoes_cidades["city_name"] == city2]['avg(longitude)'].values[0]
        rgba = cmap(corr_table[city1][city2])
        geo_corr_figure.add_trace(
            go.Scattermapbox(
                mode="markers+lines",
                lat=[city1_lat, city2_lat],
                lon=[city1_long, city2_long],
                line={'width': 1,
                      'color': "rgb({0}, {1}, {2})".format(rgba[0] * 255, rgba[1] * 255, rgba[2] * 255), },
                marker={'size': 10},
                text="{0}-{1}. Correlação: {2}".format(city1, city2, corr_table[city1][city2]),
                name="{0}-{1}".format(city1, city2),
            )
        )

    # Adicionando a correlação da cidade com ela mesma por último
    city2 = city1
    city1_lat = posicoes_cidades[posicoes_cidades["city_name"] == city1]['avg(latitude)'].values[0]
    city1_long = posicoes_cidades[posicoes_cidades["city_name"] == city1]['avg(longitude)'].values[0]
    city2_lat = posicoes_cidades[posicoes_cidades["city_name"] == city2]['avg(latitude)'].values[0]
    city2_long = posicoes_cidades[posicoes_cidades["city_name"] == city2]['avg(longitude)'].values[0]
    rgba = cmap(corr_table[city1][city2])
    geo_corr_figure.add_trace(
        go.Scattermapbox(
            mode="markers+lines",
            lat=[city1_lat, city2_lat],
            lon=[city1_long, city2_long],
            line={'width': 1,
                  'color': "rgb({0}, {1}, {2})".format(rgba[0] * 255, rgba[1] * 255, rgba[2] * 255), },
            marker={'size': 10},
            text="{0}-{1}. Correlação: {2}".format(city1, city2, corr_table[city1][city2]),
            name="{0}-{1}".format(city1, city2),
        )
    )

    # Calculando a posição média de todas as cidades
    latcenter = posicoes_cidades['avg(latitude)'].mean()
    longcenter = posicoes_cidades['avg(longitude)'].mean()

    geo_corr_figure.update_mapboxes(style="carto-positron", center={"lat": latcenter, "lon": longcenter}, zoom=3)

    return [geo_corr_figure]


if __name__ == "__main__":
    app.run_server(host='0.0.0.0', debug=False)
