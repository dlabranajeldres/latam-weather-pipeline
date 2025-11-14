# LATAM Test - Weather Pipeline + Consultas SQL

Pipeline que consume datos del clima desde la API publica del National Weather Service, los guarda en SQLite.

# ¿Qué hace este pipeline?

- Crea la base de datos SQLite (weather.db) con dos tablas:
- stations: info básica de las estaciones.
- observations: datos de clima (temp, viento, humedad).

Descarga 5 estaciones  (Inicialmente al Azar) desde
https://api.weather.gov/stations.
Guarda las estaciones (solo una vez, sin duplicar).

Descarga observaciones para cada estación:

- Primera corrida → últimos 21 días.
- Corridas siguientes → solo datos nuevos desde el último timestamp guardado.
- Inserta las observaciones usando INSERT OR IGNORE, aprovechando una llave única (station_id, timestamp) para evitar duplicados → pipeline idempotente.

# Incluye consultas SQL listas para obtener:

- Temperatura promedio de la última semana.
- Mayor cambio de velocidad del viento en 7 días.
- Mínima y máxima humedad por día.
- Variación diaria de temperatura y humedad.

Consultas en queries.sql.

# Tecnologías usadas

Python 3.14
requests
SQLite

# Estructura del proyecto
.
├── main.py            # pipeline principal
├── schema.sql         # creación de tablas
├── queries.sql        # las consultas del análisis
├── requirements.txt   # dependencia: requests
├── .gitignore
└── README.md

weather.db no se sube al repo porque se genera automáticamente al correr el pipeline.

# Cómo ejecutarlo

Clona el repo:

git clone https://github.com/dlabranajeldres/latam-weather-pipeline.git
cd latam-weather-pipeline

Crea un entorno virtual:

python -m venv venv
venv\Scripts\activate     # Windows

Instala dependencias:

pip install -r requirements.txt
Ejecuta el pipeline:
python main.py

Eso va a:

Crear la DB
Crear las tablas
Bajar estaciones
Bajar observaciones
Guardar todo de forma incremental

# Esquema de la base de datos
CREATE TABLE stations (
    id TEXT PRIMARY KEY,
    name TEXT,
    timezone TEXT,
    latitude REAL,
    longitude REAL
);

CREATE TABLE observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    station_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    temperature REAL,
    wind_speed REAL,
    humidity REAL,
    FOREIGN KEY (station_id) REFERENCES stations(id),
    UNIQUE (station_id, timestamp)
);

# Clave:
UNIQUE (station_id, timestamp) → no hay duplicados y el pipeline puede correr todas las veces que quieras, no hay duplicados y el pipeline puede correr todas las veces que quieras sin insertar datos repetidos
# Consultas del análisis

Las consultas están en queries.sql.

Incluyen:

** Promedio semanal de temperatura
** Máximo salto en la velocidad del viento
** Min/Max humedad diaria
** Variación día a día de temperatura y humedad

# Todas probadas en DB Browser for SQLite.

# Supuestos

- Se usan las 5 primeras estaciones devueltas por /stations.
- No se implementa paginación extra porque el volumen es bajo.
- Abrir weather.db en DB Browser y ejecutar el contenido de queries.sql





