from fpdf import FPDF
from datetime import datetime


def generate_pdf(report: dict) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # ── TÍTULO ─────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 12, "Country Intelligence Report", ln=True, align="C")

    pdf.set_font("Helvetica", size=11)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 8, f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC", ln=True, align="C")
    pdf.ln(6)

    # ── RESUMEN GENERAL ────────────────────────────────────
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 10, "General Summary", ln=True)
    pdf.set_draw_color(200, 200, 200)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)

    summary = report.get("summary", {})
    pdf.set_font("Helvetica", size=11)
    pdf.set_text_color(50, 50, 50)

    items = [
        ("Job ID", report.get("job_id", "N/A")),
        ("Status", report.get("status", "N/A")),
        ("Countries Requested", str(summary.get("countries_requested", 0))),
        ("Countries Processed", str(summary.get("countries_processed", 0))),
        ("Countries Failed", str(summary.get("countries_failed", 0))),
    ]

    for label, value in items:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(70, 8, f"{label}:", ln=False)
        pdf.set_font("Helvetica", size=11)
        pdf.cell(0, 8, value, ln=True)

    pdf.ln(6)

    # ── SECCIÓN POR PAÍS ───────────────────────────────────
    for country in report.get("countries", []):
        if country.get("status") == "FAILED":
            continue

        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(30, 30, 30)
        pdf.cell(0, 10, f"{country.get('country_name', 'N/A')} ({country.get('country_code', '')})", ln=True)
        pdf.set_draw_color(200, 200, 200)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(3)

        pdf.set_font("Helvetica", size=11)
        pdf.set_text_color(50, 50, 50)

        weather = country.get("weather_summary", {})
        date_range = country.get("date_range", {})
        holidays = country.get("holidays_in_range", [])

        country_items = [
            ("Capital", country.get("capital", "N/A")),
            ("Region", country.get("region", "N/A")),
            ("Currency", country.get("currency", "N/A")),
            ("Population", f"{country.get('population', 0):,}"),
            ("Date Range", f"{date_range.get('start_date')} to {date_range.get('end_date')}"),
            ("Avg Temp Max", f"{weather.get('avg_temperature_max', 'N/A')} C"),
            ("Avg Temp Min", f"{weather.get('avg_temperature_min', 'N/A')} C"),
            ("Total Precipitation", f"{weather.get('total_precipitation', 'N/A')} mm"),
            ("Holidays in Range", str(len(holidays))),
        ]

        for label, value in country_items:
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(70, 7, f"{label}:", ln=False)
            pdf.set_font("Helvetica", size=11)
            pdf.cell(0, 7, str(value), ln=True)

        if holidays:
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(0, 7, "Holidays:", ln=True)
            for h in holidays:
                pdf.set_font("Helvetica", size=10)
                pdf.cell(0, 6, f"  - {h.get('date')} | {h.get('name', 'N/A')}", ln=True)

        pdf.ln(5)

    # ── PAÍSES FALLIDOS ────────────────────────────────────
    failed = report.get("failed_countries", [])
    if failed:
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(180, 0, 0)
        pdf.cell(0, 10, "Failed Countries", ln=True)
        pdf.set_draw_color(200, 200, 200)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(3)

        for f in failed:
            pdf.set_font("Helvetica", size=11)
            pdf.set_text_color(50, 50, 50)
            pdf.cell(0, 7, f"  - {f.get('country_code')}: {f.get('error', 'Unknown error')}", ln=True)

    return bytes(pdf.output())