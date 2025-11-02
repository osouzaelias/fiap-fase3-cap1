from typing import List, Dict
import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go


def make_plot_dropdown(options: List[Dict]) -> dbc.Row:
    """
    Dropdown de talhões (plot_id/plot_name).
    `options` no formato: [{"label": "...", "value": <plot_id>}, ...]
    """
    return dbc.Row(
        [
            dbc.Col(html.Label("Selecione o Talhão:", className="fw-semibold"), width="auto"),
            dbc.Col(
                dcc.Dropdown(
                    id="plot-dropdown",
                    options=options,
                    placeholder="Escolha um talhão",
                    clearable=False,
                    style={"minWidth": "280px"},
                ),
                width=4,
            ),
        ],
        className="gy-2 align-items-center mb-3",
    )


def create_layout_tab1() -> html.Div:
    """
    Aba 1 — Sensores: linha de Umidade + 3 indicadores (P, K, pH).
    """
    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(dcc.Graph(id="humidity-line-fig"), md=8),
                    dbc.Col(
                        [
                            dcc.Graph(id="gauge-phosphorus"),
                            dcc.Graph(id="gauge-potassium"),
                            dcc.Graph(id="gauge-ph"),
                        ],
                        md=4,
                    ),
                ],
                className="g-3",
            )
        ],
        className="p-2",
    )


def create_layout_tab2() -> html.Div:
    """
    Aba 2 — Status de Irrigação: série ON/OFF + LED do status atual.
    """
    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        dcc.Graph(id="irrigation-series-fig"),
                        md=9,
                    ),
                    dbc.Col(
                        [
                            html.Div("Status de Irrigação Mais Recente", className="fw-semibold mb-2"),
                            dbc.Badge(id="irrigation-badge", className="p-3 fs-5", color="secondary"),
                        ],
                        md=3,
                    ),
                ],
                className="g-3",
            )
        ],
        className="p-2",
    )


def create_layout_tab3() -> html.Div:
    """
    Aba 3 — Sugestões (Clima): tabela + barras de frequência por ação.
    """
    from dash.dash_table import DataTable  # import local para evitar dependência circular

    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        DataTable(
                            id="suggestions-table",
                            columns=[
                                {"name": "Data", "id": "forecast_date"},
                                {"name": "T. Mín (°C)", "id": "min_temp_celsius"},
                                {"name": "T. Máx (°C)", "id": "max_temp_celsius"},
                                {"name": "Chuva (mm)", "id": "precipitation_mm"},
                                {"name": "Ação", "id": "suggested_action"},
                                {"name": "Motivo", "id": "reason"},
                            ],
                            data=[],
                            page_size=10,
                            style_table={"overflowX": "auto"},
                            style_cell={"textAlign": "center", "padding": "6px"},
                            style_header={"fontWeight": "bold"},
                        ),
                        md=7,
                    ),
                    dbc.Col(
                        dcc.Graph(id="suggestions-bar-fig"),
                        md=5,
                    ),
                ],
                className="g-3",
            )
        ],
        className="p-2",
    )


def serve_layout(plot_options: List[Dict]) -> html.Div:
    """
    Layout raiz com título, dropdown e abas.
    """
    return dbc.Container(
        [
            html.H2("AgroDash — Sensores & Irrigação", className="mt-3 mb-2"),
            html.P("Visualização de dados de campo conectada a Oracle", className="text-muted"),
            html.Hr(),
            make_plot_dropdown(plot_options),
            dcc.Tabs(
                id="tabs",
                value="tab-1",
                children=[
                    dcc.Tab(label="Sensores", value="tab-1", children=create_layout_tab1()),
                    dcc.Tab(label="Irrigação", value="tab-2", children=create_layout_tab2()),
                    dcc.Tab(label="Sugestões (Clima)", value="tab-3", children=create_layout_tab3()),
                ],
            ),
            html.Div(id="hidden-initialized", style={"display": "none"}),  # placeholder caso precise
            html.Footer(
                html.Small("© AgroDash — Dash/Plotly + Oracle • v1"),
                className="text-center text-muted d-block mt-4 mb-3",
            ),
        ],
        fluid=True,
    )