-- Table Stations
CREATE TABLE IF NOT EXISTS stations (
    id TEXT PRIMARY KEY,        -- Id de la estación
    name TEXT,                  -- Nombre de la estación
    timezone TEXT,              -- Zona horaria
    latitude REAL,              -- Latitud
    longitude REAL              -- Longitud
);
-- Tablb Observations
CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,   -- Id interno
    station_id TEXT NOT NULL,              -- Ref
    timestamp TEXT NOT NULL,               -- Momento observación
    temperature REAL,                      -- Temperata Observada
    wind_speed REAL,                       -- Vel viento
    humidity REAL,                         -- Humedad
    FOREIGN KEY (station_id) REFERENCES stations(id),
    UNIQUE (station_id, timestamp)
);
