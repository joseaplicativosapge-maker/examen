from datetime import datetime
from utils.logger import get_logger
from utils.s3_helper import save_json, save_bytes
from utils.pdf_generator import generate_pdf


def consolidate(event: dict) -> dict:
    job_id = event["job_id"]
    results = event["results"]

    log = get_logger(job_id)
    log("Iniciando consolidación fan-in")

    processed = [r for r in results if r.get("status") == "PROCESSED"]
    failed = [r for r in results if r.get("status") == "FAILED"]

    overall_status = "COMPLETED" if not failed else ("PARTIAL" if processed else "FAILED")

    report = {
        "job_id": job_id,
        "status": overall_status,
        "generated_at": datetime.utcnow().isoformat(),
        "summary": {
            "countries_requested": len(results),
            "countries_processed": len(processed),
            "countries_failed": len(failed)
        },
        "countries": results,
        "failed_countries": [
            {"country_code": f["country_code"], "error": f.get("error")}
            for f in failed
        ]
    }

    # ── Golden: report.json ────────────────────────────────
    save_json(f"golden/jobs/{job_id}/report.json", report)
    log("Golden: report.json guardado")

    # ── Golden: report.pdf ─────────────────────────────────
    pdf_bytes = generate_pdf(report)
    save_bytes(f"golden/jobs/{job_id}/report.pdf", pdf_bytes)
    log("Golden: report.pdf guardado")

    # ── Golden: notification_payload.json ──────────────────
    notification = {
        "job_id": job_id,
        "status": overall_status,
        "countries_processed": len(processed),
        "countries_failed": len(failed),
        "report_location": f"golden/jobs/{job_id}/report.json",
        "pdf_location": f"golden/jobs/{job_id}/report.pdf",
        "notified_at": datetime.utcnow().isoformat()
    }

    save_json(f"golden/jobs/{job_id}/notification_payload.json", notification)
    log("Golden: notification_payload.json guardado")

    log(f"Consolidación completa — status: {overall_status}")
    return report


def lambda_handler(event: dict, context) -> dict:
    return consolidate(event)