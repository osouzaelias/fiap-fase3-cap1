from typing import List, Dict
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output, State
from dash.dash_table import DataTable
import dash_bootstrap_components as dbc

from db_connector import (
    get_db_connection,
    fetch_sensor_data,
    fetch_suggestion_data,
    fetch_latest_irrigation_status,
)


def _make_gauge_indicator(title: str, value: float, vmin: float, vmax: float, suffix: str = "") -> go.Figure:
    """
    Cria um Gauge (Indicator) simples com escala [vmin, vmax].
    """
    value = None if value is None or np.isnan(value) else float(value)
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value if value is not None else 0,
            number={"suffix": suffix},
            title={"text": title},
            gauge={"axis": {"range": [vmin, vmax]}},
        )
    )
    fig.update_layout(margin=dict(l=20, r=20, t=40, b=20), height=180)
    return fig


def register_callbacks(app):
    """
    Registra todos os callbacks do Dash.
    """

    # --- ABA 1: Sensores ---
    @app.callback(
        Output("humidity-line-fig", "figure"),
        Output("gauge-phosphorus", "figure"),
        Output("gauge-potassium", "figure"),
        Output("gauge-ph", "figure"),
        Input("plot-dropdown", "value"),
        prevent_initial_call=True,
    )
    def update_tab1(plot_id):
        if plot_id is None:
            # Gráficos vazios
            return go.Figure(), _make_gauge_indicator("Fósforo (P)", 0, 0, 50), _make_gauge_indicator("Potássio (K)", 0, 0, 60), _make_gauge_indicator("pH", 0, 0, 14)

        with get_db_connection() as conn:
            df = fetch_sensor_data(conn, int(plot_id))

        # Linha de umidade
        if df.empty:
            humidity_fig = px.line(title="Umidade (%) — sem dados")
        else:
            humidity_fig = px.line(
                df,
                x="log_timestamp",
                y="humidity",
                title="Umidade do Solo (%)",
                markers=True,
            )
            humidity_fig.update_layout(xaxis_title="Tempo", yaxis_title="Umidade (%)", margin=dict(l=20, r=20, t=50, b=20))

        # Indicadores médios
        if df.empty:
            p_mean = k_mean = ph_mean = np.nan
        else:
            p_mean = df["phosphorus_p"].astype(float).mean()
            k_mean = df["potassium_k"].astype(float).mean()
            ph_mean = df["ph_level"].astype(float).mean()

        phosphorus_g = _make_gauge_indicator("Fósforo (P)", p_mean, 0, 50, " mg/kg")
        potassium_g = _make_gauge_indicator("Potássio (K)", k_mean, 0, 60, " mg/kg")
        ph_g = _make_gauge_indicator("pH", ph_mean, 0, 14, "")

        return humidity_fig, phosphorus_g, potassium_g, ph_g

    # --- ABA 2: Irrigação ---
    @app.callback(
        Output("irrigation-series-fig", "figure"),
        Output("irrigation-badge", "children"),
        Output("irrigation-badge", "color"),
        Input("plot-dropdown", "value"),
        prevent_initial_call=True,
    )
    def update_tab2(plot_id):
        if plot_id is None:
            return go.Figure(), "—", "secondary"

        with get_db_connection() as conn:
            df = fetch_sensor_data(conn, int(plot_id))
            latest = fetch_latest_irrigation_status(conn, int(plot_id))

        # Série ON/OFF (mapear ON->1, OFF->0)
        if df.empty:
            series_fig = px.line(title="Status de Irrigação — sem dados")
        else:
            ser = df.copy()
            ser["status_num"] = ser["irrigation_status"].map({"ON": 1, "OFF": 0}).fillna(0).astype(int)
            series_fig = px.line(
                ser,
                x="log_timestamp",
                y="status_num",
                title="Status de Irrigação (ON=1, OFF=0)",
                markers=True,
            )
            series_fig.update_yaxes(tickmode="array", tickvals=[0, 1], ticktext=["OFF", "ON"], range=[-0.1, 1.1])
            series_fig.update_layout(xaxis_title="Tempo", yaxis_title="Status", margin=dict(l=20, r=20, t=50, b=20))

        # LED de status mais recente
        badge_text = latest if latest else "—"
        badge_color = "success" if latest == "ON" else ("secondary" if latest is None else "danger")

        return series_fig, badge_text, badge_color

    # --- ABA 3: Sugestões (Clima) ---
    @app.callback(
        Output("suggestions-table", "data"),
        Output("suggestions-bar-fig", "figure"),
        Input("plot-dropdown", "value"),
        prevent_initial_call=True,
    )
    def update_tab3(plot_id):
        if plot_id is None:
            return [], go.Figure()

        with get_db_connection() as conn:
            df = fetch_suggestion_data(conn, int(plot_id))

        if df.empty:
            return [], px.bar(title="Frequência por Ação — sem dados")

        # Tabela
        table_data = df[
            ["forecast_date", "min_temp_celsius", "max_temp_celsius", "precipitation_mm", "suggested_action", "reason"]
        ].to_dict("records")

        # Barras de frequência
        freq = df["suggested_action"].value_counts().reset_index()
        freq.columns = ["suggested_action", "count"]
        bar_fig = px.bar(
            freq,
            x="suggested_action",
            y="count",
            text="count",
            title="Frequência por Ação Sugerida",
        )
        bar_fig.update_layout(xaxis_title="Ação", yaxis_title="Contagem", margin=dict(l=20, r=20, t=50, b=20))

        return table_data, bar_fig