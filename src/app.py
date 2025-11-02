import dash
from dash import html
import dash_bootstrap_components as dbc

from db_connector import get_db_connection, fetch_plot_list
from layouts import serve_layout
from callbacks import register_callbacks


# CSS do Bootstrap para estilização
external_stylesheets = [dbc.themes.BOOTSTRAP]

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app.title = "AgroDash"


def _build_plot_options():
    with get_db_connection() as conn:
        df = fetch_plot_list(conn)
    # Se vazio, ainda renderiza dropdown
    options = [{"label": r["plot_name"], "value": int(r["plot_id"])} for _, r in df.iterrows()] if not df.empty else []
    return options


# Define o layout com opções do dropdown carregadas do banco.
app.layout = serve_layout(plot_options=_build_plot_options())

# Registra os callbacks
register_callbacks(app)


if __name__ == "__main__":
    # host="0.0.0.0" caso vá dockerizar/expor
    app.run_server(debug=True, host="127.0.0.1", port=8050)