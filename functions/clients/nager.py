import requests
from utils.logger import get_logger


def fetch(country_code: str, year: int, job_id: str) -> list:
    log = get_logger(job_id, country_code)
    url = f"https://date.nager.at/api/v3/PublicHolidays/{year}/{country_code}"
    
    log(f"Consultando Nager.Date", url=url)
    
    response = requests.get(url, timeout=10)
    
    if response.status_code == 404:
        log("Nager.Date: país no encontrado, retornando lista vacía", level="WARNING")
        return []
    
    response.raise_for_status()
    
    log("Nager.Date OK")
    return response.json()