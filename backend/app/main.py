"""
Autocert Certificate Automation Backend API
Exposes endpoints for certificate generation, health status, and preview/download.
"""

import os
import io
import json
import uuid
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from .core.config import load_settings
from .services.models import TemplateManifest, FieldConfig
from .services.text_fitting import TextFittingService
from .services.engines.image_engine import PillowImageEngine
from .services.engines.pdf_engine import PyMuPdfEngine

app = FastAPI(
    title="Autocert Certificate Automation API",
    description="Backend API for personalized batch certificate generation",
    version="1.0.0"
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Output directory for rendered certificates
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTPUT_DIR = os.path.join(BASE_DIR, "sample_templates", "output")
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
                "achievement_text": FieldConfig(
                    name="achievement_text",
                    x_pct=0.50,
                    y_pct=0.575,
                    max_w_pct=0.70,
                    font_family="serif",
                    font_size_pct=0.028,
                    min_font_size_pct=0.014,
                    align="center",
                    color="#2D2D2D",
                    line_spacing=1.45,
                    clear_area=(0.15, 0.492, 0.85, 0.635),
                    clear_bg_color="#F9F9F9",
                ),
                "issue_date": FieldConfig(
                    name="issue_date",
                    x_pct=0.50,
                    y_pct=0.678,
                    max_w_pct=0.40,
                    font_family="sans-serif",
                    font_size_pct=0.024,
                    min_font_size_pct=0.013,
                    align="center",
                    color="#444444",
                    clear_area=(0.25, 0.640, 0.75, 0.715),
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
                "achievement_title": FieldConfig(
                    name="achievement_title",
                    x_pct=0.50,
                    y_pct=0.542,
                    max_w_pct=0.65,
                    font_family="sans-serif",
                    font_size_pct=0.034,
                    min_font_size_pct=0.015,
                    align="center",
                    color="#333333",
                    clear_area=(0.20, 0.51, 0.80, 0.57),
                    clear_bg_color="#FFFFFF"
                ),
                "issue_date": FieldConfig(
                    name="issue_date",
                    x_pct=0.50,
                    y_pct=0.640,
                    max_w_pct=0.50,
                    font_family="sans-serif",
                    font_size_pct=0.030,
                    min_font_size_pct=0.015,
                    align="center",
                    color="#444444",
                    clear_area=(0.25, 0.618, 0.75, 0.670),
                    clear_bg_color="#FFFFFF"
                ),
            }
        )
    else:
        # Generic elegant template manifest with dynamic text fitting
        return TemplateManifest(
            template_id="generic_certificate",
            template_filename=filename,
            default_format=normalized_format,
            base_width=2000,
            base_height=1414,
            fields={
                "full_name": FieldConfig(
                    name="full_name",
                    x_pct=0.50,
                    y_pct=0.450,
                    max_w_pct=0.70,
                    font_family="script",
                    font_size_pct=0.065,
                    min_font_size_pct=0.020,
                    align="center",
                    color="#1A5C47",
                    clear_area=(0.15, 0.385, 0.85, 0.4855),
                    clear_bg_color="auto",
                ),
                "achievement_text": FieldConfig(
                    name="achievement_text",
                    x_pct=0.50,
                    y_pct=0.580,
                    max_w_pct=0.72,
                    font_family="serif",
                    font_size_pct=0.028,
                    min_font_size_pct=0.014,
                    align="center",
                    color="#2D2D2D",
                    line_spacing=1.45,
                    clear_area=(0.15, 0.495, 0.85, 0.635),
                    clear_bg_color="auto",
                ),
                "issue_date": FieldConfig(
                    name="issue_date",
                    x_pct=0.50,
                    y_pct=0.680,
                    max_w_pct=0.45,
                    font_family="sans-serif",
                    font_size_pct=0.024,
                    min_font_size_pct=0.013,
                    align="center",
                    color="#444444",
                    clear_area=(0.25, 0.640, 0.75, 0.715),
                    clear_bg_color="auto",
                ),
            }
        )


def normalize_record(p: Dict[str, Any]) -> Dict[str, Any]:
    """Normalizes participant fields and builds dynamic achievement text if missing."""
    full_name = p.get("full_name") or p.get("recipient_name") or p.get("name") or ""
    achievement_text = p.get("achievement_text") or ""
    if not achievement_text:
        pronoun = "her" if str(p.get("gender", "")).lower() == "female" else "his"
        event = p.get("event_name") or p.get("achievement_title") or ""
        date_str = p.get("participated_date") or p.get("issue_date") or ""
        org = p.get("organization_on_certificate") or p.get("organization") or ""
        if event:
            achievement_text = (
                f"In appreciation of {pronoun} exceptional achievements and contributions "
                f"in {event}, which have greatly enhanced the values of {org} on {date_str}."
            )

    return {
        "full_name": full_name.strip(),
        "certificate_id": str(p.get("certificate_id") or "").strip(),
        "email": str(p.get("email") or "").strip(),
        "achievement_title": str(p.get("achievement_title") or p.get("role") or "").strip(),
        "achievement_text": achievement_text.strip(),
        "issue_date": str(p.get("issue_date") or p.get("participated_date") or "").strip(),
        "signer_name": str(p.get("signer_name") or "").strip(),
        "signer_title": str(p.get("signer_title") or "").strip(),
        "organization_on_certificate": str(p.get("organization_on_certificate") or "").strip(),
    }


@app.get("/")
@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "autocert-certificate-automation",
        "version": "1.0.0"
    }


@app.post("/api/certificates/generate")
@app.post("/certificate/batches/generate")
async def generate_certificates(
    template: UploadFile = File(...),
    participants: str = Form(...),
    format: str = Form("png")
):
    """
    Generates batch certificates from the uploaded PNG template and mapped participants JSON.
    """
    # 1. Validate template
    filename = template.filename or "template.png"
    ext = filename.lower().split(".")[-1]
    if ext not in ("png", "jpg", "jpeg"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported template format '.{ext}'. Please upload a PNG image template."
        )

    template_bytes = await template.read()
    if not template_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded template file is empty."
        )

    # 2. Parse participant JSON
    try:
        raw_participants = json.loads(participants)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid participant JSON data: {str(e)}"
        )

    if not isinstance(raw_participants, list) or len(raw_participants) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Participant dataset must be a non-empty list of records."
        )

    # 3. Normalize records and validate essential fields
    normalized_list = []
    for idx, raw_p in enumerate(raw_participants, start=1):
        norm = normalize_record(raw_p)
        if not norm["full_name"]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Record #{idx} is missing required recipient name."
            )
        if not norm["certificate_id"]:
            # Auto-assign certificate ID if missing
            norm["certificate_id"] = f"CERT-{idx:04d}"
        normalized_list.append(norm)

    # 4. Build manifest & initialize rendering engine
    manifest = build_default_manifest(filename, output_format=format)
    text_service = TextFittingService()
    engine = PillowImageEngine(text_service)

    # 5. Render batch certificates
    batch_id = f"batch_{uuid.uuid4().hex[:8]}"
    generated_results = []

    for item in normalized_list:
        try:
            render_res = engine.render(
                template_bytes=template_bytes,
                fields=item,
                manifest=manifest
            )

            # Persist to output folder
            out_filename = render_res.filename
            out_path = os.path.join(OUTPUT_DIR, out_filename)
            with open(out_path, "wb") as f:
                f.write(render_res.content)

            generated_results.append({
                "certificate_id": item["certificate_id"],
                "participant_name": item["full_name"],
                "email": item.get("email", ""),
                "status": "Generated",
                "filename": out_filename,
                "preview_url": f"/api/certificates/download/{out_filename}"
            })
        except Exception as err:
            generated_results.append({
                "certificate_id": item["certificate_id"],
                "participant_name": item["full_name"],
                "email": item.get("email", ""),
                "status": "Failed",
                "filename": "",
                "error": str(err)
            })

    return {
        "success": True,
        "batch_id": batch_id,
        "total_count": len(normalized_list),
        "generated_count": sum(1 for r in generated_results if r["status"] == "Generated"),
        "certificates": generated_results
    }


@app.get("/api/certificates/download/{filename}")
def download_certificate(filename: str):
    """Serves generated certificate PNG directly."""
    # Prevent directory traversal
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(OUTPUT_DIR, safe_filename)

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate file '{safe_filename}' not found."
        )

    return FileResponse(
        path=file_path,
        media_type="image/png",
        filename=safe_filename
    )
