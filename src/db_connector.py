import os
import configparser
from typing import List, Tuple, Optional
from datetime import datetime
import pandas as pd
import oracledb


CONFIG_PATH_DEFAULT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "config.ini")


def _read_config(config_path: Optional[str] = None) -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    path = config_path or CONFIG_PATH_DEFAULT
    if not os.path.exists(path):
        raise FileNotFoundError(f"Arquivo de configuração não encontrado em: {path}")
    cfg.read(path, encoding="utf-8")
    if "database" not in cfg:
        raise KeyError("Seção [database] não encontrada no config.ini")
    return cfg


def get_db_connection(config_path: Optional[str] = None) -> oracledb.Connection:
    """
    Abre e retorna uma conexão Oracle usando `oracledb` (modo Thin por padrão).
    Lê as credenciais de config/config.ini.
    """
    cfg = _read_config(config_path)
    user = cfg["database"].get("user")
    password = cfg["database"].get("password")
    dsn = cfg["database"].get("dsn")

    if not user or not password or not dsn:
        raise ValueError("Parâmetros do banco incompletos. Verifique [database] user/password/dsn no config.ini")

    # Modo Thin (padrão). Para Thick, veja documentação do `oracledb`.
    conn = oracledb.connect(user=user, password=password, dsn=dsn)
    return conn


def fetch_plot_list(conn: oracledb.Connection) -> pd.DataFrame:
    """
    Retorna lista de talhões (plot_id, plot_name) para o dropdown.
    """
    sql = """
        SELECT plot_id, plot_name
        FROM PLOT_LOCATIONS
        ORDER BY plot_name
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()
        df = pd.DataFrame(rows, columns=["plot_id", "plot_name"])
    return df


def fetch_sensor_data(conn: oracledb.Connection, plot_id: int) -> pd.DataFrame:
    """
    Retorna série de sensores (umidade, P, K, pH, status irrigação) para um plot.
    """
    sql = """
        SELECT
            log_id,
            plot_id,
            log_timestamp,
            humidity,
            phosphorus_p,
            potassium_k,
            ph_level,
            irrigation_status
        FROM SENSOR_LOGS
        WHERE plot_id = :plot_id
        ORDER BY log_timestamp
    """
    with conn.cursor() as cur:
        cur.execute(sql, {"plot_id": plot_id})
        rows = cur.fetchall()
        cols = [d[0].lower() for d in cur.description]
    df = pd.DataFrame(rows, columns=cols)
    # Converte timestamp Oracle -> pandas datetime (se necessário)
    if not df.empty:
        df["log_timestamp"] = pd.to_datetime(df["log_timestamp"])
        # Normaliza status para {ON, OFF}
        df["irrigation_status"] = df["irrigation_status"].astype(str).str.upper().str.strip()
    return df


def fetch_latest_irrigation_status(conn: oracledb.Connection, plot_id: int) -> Optional[str]:
    """
    Retorna o status de irrigação mais recente (ON/OFF) para o plot.
    """
    sql = """
        SELECT irrigation_status
        FROM (
            SELECT irrigation_status
            FROM SENSOR_LOGS
            WHERE plot_id = :plot_id
            ORDER BY log_timestamp DESC
        )
        WHERE ROWNUM = 1
    """
    with conn.cursor() as cur:
        cur.execute(sql, {"plot_id": plot_id})
        row = cur.fetchone()
    if row:
        return str(row[0]).upper().strip()
    return None


def fetch_suggestion_data(conn: oracledb.Connection, plot_id: int) -> pd.DataFrame:
    """
    Retorna sugestões climáticas para o plot.
    """
    sql = """
        SELECT
            suggestion_id,
            plot_id,
            forecast_date,
            min_temp_celsius,
            max_temp_celsius,
            precipitation_mm,
            suggested_action,
            reason
        FROM WEATHER_SUGGESTIONS
        WHERE plot_id = :plot_id
        ORDER BY forecast_date
    """
    with conn.cursor() as cur:
        cur.execute(sql, {"plot_id": plot_id})
        rows = cur.fetchall()
        cols = [d[0].lower() for d in cur.description]
    df = pd.DataFrame(rows, columns=cols)
    if not df.empty:
        df["forecast_date"] = pd.to_datetime(df["forecast_date"]).dt.date
        df["suggested_action"] = df["suggested_action"].astype(str).str.upper().str.strip()
    return df