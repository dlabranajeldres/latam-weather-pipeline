# 1. Temperatura media de la última semana (lunes a domingo)
WITH latest AS (
    SELECT date(MAX(timestamp)) AS last_date
    FROM observations
),
week_info AS (
    SELECT
        strftime('%Y', last_date) AS yr,
        strftime('%W', last_date) AS wk
    FROM latest
)
SELECT
    AVG(temperature) AS avg_temperature_last_week
FROM
    observations,
    week_info
WHERE
    strftime('%Y', date(timestamp)) = week_info.yr
    AND strftime('%W', date(timestamp)) = week_info.wk;


# 2. Máximo cambio de velocidad del viento entre dos observaciones consecutivas (últimos 7 días)
WITH recent AS (
    SELECT
        station_id,
        timestamp,
        wind_speed,
        LAG(wind_speed) OVER (
            PARTITION BY station_id
            ORDER BY timestamp
        ) AS prev_wind_speed
    FROM observations
    WHERE timestamp >= datetime('now', '-7 days')
),
diffs AS (
    SELECT
        station_id,
        timestamp,
        ABS(wind_speed - prev_wind_speed) AS delta_wind
    FROM recent
    WHERE prev_wind_speed IS NOT NULL
)
SELECT
    station_id,
    timestamp,
    delta_wind AS max_wind_change
FROM diffs
ORDER BY delta_wind DESC
LIMIT 1;


# 3. Mínima y máxima humedad por día
SELECT
    date(timestamp) AS day,
    MIN(humidity) AS min_humidity,
    MAX(humidity) AS max_humidity
FROM observations
GROUP BY day
ORDER BY day;


# 4. Variación promedio de humedad y temperatura vs el día anterior
WITH daily AS (
    SELECT
        date(timestamp) AS day,
        AVG(temperature) AS avg_temp,
        AVG(humidity) AS avg_hum
    FROM observations
    GROUP BY day
),
with_prev AS (
    SELECT
        day,
        avg_temp,
        avg_hum,
        LAG(avg_temp) OVER (ORDER BY day) AS prev_avg_temp,
        LAG(avg_hum) OVER (ORDER BY day) AS prev_avg_hum
    FROM daily
)
SELECT
    day,
    avg_temp,
    prev_avg_temp,
    avg_temp - prev_avg_temp AS diff_temp_vs_prev_day,
    avg_hum,
    prev_avg_hum,
    avg_hum - prev_avg_hum AS diff_hum_vs_prev_day
FROM with_prev
WHERE prev_avg_temp IS NOT NULL
ORDER BY day;
