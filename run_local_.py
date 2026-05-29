import json
import os
import sys
import concurrent.futures
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# ✅ Solo poner defaults si no están en el .env
os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("S3_BUCKET", "local-output")


# Patch ANTES de cualquier import del proyecto
import utils.s3_helper as s3_module

def save_json_local(key: str, data: dict) -> str:
    path = Path("local-output") / key
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return str(path)

def save_bytes_local(key: str, data: bytes, content_type: str = "application/pdf") -> str:
    path = Path("local-output") / key
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    return str(path)

def get_json_local(key: str) -> dict:
    path = Path("local-output") / key
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

s3_module.save_json = save_json_local
s3_module.save_bytes = save_bytes_local
s3_module.get_json = get_json_local

# Ahora sí importar el resto
from functions.handler import validate
from functions.process_country import process
from functions.consolidate import consolidate


def run_pipeline(payload_path: str):
    with open(payload_path, "r") as f:
        body = json.load(f)

    print(f"\n{'='*50}")
    print(f"🚀 Iniciando pipeline: {body['job_id']}")
    print(f"{'='*50}")

    error = validate(body)
    if error:
        print(f"\n❌ Validación fallida (HTTP 400): {error}")
        return

    print(f"✅ Payload válido")

    job_id = body["job_id"]
    countries = body["countries"]

    save_json_local(f"bronze/jobs/{job_id}/request_payload.json", body)
    print(f"✅ Bronze: request_payload.json guardado")

    print(f"\n📡 Fan-out: procesando {len(countries)} países en paralelo...")
    results = []

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

    print(f"\n🔄 Fan-in: consolidando resultados...")
    report = consolidate({
        "job_id": job_id,
        "results": results
    })

    print(f"\n{'='*50}")
    print(f"✅ Pipeline completado")
    print(f"   Status    : {report['status']}")
    print(f"   Procesados: {report['summary']['countries_processed']}")
    print(f"   Fallidos  : {report['summary']['countries_failed']}")
    print(f"\n📁 Archivos en: local-output/")
    print(f"   bronze/jobs/{job_id}/request_payload.json")
    print(f"   silver/jobs/{job_id}/countries/<code>/country_summary.json")
    print(f"   golden/jobs/{job_id}/report.json")
    print(f"   golden/jobs/{job_id}/report.pdf")
    print(f"   golden/jobs/{job_id}/notification_payload.json")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    payload = sys.argv[1] if len(sys.argv) > 1 else "payloads/happy_path.json"
    run_pipeline(payload)