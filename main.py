from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, List, Optional

import requests

# Configuración

BASE_URL = "https://api.weather.gov"
DB_PATH = Path("weather.db")
SCHEMA_PATH = Path("schema.sql")

# Funciones de base de datos

def get_connection() -> sqlite3.Connection:
    """Retorna una conexión a la base de datos SQLite."""
    return sqlite3.connect(DB_PATH)


def init_database() -> None:
    """Crea la base de datos y el esquema si no existen."""
    with get_connection() as conn, SCHEMA_PATH.open("r", encoding="utf-8") as f:
        conn.executescript(f.read())
    print("Base de datos inicializada.")


# Estaciones

def fetch_stations(limit: int = 5) -> List[dict]:
    """
    Obtiene estaciones desde la API pública del NWS.

    Parameters
    ----------
    limit : int
        Número de estaciones a solicitar.

    Returns
    -------
    list[dict]
        Lista de features tal como las entrega la API.
        Devuelve lista vacía si ocurre un error de red.
    """
    url = f"{BASE_URL}/stations"
    params = {"limit": limit}

    print(f"Solicitando estaciones: {url} (limit={limit})")

    try:
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        # Cubre timeouts, conexión rechazada, HTTP 4xx/5xx, etc.
        print(f"Error al obtener estaciones: {exc}")
        return []

    data = response.json()
    features = data.get("features", [])
    print(f"Estaciones recibidas: {len(features)}")

    return features


def upsert_stations(stations: Iterable[dict]) -> None:
    """
    Inserta estaciones en la tabla `stations`.

    Usa INSERT OR IGNORE para garantizar idempotencia.
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        for feature in stations:
            props = feature.get("properties", {})

            station_id = props.get("stationIdentifier")
            name = props.get("name")
            timezone_name = props.get("timeZone")
            latitude = props.get("latitude")
            longitude = props.get("longitude")

            cursor.execute(
                """
                INSERT OR IGNORE INTO stations (id, name, timezone, latitude, longitude)
                VALUES (?, ?, ?, ?, ?)
                """,
                (station_id, name, timezone_name, latitude, longitude),
            )

    print("Estaciones almacenadas (INSERT OR IGNORE).")


def get_station_ids() -> List[str]:
    """Devuelve la lista de IDs de estaciones almacenadas en la base."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM stations")
        rows = cursor.fetchall()

    return [row[0] for row in rows]

# Observaciones

def get_last_observation_timestamp(station_id: str) -> Optional[str]:
    """
    Obtiene el último timestamp registrado para una estación.
    Devuelve None si no hay datos.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT MAX(timestamp) FROM observations WHERE station_id = ?",
            (station_id,),
        )
        row = cursor.fetchone()

    return row[0] if row else None


def fetch_observations(
    station_id: str,
    start_iso: str,
    end_iso: str,
) -> List[dict]:
    """
    Obtiene observaciones para una estación en un rango de tiempo.

    Utiliza /stations/{id}/observations con parámetros start/end.
    Devuelve lista vacía si ocurre un error de red o HTTP.
    """
    url = f"{BASE_URL}/stations/{station_id}/observations"
    params = {"start": start_iso, "end": end_iso}

    print(f"Observaciones {station_id}: {start_iso} → {end_iso}")

    try:
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        print(f"Error al obtener observaciones de {station_id}: {exc}")
        return []

    data = response.json()
    features = data.get("features", [])
    print(f"Observaciones recibidas: {len(features)}")

    return features


def _round2(value: Optional[float]) -> Optional[float]:
    """Redondea a 2 decimales si value es numérico, si no, devuelve None."""
    if isinstance(value, (int, float)):
        return round(value, 2)
    return None


def insert_observations(station_id: str, observations: Iterable[dict]) -> None:
    """
    Inserta observaciones en la tabla `observations`.

    Se apoya en la restriccion UNIQUE (station_id, timestamp)
    Garantizar idempotencia.
    """
    inserted = 0

    with get_connection() as conn:
        cursor = conn.cursor()

        for feature in observations:
            props = feature.get("properties", {})

            timestamp = props.get("timestamp")

            temp = props.get("temperature", {}).get("value")
            wind_speed = props.get("windSpeed", {}).get("value")
            humidity = props.get("relativeHumidity", {}).get("value")

            temp = _round2(temp)
            wind_speed = _round2(wind_speed)
            humidity = _round2(humidity)

            cursor.execute(
                """
                INSERT OR IGNORE INTO observations
                    (station_id, timestamp, temperature, wind_speed, humidity)
                VALUES (?, ?, ?, ?, ?)
                """,
                (station_id, timestamp, temp, wind_speed, humidity),
            )

            inserted += cursor.rowcount  # 1 si insertó, 0 si ignoró

    print(f" {station_id}: {inserted} observaciones nuevas.")


def update_observations(days_back: int = 21) -> None:
    """
    Actualiza las observaciones de todas las estaciones.

    - Si una estación no tiene datos: baja `days_back`
    - Si ya tiene datos: baja desde el último timestamp hasta el momento de consulta
    """
    station_ids = get_station_ids()
    now = datetime.now(timezone.utc)
    end_iso = now.isoformat()

    for station_id in station_ids:
        last_ts = get_last_observation_timestamp(station_id)

        if last_ts is None:
            # Primera carga ultimos N días
            start_dt = now - timedelta(days=days_back)
            print(f"{station_id}: sin datos previos, cargando últimos {days_back} dias.")
        else:
            # Incremental desde el último dato
            start_dt = datetime.fromisoformat(last_ts)
            print(f" {station_id}: ultimo dato en {last_ts}, cargando datos nuevos.")

        start_iso = start_dt.isoformat()

        observations = fetch_observations(station_id, start_iso, end_iso)
        if not observations:
            print(f"No se obtuvieron observaciones nuevas para {station_id}.")
            continue

        insert_observations(station_id, observations)

# Punto de entrada


def main() -> None:
    """Orquesta la ejecucion completa del pipeline."""
    init_database()

    stations = fetch_stations(limit=5)
    if not stations:
        # Si no se pudieron obtener, no tiene sentido seguir
        print("No se obtuvieron estaciones. Se aborta la actualizacion de observaciones.")
        return

    upsert_stations(stations)
    update_observations(days_back=21)

    print("Pipeline ejecutado correctamente.")

# Por siaca errores 

if __name__ == "__main__":
    try:
        main()
    except sqlite3.Error as db_err:
        print(f"Error de base de datos: {db_err}")
    except requests.exceptions.RequestException as http_err:
        # Por si se escapara alguna RequestException no manejada dentro de las funciones
        print(f"Error de red al llamar a la API: {http_err}")
    except Exception as exc:
        # Último recurso: no deja el stacktrace crudo, pero si muestra el error
        print(f"Error inesperado: {exc}")
