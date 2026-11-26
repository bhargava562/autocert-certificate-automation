"""
Autocert Certificate Automation Backend API
Provides endpoints for:
- Concurrent batch certificate generation from image (PNG/JPG) or PDF templates.
- Bulk participant data mapping (JSON, CSV, XLSX).
- Rate-limited distinct certificate email dispatch via Gmail/SMTP.
- Preview, health check, and single/batch email management.
"""

import os
import io
import time
import json
import uuid
import smtplib
from email.message import EmailMessage
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor

import re
import fitz  # PyMuPDF
import jinja2
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, status, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from .core.config import load_settings, Settings
from .services.models import TemplateManifest, FieldConfig
from .services.text_fitting import TextFittingService
from .services.engines.image_engine import PillowImageEngine
from .services.template_scanner import scan_template_placeholders
from .services.dataset_parser import load_dataset

app = FastAPI(
    title="Autocert Certificate Automation API",
    description="Backend API for high-throughput personalized batch certificate generation & SMTP delivery",
    version="1.1.0"
)

# Enable CORS from environment configuration (backend/.env -> CORS_ORIGINS)
_startup_settings = load_settings()
_cors_origins = list(_startup_settings.cors_origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials="*" not in _cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directory configurations
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTPUT_DIR = os.path.join(BASE_DIR, "sample_templates", "output")
EMAIL_TEMPLATE_PATH = os.path.join(BASE_DIR, "sample_templates", "sample_email_template.html")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def build_default_manifest(filename: str, output_format: str = "png") -> TemplateManifest:
    """Builds a proportional layout manifest matching template characteristics."""
    fn_lower = filename.lower()
    normalized_format = "pdf" if output_format.lower() == "pdf" else "png"

    if any(k in fn_lower for k in ("white", "green", "completion", "geometric")):
        return TemplateManifest(
            template_id="white_green_completion",
            template_filename=filename,
            default_format=normalized_format,
            base_width=2000,
            base_height=1414,
            fields={
                "full_name": FieldConfig(
                    name="full_name",
                    x_pct=0.50,
                    y_pct=0.438,
                    max_w_pct=0.65,
                    font_family="script",
                    font_size_pct=0.068,
                    min_font_size_pct=0.022,
                    align="center",
                    color="#1A5C47",
                    clear_area=(0.15, 0.385, 0.85, 0.4855),
                    clear_bg_color="#F9F9F9",
                ),
            }
        )
    elif "internship" in fn_lower or "red" in fn_lower:
        return TemplateManifest(
            template_id="red_gold_internship",
            template_filename=filename,
            default_format=normalized_format,
            base_width=2000,
            base_height=1414,
            fields={
                "full_name": FieldConfig(
                    name="full_name",
                    x_pct=0.50,
                    y_pct=0.395,
                    max_w_pct=0.60,
                    font_family="script",
                    font_size_pct=0.062,
                    min_font_size_pct=0.018,
                    align="center",
                    color="#2D2D2D",
                    clear_area=(0.20, 0.35, 0.80, 0.44),
                    clear_bg_color="#FFFFFF"
                ),
            }
        )
    else:
        # Default participation certificate manifest (RMK / GDG Study Jam template)
        return TemplateManifest(
            template_id="rmk_participation",
            template_filename=filename,
            default_format=normalized_format,
            base_width=2000,
            base_height=1414,
            fields={
                "full_name": FieldConfig(
                    name="full_name",
                    x_pct=0.470,
                    y_pct=0.592,
                    max_w_pct=0.20,
                    font_family="sans-serif",
                    font_size_pct=0.024,
                    min_font_size_pct=0.012,
                    align="center",
                    color="#0f172a",
                    clear_area=(0.420, 0.550, 0.535, 0.635),
                    clear_bg_color="transparent",
                ),
                "year": FieldConfig(
                    name="year",
                    x_pct=0.630,
                    y_pct=0.592,
                    max_w_pct=0.07,
                    font_family="sans-serif",
                    font_size_pct=0.024,
                    min_font_size_pct=0.012,
                    align="center",
                    color="#0f172a",
                    clear_area=(0.595, 0.550, 0.672, 0.635),
                    clear_bg_color="transparent",
                ),
                "department": FieldConfig(
                    name="department",
                    x_pct=0.758,
                    y_pct=0.592,
                    max_w_pct=0.08,
                    font_family="sans-serif",
                    font_size_pct=0.024,
                    min_font_size_pct=0.012,
                    align="center",
                    color="#0f172a",
                    clear_area=(0.715, 0.550, 0.800, 0.635),
                    clear_bg_color="transparent",
                ),
            }
        )


def normalize_record(p: Dict[str, Any]) -> Dict[str, Any]:
    """Normalizes participant fields. Empty optional fields remain empty and are not drawn over pre-printed template text."""
    full_name = p.get("full_name") or p.get("recipient_name") or p.get("name") or ""
    achievement_text = p.get("achievement_text") or p.get("description") or ""

    return {
        "full_name": full_name.strip(),
        "certificate_id": str(p.get("certificate_id") or "").strip(),
        "email": str(p.get("email") or p.get("email_address") or p.get("mail") or "").strip(),
        "year": str(p.get("year") or p.get("academic_year") or p.get("batch_year") or p.get("class") or "").strip(),
        "department": str(p.get("department") or p.get("dept") or p.get("branch") or p.get("stream") or "").strip(),
        "achievement_title": str(p.get("achievement_title") or p.get("role") or "").strip(),
        "achievement_text": achievement_text.strip() if achievement_text else "",
        "event_name": str(p.get("event_name") or p.get("achievement_title") or "").strip(),
        "issue_date": str(p.get("issue_date") or p.get("participated_date") or "").strip(),
        "signer_name": str(p.get("signer_name") or "").strip(),
        "signer_title": str(p.get("signer_title") or "").strip(),
        "organization": str(p.get("organization_on_certificate") or p.get("organization") or "").strip(),
    }


def convert_pdf_to_image_bytes(pdf_bytes: bytes, dpi: int = 150) -> bytes:
    """Converts the first page of a vector PDF template into high-res PNG image bytes, redacting any template placeholders."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    if doc.page_count == 0:
        raise ValueError("Uploaded PDF template has no pages.")
    page = doc[0]

    # Defensively erase any curly-bracket placeholders like {{name}}, {{work}}, {{date}}
    page_text = page.get_text()
    found_tags = set(re.findall(r"\{\{([^}]+)\}\}", page_text))
    for tag in found_tags:
        occurrences = page.search_for(f"{{{{{tag}}}}}")
        for occ in occurrences:
            r_exp = fitz.Rect(occ.x0 - 2, occ.y0 - 2, occ.x1 + 2, occ.y1 + 2)
            page.add_redact_annot(r_exp, fill=(249 / 255.0, 249 / 255.0, 249 / 255.0))
    if found_tags:
        page.apply_redactions()

    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img_bytes = pix.tobytes("png")
    doc.close()
    return img_bytes


def render_single_certificate(
    item: Dict[str, Any],
    image_bytes: bytes,
    manifest: TemplateManifest,
    engine: PillowImageEngine,
    output_dir: str
) -> Dict[str, Any]:
    """Renders an individual certificate safely."""
    try:
        render_res = engine.render(
            template_bytes=image_bytes,
            fields=item,
            manifest=manifest
        )
        out_filename = render_res.filename
        out_path = os.path.join(output_dir, out_filename)
        with open(out_path, "wb") as f:
            f.write(render_res.content)

        return {
            "certificate_id": item["certificate_id"],
            "participant_name": item["full_name"],
            "email": item.get("email", ""),
            "status": "Generated",
            "filename": out_filename,
            "preview_url": f"/api/certificates/download/{out_filename}",
            "file_path": out_path,
            "item_data": item,
        }
    except Exception as err:
        return {
            "certificate_id": item["certificate_id"],
            "participant_name": item["full_name"],
            "email": item.get("email", ""),
            "status": "Failed",
            "filename": "",
            "preview_url": "",
            "error": str(err),
            "file_path": "",
            "item_data": item,
        }


def dispatch_single_email_smtp(
    server: smtplib.SMTP,
    sender_email: str,
    sender_name: str,
    recipient_email: str,
    participant: Dict[str, Any],
    pdf_path: str,
    subject: Optional[str] = None,
    jinja_tmpl: Optional[jinja2.Template] = None
) -> Dict[str, Any]:
    """Dispatches a distinct certificate email via an active SMTP connection."""
    try:
        full_name = participant.get("full_name", "Recipient")
        cert_id = participant.get("certificate_id", "")
        event_name = participant.get("event_name", "Certificate of Achievement")

        with open(pdf_path, "rb") as f:
            attachment_bytes = f.read()
        attachment_filename = os.path.basename(pdf_path)

        # HTML body
        if jinja_tmpl:
            html_body = jinja_tmpl.render(**participant)
        else:
            html_body = f"<p>Dear {full_name},</p><p>Congratulations! Your certificate is attached.</p>"

        # Construct email message
        msg = EmailMessage()
        msg["Subject"] = subject or f"Your Certificate of Achievement - {event_name}"
        msg["From"] = f"{sender_name} <{sender_email}>"
        msg["To"] = recipient_email

        msg.set_content(
            f"Dear {full_name},\n\n"
            f"Congratulations on receiving your certificate for {event_name}.\n"
            f"Please find your certificate attached.\n\n"
            f"Certificate ID: {cert_id}\n"
        )
        msg.add_alternative(html_body, subtype="html")

        # Detect attachment subtype
        ext = attachment_filename.lower().split(".")[-1]
        subtype = "pdf" if ext == "pdf" else "png"
        msg.add_attachment(
            attachment_bytes,
            maintype="application" if subtype == "pdf" else "image",
            subtype=subtype,
            filename=attachment_filename
        )

        server.send_message(msg)
        return {"status": "Sent", "error": None}
    except Exception as e:
        return {"status": "Failed", "error": str(e)}


@app.get("/")
@app.get("/api/health")
def health_check():
    settings = load_settings()
    smtp_configured = bool(settings.smtp_user and settings.smtp_password)
    return {
        "status": "healthy",
        "service": "autocert-certificate-automation",
        "version": "1.1.0",
        "smtp_configured": smtp_configured,
        "smtp_from_email": settings.smtp_from_email,
        "smtp_from_name": settings.smtp_from_name
    }


@app.post("/api/dataset/parse")
async def parse_dataset_file(file: UploadFile = File(...)):
    """
    Parses an uploaded participant dataset file (.xlsx, .xls, .csv, .tsv, .json)
    and returns detected columns, row count, and parsed records.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file has no filename.")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded dataset file is empty.")
    try:
        records = load_dataset(content_bytes=content, filename=file.filename)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse dataset: {str(e)}")

    if not records:
        raise HTTPException(status_code=400, detail="The uploaded dataset contains no valid data rows.")

    columns = list(records[0].keys()) if records else []
    return {
        "ok": True,
        "filename": file.filename,
        "total_records": len(records),
        "columns": columns,
        "records": records,
    }


@app.post("/api/certificates/generate")
@app.post("/certificate/batches/generate")
async def generate_certificates(
    template: UploadFile = File(...),
    participants: Optional[str] = Form(None),
    dataset: Optional[UploadFile] = File(None),
    format: str = Form("png"),
    send_emails: bool = Form(False),
    email_subject: Optional[str] = Form(None)
):
    """
    Generates batch certificates from uploaded Image (PNG/JPG) or PDF template
    and mapped participants JSON or dataset spreadsheet (.xlsx, .xls, .csv).
    Uses concurrent thread workers for high speed.
    Optionally dispatches distinct emails with attachments.
    """
    # 1. Validate template format
    filename = template.filename or "template.png"
    ext = filename.lower().split(".")[-1]
    if ext not in ("png", "jpg", "jpeg", "pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported template format '.{ext}'. Please upload a PNG, JPG, or PDF file."
        )

    template_bytes = await template.read()
    if not template_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded template file is empty."
        )

    # 2. Normalize template bytes to renderable image bytes
    if ext == "pdf":
        try:
            image_template_bytes = convert_pdf_to_image_bytes(template_bytes, dpi=200)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not parse PDF template: {str(e)}"
            )
    else:
        image_template_bytes = template_bytes

    # 3. Parse participant data from uploaded spreadsheet file OR form JSON string
    raw_participants = []
    if dataset is not None and dataset.filename:
        dataset_bytes = await dataset.read()
        if dataset_bytes:
            try:
                raw_participants = load_dataset(content_bytes=dataset_bytes, filename=dataset.filename)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to parse uploaded dataset spreadsheet '{dataset.filename}': {str(e)}"
                )

    if not raw_participants and participants:
        try:
            raw_participants = json.loads(participants)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid participant JSON data: {str(e)}"
            )

    if not raw_participants:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide participant data via 'participants' JSON or upload a 'dataset' spreadsheet (.xlsx, .xls, .csv)."
        )

    if not isinstance(raw_participants, list) or len(raw_participants) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Participant dataset must be a non-empty list of records."
        )

    # 4. Normalize records and validate essential fields
    normalized_list = []
    for idx, raw_p in enumerate(raw_participants, start=1):
        norm = normalize_record(raw_p)
        if not norm["full_name"]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Record #{idx} is missing required recipient name."
            )
        if not norm["certificate_id"]:
            norm["certificate_id"] = f"CERT-{idx:04d}"
        normalized_list.append(norm)

    # 5. Build manifest & initialize rendering engine by scanning template for exact text placeholders
    manifest = scan_template_placeholders(
        template_bytes=template_bytes,
        filename=filename,
        default_format=format
    )
    text_service = TextFittingService()
    engine = PillowImageEngine(text_service)

    # Clean output folder before generating new batch to eliminate stale artifacts
    for f in os.listdir(OUTPUT_DIR):
        fp = os.path.join(OUTPUT_DIR, f)
        if os.path.isfile(fp):
            try:
                os.remove(fp)
            except Exception:
                pass

    # 6. Concurrency: Multi-threaded parallel certificate rendering
    batch_id = f"batch_{uuid.uuid4().hex[:8]}"
    max_workers = min(16, (os.cpu_count() or 1) + 4)

    def _render_task(item):
        return render_single_certificate(
            item=item,
            image_bytes=image_template_bytes,
            manifest=manifest,
            engine=engine,
            output_dir=OUTPUT_DIR
        )

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        generated_results = list(executor.map(_render_task, normalized_list))

    # 7. Optional: Bulk Email Dispatch (Paced & Error-Isolated)
    emails_dispatched = 0
    emails_failed = 0

    if send_emails:
        settings = load_settings()
        clean_pwd = (settings.smtp_password or "").replace(" ", "").strip()
        if not settings.smtp_user or not clean_pwd:
            for r in generated_results:
                r["email_status"] = "Failed: SMTP credentials not configured in backend .env"
        else:
            # Load HTML email template
            jinja_tmpl = None
            if os.path.exists(EMAIL_TEMPLATE_PATH):
                with open(EMAIL_TEMPLATE_PATH, "r", encoding="utf-8") as f:
                    jinja_tmpl = jinja2.Template(f.read())

            try:
                with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
                    server.login(settings.smtp_user, clean_pwd)

                    for r in generated_results:
                        if r["status"] != "Generated" or not r.get("email"):
                            r["email_status"] = "Skipped (no valid email or generation failed)"
                            continue

                        disp_res = dispatch_single_email_smtp(
                            server=server,
                            sender_email=settings.smtp_user,
                            sender_name=settings.smtp_from_name,
                            recipient_email=r["email"],
                            participant=r["item_data"],
                            pdf_path=r["file_path"],
                            subject=email_subject,
                            jinja_tmpl=jinja_tmpl
                        )

                        r["email_status"] = disp_res["status"]
                        if disp_res["status"] == "Sent":
                            emails_dispatched += 1
                        else:
                            emails_failed += 1
                            r["email_error"] = disp_res["error"]

                        # Pacing to protect against Gmail spam throttle
                        time.sleep(0.15)
            except Exception as smtp_err:
                for r in generated_results:
                    if "email_status" not in r:
                        r["email_status"] = f"Failed: {str(smtp_err)}"
                        emails_failed += 1
    else:
        for r in generated_results:
            r["email_status"] = "Not Sent"

    # Clean up internal fields from client response
    for r in generated_results:
        r.pop("file_path", None)
        r.pop("item_data", None)

    return {
        "success": True,
        "batch_id": batch_id,
        "total_count": len(normalized_list),
        "generated_count": sum(1 for r in generated_results if r["status"] == "Generated"),
        "emails_sent_count": emails_dispatched,
        "emails_failed_count": emails_failed,
        "certificates": generated_results
    }


class SendBatchEmailsRequest(BaseModel):
    filenames: List[str]
    recipients: List[Dict[str, Any]]
    subject: Optional[str] = None


@app.post("/api/certificates/send-batch-emails")
async def send_batch_emails(req: SendBatchEmailsRequest):
    """Dispatches emails for previously generated certificates with pacing & error isolation."""
    settings = load_settings()
    clean_pwd = (settings.smtp_password or "").replace(" ", "").strip()
    if not settings.smtp_user or not clean_pwd:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SMTP credentials not configured in backend environment."
        )

    jinja_tmpl = None
    if os.path.exists(EMAIL_TEMPLATE_PATH):
        with open(EMAIL_TEMPLATE_PATH, "r", encoding="utf-8") as f:
            jinja_tmpl = jinja2.Template(f.read())

    results = []
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(settings.smtp_user, clean_pwd)

            for item in req.recipients:
                email = item.get("email")
                filename = item.get("filename")
                if not email or not filename:
                    results.append({"email": email, "status": "Failed", "error": "Missing email or filename"})
                    continue

                file_path = os.path.join(OUTPUT_DIR, os.path.basename(filename))
                if not os.path.exists(file_path):
                    results.append({"email": email, "status": "Failed", "error": f"File '{filename}' not found"})
                    continue

                disp_res = dispatch_single_email_smtp(
                    server=server,
                    sender_email=settings.smtp_user,
                    sender_name=settings.smtp_from_name,
                    recipient_email=email,
                    participant=item,
                    pdf_path=file_path,
                    subject=req.subject,
                    jinja_tmpl=jinja_tmpl
                )
                results.append({"email": email, "status": disp_res["status"], "error": disp_res.get("error")})
                time.sleep(0.15)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"SMTP Connection Error: {str(e)}"
        )

    return {"success": True, "results": results}


class SendSingleEmailRequest(BaseModel):
    filename: str
    email: str
    full_name: str
    certificate_id: str
    achievement_title: Optional[str] = ""
    event_name: Optional[str] = "Certificate of Achievement"
    issue_date: Optional[str] = ""
    subject: Optional[str] = None


@app.post("/api/certificates/send-single-email")
async def send_single_email(req: SendSingleEmailRequest):
    """Sends a certificate to an individual recipient."""
    settings = load_settings()
    clean_pwd = (settings.smtp_password or "").replace(" ", "").strip()
    if not settings.smtp_user or not clean_pwd:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SMTP credentials not configured."
        )

    file_path = os.path.join(OUTPUT_DIR, os.path.basename(req.filename))
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate file '{req.filename}' not found."
        )

    jinja_tmpl = None
    if os.path.exists(EMAIL_TEMPLATE_PATH):
        with open(EMAIL_TEMPLATE_PATH, "r", encoding="utf-8") as f:
            jinja_tmpl = jinja2.Template(f.read())

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(settings.smtp_user, clean_pwd)

            disp_res = dispatch_single_email_smtp(
                server=server,
                sender_email=settings.smtp_user,
                sender_name=settings.smtp_from_name,
                recipient_email=req.email,
                participant=req.model_dump(),
                pdf_path=file_path,
                subject=req.subject,
                jinja_tmpl=jinja_tmpl
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"SMTP Error: {str(e)}"
        )

    if disp_res["status"] != "Sent":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=disp_res.get("error", "Email dispatch failed")
        )

    return {"success": True, "message": f"Email successfully sent to {req.email}"}


@app.post("/api/certificates/test-smtp")
def test_smtp_connection():
    """Validates SMTP server reachability and authentication."""
    settings = load_settings()
    clean_pwd = (settings.smtp_password or "").replace(" ", "").strip()
    if not settings.smtp_user or not clean_pwd:
        return {
            "ok": False,
            "error": "SMTP_USER or SMTP_PASSWORD is not set in backend .env"
        }

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(settings.smtp_user, clean_pwd)
        return {
            "ok": True,
            "message": f"Successfully connected and authenticated with {settings.smtp_host}:{settings.smtp_port} as {settings.smtp_user}"
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/certificates/download/{filename}")
def download_certificate(filename: str):
    """Serves generated certificate PNG or PDF directly."""
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(OUTPUT_DIR, safe_filename)

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate file '{safe_filename}' not found."
        )

    ext = safe_filename.lower().split(".")[-1]
    media_type = "application/pdf" if ext == "pdf" else "image/png"

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=safe_filename
    )
