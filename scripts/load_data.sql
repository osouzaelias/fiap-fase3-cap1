-- ============================================
-- 2) DML — População de Dados
-- ============================================

-- 2.1) PLOT_LOCATIONS — 5 talhões de exemplo (Brasil)
INSERT ALL
  INTO PLOT_LOCATIONS (plot_id, plot_name, crop_type, latitude, longitude) VALUES (1, 'Talhão A - Milho', 'Milho',   -22.905000, -47.060000)
  INTO PLOT_LOCATIONS (plot_id, plot_name, crop_type, latitude, longitude) VALUES (2, 'Talhão B - Soja',  'Soja',    -21.176000, -47.820000)
  INTO PLOT_LOCATIONS (plot_id, plot_name, crop_type, latitude, longitude) VALUES (3, 'Talhão C - Café',  'Café',    -20.120000, -45.010000)
  INTO PLOT_LOCATIONS (plot_id, plot_name, crop_type, latitude, longitude) VALUES (4, 'Talhão D - Trigo', 'Trigo',   -29.680000, -51.130000)
  INTO PLOT_LOCATIONS (plot_id, plot_name, crop_type, latitude, longitude) VALUES (5, 'Talhão E - Tomate','Tomate',  -23.550520, -46.633308)
SELECT 1 FROM DUAL;

-- 2.2) SENSOR_LOGS — 200 registros (40 por talhão), últimos 30 dias
-- Regras:
--  - 40 pontos por talhão, distribuídos uniformemente nos últimos 30 dias.
--  - Ciclos de irrigação: a cada bloco de 10, os 3 primeiros ficam 'ON' (0..2) e os demais 'OFF' (3..9).
--  - Quando muda de OFF->ON (no início de cada bloco), a umidade passa a subir nos registros subsequentes.
--  - P, K e pH variam de forma realista e são limitados a faixas plausíveis.

INSERT INTO SENSOR_LOGS (
  log_id, plot_id, log_timestamp,
  humidity, phosphorus_p, potassium_k, ph_level, irrigation_status
)
WITH
  seq AS (
    SELECT LEVEL AS seq FROM DUAL CONNECT BY LEVEL <= 40   -- 40 medições/plot
  ),
  plots AS (
    SELECT plot_id FROM PLOT_LOCATIONS WHERE plot_id BETWEEN 1 AND 5
  ),
  grid AS (
    SELECT p.plot_id, s.seq,
           MOD(s.seq-1,10) AS seg_idx    -- 0..9, define ON/OFF e dinâmica
    FROM plots p
    CROSS JOIN seq s
  )
SELECT
  /* log_id único por talhão e sequência */
  (plot_id*1000) + seq AS log_id,
  plot_id,

  /* Timestamp: últimos 30 dias, do mais antigo (~30d) ao mais recente (~0.75d) */
  SYSTIMESTAMP - NUMTODSINTERVAL(30 - (seq-1)*0.75, 'DAY') AS log_timestamp,

  /* Umidade: sobe nos 3 primeiros pontos do bloco (irrigação ON), e decresce nos demais (OFF) */
  ROUND(
    CASE
      WHEN seg_idx BETWEEN 0 AND 2
        THEN 48 + (seg_idx * 6) + (plot_id * 0.5)     -- 48, 54, 60 (crescendo) com leve offset por talhão
      ELSE
        60 - ((seg_idx - 2) * 3) + (plot_id * 0.5)    -- 57,54,51,...,39 (decrescendo)
    END
  , 2) AS humidity,

  /* Fósforo (P): ~[10..35], variação suave senoidal + leve offset por talhão */
  ROUND(
    LEAST(35,
      GREATEST(10,
        20 + 8*SIN( (seq + plot_id) / 3 ) + (plot_id * 0.7)
      )
    )
  , 2) AS phosphorus_p,

  /* Potássio (K): ~[15..45], variação suave cossenoidal + leve offset por talhão */
  ROUND(
    LEAST(45,
      GREATEST(15,
        25 + 6*COS( (seq + plot_id) / 4 ) + (plot_id * 0.5)
      )
    )
  , 2) AS potassium_k,

  /* pH: ~[5.5..7.5], variação leve e limitada */
  ROUND(
    LEAST(7.5,
      GREATEST(5.5,
        6.5 + 0.8*COS( (seq + plot_id) / 5 )
      )
    )
  , 2) AS ph_level,

  /* Status de irrigação conforme bloco (3 ON + 7 OFF): garante OFF->ON com subida subsequente da umidade */
  CASE WHEN seg_idx BETWEEN 0 AND 2 THEN 'ON' ELSE 'OFF' END AS irrigation_status
FROM grid
ORDER BY plot_id, seq;

-- 2.3) WEATHER_SUGGESTIONS — 60 registros (12 por talhão), cobrindo os últimos ~30 dias
-- Regras de sugestão:
--  * precip_mm > 5.0  -> 'AGUARDAR'  (Motivo: "Chuva prevista")
--  * precip_mm = 0.0 AND max_temp > 30 -> 'IRRIGAR' (Motivo: "Alta temperatura, sem chuva")
--  * caso contrário -> 'MANTER'

INSERT INTO WEATHER_SUGGESTIONS (
  suggestion_id, plot_id, forecast_date,
  min_temp_celsius, max_temp_celsius, precipitation_mm,
  suggested_action, reason
)
WITH
  days AS (
    -- 12 previsões por talhão, espaçadas para cobrir ~24-33 dias (2 a 3 dias de intervalo)
    SELECT LEVEL AS d
    FROM DUAL CONNECT BY LEVEL <= 12
  ),
  plots AS (
    SELECT plot_id FROM PLOT_LOCATIONS WHERE plot_id BETWEEN 1 AND 5
  ),
  grid AS (
    SELECT p.plot_id, d.d
    FROM plots p
    CROSS JOIN days d
  ),
  base_calc AS (
    SELECT
      plot_id,
      d,

      /* Datas de previsão: distribua no passado recente (0, 2, 4, ... 22 dias; ajuste com leve jitter por talhão) */
      TRUNC(SYSDATE) - ( (d-1)*2 + MOD(plot_id,3) ) AS forecast_date,

      /* Precipitação discretizada para garantir casos com 0 e >5 */
      CASE MOD(d + plot_id, 4)
        WHEN 0 THEN 0.0
        WHEN 1 THEN 2.5
        WHEN 2 THEN 8.0
        ELSE 12.5
      END AS precipitation_mm_raw,

      /* Max temp variando entre 28 e 34, com padrão cíclico */
      (28 + MOD(d*plot_id, 7)) AS max_temp_raw
    FROM grid
  ),
  finalized AS (
    SELECT
      plot_id,
      d,
      forecast_date,
      ROUND(precipitation_mm_raw, 1) AS precipitation_mm,
      ROUND(max_temp_raw, 1) AS max_temp_celsius,
      /* min temp = max - (8..10) com leve variação */
      ROUND( (max_temp_raw - (8 + MOD(d + plot_id, 3))), 1 ) AS min_temp_celsius
    FROM base_calc
  )
SELECT
  /* suggestion_id estável e único por (plot, d) */
  (plot_id*100) + d AS suggestion_id,
  plot_id,
  forecast_date,
  min_temp_celsius,
  max_temp_celsius,
  precipitation_mm,
  CASE
    WHEN precipitation_mm > 5.0 THEN 'AGUARDAR'
    WHEN precipitation_mm = 0.0 AND max_temp_celsius > 30 THEN 'IRRIGAR'
    ELSE 'MANTER'
  END AS suggested_action,
  CASE
    WHEN precipitation_mm > 5.0 THEN 'Chuva prevista'
    WHEN precipitation_mm = 0.0 AND max_temp_celsius > 30 THEN 'Alta temperatura, sem chuva'
    ELSE 'Condições estáveis; manter plano atual'
  END AS reason
FROM finalized
ORDER BY plot_id, d;