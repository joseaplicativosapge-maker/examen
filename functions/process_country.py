import json
from datetime import datetime
from utils.logger import get_logger
from utils.s3_helper import save_json
from functions.clients import rest_countries, open_meteo, nager


def process(event: dict) -> dict:
    job_id = event["job_id"]
    country_code = event["country_code"]
    start_date = event["date_range"]["start_date"]
    end_date = event["date_range"]["end_date"]

    log = get_logger(job_id, country_code)
    log("Iniciando procesamiento de país")

    try:
        # ── 1. REST Countries ──────────────────────────────
        country_data = rest_countries.fetch(country_code, job_id)

        save_json(
            f"bronze/jobs/{job_id}/countries/{country_code}/rest_countries_raw.json",
            country_data
        )
        log("Bronze: rest_countries_raw.json guardado")

        # Extraer coordenadas
        latlng = country_data.get("latlng", [0, 0])
        lat, lon = latlng[0], latlng[1]

        # ── 2. Open-Meteo ──────────────────────────────────
        weather_data = open_meteo.fetch(lat, lon, start_date, end_date, job_id, country_code)

        save_json(
            f"bronze/jobs/{job_id}/countries/{country_code}/open_meteo_raw.json",
            weather_data
        )
        log("Bronze: open_meteo_raw.json guardado")

        # ── 3. Nager.Date ──────────────────────────────────
        year = int(start_date[:4])
        holidays_data = nager.fetch(country_code, year, job_id)

        save_json(
            f"bronze/jobs/{job_id}/countries/{country_code}/holidays_raw.json",
            {"holidays": holidays_data}
        )
        log("Bronze: holidays_raw.json guardado")

        # ── 4. Normalizar → Silver ─────────────────────────
        summary = normalize(
            job_id, country_code, country_data,
            weather_data, holidays_data,
            start_date, end_date
        )

        save_json(
            f"silver/jobs/{job_id}/countries/{country_code}/country_summary.json",
            summary
        )
        log("Silver: country_summary.json guardado")

        return summary

    except Exception as e:
        log(f"Error procesando país: {str(e)}", level="ERROR")

        error_payload = {
            "job_id": job_id,
            "country_code": country_code,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

        save_json(
            f"errors/jobs/{job_id}/countries/{country_code}/error.json",
            error_payload
        )

        return {
            "job_id": job_id,
            "country_code": country_code,
            "status": "FAILED",
            "error": str(e)
        }


def normalize(job_id, country_code, country_data, weather_data, holidays_data, start_date, end_date) -> dict:
    # Datos básicos del país
    name = country_data.get("name", {}).get("common", country_code)
    capital = country_data.get("capital", ["N/A"])[0] if country_data.get("capital") else "N/A"
    region = country_data.get("region", "N/A")

    currencies = country_data.get("currencies", {})
    currency = list(currencies.keys())[0] if currencies else "N/A"

    languages = country_data.get("languages", {})
    language_list = list(languages.values())

    population = country_data.get("population", 0)
    latlng = country_data.get("latlng", [0, 0])

    # Resumen del clima
    daily = weather_data.get("daily", {})
    temps_max = [t for t in daily.get("temperature_2m_max", []) if t is not None]
    temps_min = [t for t in daily.get("temperature_2m_min", []) if t is not None]
    precip = [p for p in daily.get("precipitation_sum", []) if p is not None]

    weather_summary = {
        "avg_temperature_max": round(sum(temps_max) / len(temps_max), 2) if temps_max else None,
        "avg_temperature_min": round(sum(temps_min) / len(temps_min), 2) if temps_min else None,
        "total_precipitation": round(sum(precip), 2) if precip else None
    }

    # Festivos en el rango de fechas
    holidays_in_range = [
        h for h in holidays_data
        if start_date <= h.get("date", "") <= end_date
    ]

    return {
        "job_id": job_id,
        "country_code": country_code,
        "country_name": name,
        "capital": capital,
        "region": region,
        "currency": currency,
        "languages": language_list,
        "population": population,
        "coordinates": {"lat": latlng[0], "lon": latlng[1]},
        "date_range": {"start_date": start_date, "end_date": end_date},
        "weather_summary": weather_summary,
        "holidays_in_range": holidays_in_range,
        "status": "PROCESSED"
    }


def lambda_handler(event: dict, context) -> dict:
    return process(event)