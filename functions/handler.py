import json
import boto3
import os
from datetime import datetime
from utils.logger import get_logger
from utils.s3_helper import save_json


def lambda_handler(event: dict, context) -> dict:
    # ── Parsear body ───────────────────────────────────────
    try:
        if isinstance(event.get("body"), str):
            body = json.loads(event["body"])
        elif isinstance(event.get("body"), dict):
            body = event["body"]
        else:
            body = event
    except Exception:
        return response(400, {"error": "Body JSON inválido"})

    # ── Validar payload ────────────────────────────────────
    error = validate(body)
    if error:
        return response(400, {"error": error})

    job_id = body["job_id"]
    log = get_logger(job_id)
    log("Payload recibido y validado")

    # ── Bronze: guardar payload original ───────────────────
    save_json(f"bronze/jobs/{job_id}/request_payload.json", body)
    log("Bronze: request_payload.json guardado")

    # ── Iniciar Step Functions ─────────────────────────────
    sf_arn = os.environ.get("STATE_MACHINE_ARN")
    sf_client = boto3.client(
        "stepfunctions",
        endpoint_url=os.environ.get("AWS_ENDPOINT_URL", None),
        region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
    )

    execution = sf_client.start_execution(
        stateMachineArn=sf_arn,
        name=f"{job_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        input=json.dumps(body)
    )

    log("Step Functions iniciado", execution_arn=execution["executionArn"])

    return response(202, {
        "job_id": job_id,
        "status": "ACCEPTED",
        "execution_arn": execution["executionArn"],
        "message": "Pipeline iniciado correctamente"
    })


def validate(body: dict) -> str:
    if not body.get("job_id"):
        return "job_id es obligatorio"

    countries = body.get("countries", [])
    if not countries:
        return "countries es obligatorio y no puede estar vacío"

    if len(countries) > 5:
        return "Máximo 5 países permitidos"

    for c in countries:
        if not c.get("country_code"):
            return "country_code es obligatorio en cada país"

        date_range = c.get("date_range", {})
        start = date_range.get("start_date")
        end = date_range.get("end_date")

        if not start or not end:
            return f"date_range incompleto para {c.get('country_code')}"

        if start > end:
            return f"start_date no puede ser mayor que end_date en {c.get('country_code')}"

    if not body.get("report", {}).get("format"):
        return "report.format es obligatorio"

    return None


def response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body)
    }