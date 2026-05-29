import json
import os
import sys
from pathlib import Path

# ── Configurar entorno local ───────────────────────────────
os.environ["S3_BUCKET"] = "country-pipeline-local"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["AWS_ACCESS_KEY_ID"] = "test"
os.environ["AWS_SECRET_ACCESS_KEY"] = "test"
os.environ["AWS_ENDPOINT_URL"] = "http://192.168.99.100:4566"

import boto3

# ── Crear bucket local en LocalStack ──────────────────────
def setup_bucket():
    s3 = boto3.client(
        "s3",
        endpoint_url="http://192.168.99.100:4566",
        region_name="us-east-1"
    )
    try:
        s3.create_bucket(Bucket="country-pipeline-local")
        print("✅ Bucket creado: country-pipeline-local")
    except Exception as e:
        if "BucketAlreadyOwnedByYou" in str(e):
            print("✅ Bucket ya existe")
        else:
            print(f"⚠️  Bucket error: {e}")

# ── Simular pipeline completo ──────────────────────────────
def run_pipeline(payload_path: str):
    from functions.handler import validate
    from functions.process_country import process
    from functions.consolidate import consolidate

    # Cargar payload
    with open(payload_path, "r") as f:
        body = json.load(f)

    print(f"\n{'='*50}")
    print(f"🚀 Iniciando pipeline: {body['job_id']}")
    print(f"{'='*50}")

    # Validar
    error = validate(body)
    if error:
        print(f"\n❌ Validación fallida (HTTP 400): {error}")
        return

    print(f"✅ Payload válido")

    job_id = body["job_id"]
    countries = body["countries"]

    # Guardar bronze
    from utils.s3_helper import save_json
    save_json(f"bronze/jobs/{job_id}/request_payload.json", body)
    print(f"✅ Bronze: request_payload.json guardado")

    # Fan-out: procesar países en paralelo
    print(f"\n📡 Fan-out: procesando {len(countries)} países...")
    results = []

    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(process, {
                "job_id": job_id,
                "country_code": c["country_code"],
                "date_range": c["date_range"]
            }): c["country_code"]
            for c in countries
        }

        for future in concurrent.futures.as_completed(futures):
            country_code = futures[future]
            try:
                result = future.result()
                status = result.get("status", "UNKNOWN")
                icon = "✅" if status == "PROCESSED" else "❌"
                print(f"  {icon} {country_code}: {status}")
                results.append(result)
            except Exception as e:
                print(f"  ❌ {country_code}: ERROR - {e}")
                results.append({
                    "job_id": job_id,
                    "country_code": country_code,
                    "status": "FAILED",
                    "error": str(e)
                })

    # Fan-in: consolidar
    print(f"\n🔄 Fan-in: consolidando resultados...")
    report = consolidate({
        "job_id": job_id,
        "results": results
    })

    print(f"\n{'='*50}")
    print(f"✅ Pipeline completado")
    print(f"   Status: {report['status']}")
    print(f"   Procesados: {report['summary']['countries_processed']}")
    print(f"   Fallidos:   {report['summary']['countries_failed']}")
    print(f"\n📁 Archivos generados en S3:")
    print(f"   bronze/jobs/{job_id}/request_payload.json")
    print(f"   silver/jobs/{job_id}/countries/<code>/country_summary.json")
    print(f"   golden/jobs/{job_id}/report.json")
    print(f"   golden/jobs/{job_id}/report.pdf")
    print(f"   golden/jobs/{job_id}/notification_payload.json")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    payload = sys.argv[1] if len(sys.argv) > 1 else "payloads/happy_path.json"

    print("🔧 Configurando bucket local...")
    setup_bucket()

    run_pipeline(payload)