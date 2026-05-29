import logging
import json

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_logger(job_id: str, country_code: str = None):
    def log(message: str, level: str = "INFO", **kwargs):
        entry = {
            "job_id": job_id,
            "message": message,
            **kwargs
        }
        if country_code:
            entry["country_code"] = country_code

        if level == "ERROR":
            logger.error(json.dumps(entry))
        elif level == "WARNING":
            logger.warning(json.dumps(entry))
        else:
            logger.info(json.dumps(entry))

    return log