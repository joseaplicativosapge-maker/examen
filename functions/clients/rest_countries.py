import requests
from utils.logger import get_logger


def fetch(country_code: str, job_id: str) -> dict:
    log = get_logger(job_id, country_code)
    url = f"https://restcountries.com/v3.1/alpha/{country_code}"
    
    log(f"Consultando REST Countries", url=url)
    
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    
    data = response.json()
    if isinstance(data, list):
        data = data[0]
    
    log("REST Countries OK")
    return data