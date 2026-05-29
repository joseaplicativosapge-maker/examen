import requests
from utils.logger import get_logger


def fetch(lat: float, lon: float, start_date: str, end_date: str, job_id: str, country_code: str) -> dict:
    log = get_logger(job_id, country_code)
    url = "https://archive-api.open-meteo.com/v1/archive"
    
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
        "timezone": "auto"
    }
    
    log("Consultando Open-Meteo", url=url)
    
    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()
    
    log("Open-Meteo OK")
    return response.json()