-- ============================================
-- 1) DDL — Criação das Tabelas e Restrições
-- ============================================

-- (Re)criação segura (opcional)
BEGIN
  EXECUTE IMMEDIATE 'DROP TABLE WEATHER_SUGGESTIONS CASCADE CONSTRAINTS';
EXCEPTION WHEN OTHERS THEN NULL; END;
/
BEGIN
  EXECUTE IMMEDIATE 'DROP TABLE SENSOR_LOGS CASCADE CONSTRAINTS';
EXCEPTION WHEN OTHERS THEN NULL; END;
/
BEGIN
  EXECUTE IMMEDIATE 'DROP TABLE PLOT_LOCATIONS CASCADE CONSTRAINTS';
EXCEPTION WHEN OTHERS THEN NULL; END;
/

-- 1. PLOT_LOCATIONS
CREATE TABLE PLOT_LOCATIONS (
  plot_id    NUMBER        PRIMARY KEY,
  plot_name  VARCHAR2(100) NOT NULL,
  crop_type  VARCHAR2(50),
  latitude   NUMBER(10, 6),
  longitude  NUMBER(10, 6)
);

-- 2. SENSOR_LOGS
CREATE TABLE SENSOR_LOGS (
  log_id            NUMBER        PRIMARY KEY,
  plot_id           NUMBER        NOT NULL,
  log_timestamp     TIMESTAMP     NOT NULL,
  humidity          NUMBER(5, 2),
  phosphorus_p      NUMBER(5, 2),
  potassium_k       NUMBER(5, 2),
  ph_level          NUMBER(4, 2),
  irrigation_status VARCHAR2(10)  CONSTRAINT ck_sensor_logs_irrig CHECK (irrigation_status IN ('ON','OFF')),
  CONSTRAINT fk_sensor_logs_plot FOREIGN KEY (plot_id) REFERENCES PLOT_LOCATIONS(plot_id)
);

-- 3. WEATHER_SUGGESTIONS
CREATE TABLE WEATHER_SUGGESTIONS (
  suggestion_id      NUMBER        PRIMARY KEY,
  plot_id            NUMBER        NOT NULL,
  forecast_date      DATE          NOT NULL,
  min_temp_celsius   NUMBER(4, 1),
  max_temp_celsius   NUMBER(4, 1),
  precipitation_mm   NUMBER(5, 1),
  suggested_action   VARCHAR2(20)  CONSTRAINT ck_weather_sugg_action CHECK (suggested_action IN ('IRRIGAR','AGUARDAR','MANTER')),
  reason             VARCHAR2(255),
  CONSTRAINT fk_weather_plot FOREIGN KEY (plot_id) REFERENCES PLOT_LOCATIONS(plot_id)
);

-- (Opcional) Índices úteis para consultas
CREATE INDEX ix_sensor_logs_plot_ts ON SENSOR_LOGS (plot_id, log_timestamp);
CREATE INDEX ix_weather_plot_date  ON WEATHER_SUGGESTIONS (plot_id, forecast_date);