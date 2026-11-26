"""
Comprehensive pytest suite for Autocert Certificate Automation Backend.

Covers:
1. Dataset parsing (.csv, .xlsx, .json) with banner rows, whitespace/newlines, missing values.
2. Placeholder extraction & style detection on PDF (sample cert 2.pdf & synthetic) and PNG templates.
3. POST /api/templates/inspect and POST /api/certificates/generate with dynamic field_mapping.
4. Binary-search font scaling (short vs long names) and overflow warning reporting.
5. Path-traversal protection on /api/certificates/download/...
6. Mocked SMTP email validation, transient retry, HTML escaping, and batch idempotency.
"""

import io
import json
import os
import smtplib
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import openpyxl
import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

# Ensure backend/ is on sys.path regardless of pytest invocation directory
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Detect whether PyMuPDF can be imported (Windows Application Control may block _mupdf.pyd)
try:
    import pymupdf  # noqa: F401
    HAS_PYMUPDF = True
except (ImportError, OSError):
    HAS_PYMUPDF = False

from app.services.dataset_parser import load_dataset
from app.services.models import FieldConfig, TemplateManifest
from app.services.text_fitting import TextFittingService
from app.services.engines.image_engine import PillowImageEngine


def _make_png_template(width: int = 1200, height: int = 850) -> bytes:
    """Creates a clean in-memory PNG certificate template."""
    img = Image.new("RGB", (width, height), color=(250, 248, 242))
    draw = ImageDraw.Draw(img)
    draw.rectangle([(30, 30), (width - 30, height - 30)], outline=(197, 160, 89), width=6)
    draw.text((width // 2 - 120, 120), "CERTIFICATE OF ACHIEVEMENT", fill=(30, 41, 59))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _get_test_client():
    """Imports FastAPI app lazily so non-API tests still run if PyMuPDF is blocked."""
    if not HAS_PYMUPDF:
        pytest.skip("PyMuPDF (_mupdf.pyd) unavailable or blocked by OS policy in this environment")
    from app.main import app
    return TestClient(app)


# ---------------------------------------------------------------------------
# 1. Dataset Parsing Tests (.csv, .xlsx, .json)
# ---------------------------------------------------------------------------

class TestDatasetParsing:
    def test_parse_csv_with_banner_rows_whitespace_and_missing_values(self):
        csv_text = (
            "Annual Tech Summit 2026\n"
            "\n"
            "  Full Name  , Email , Department , Year \n"
            '"  Alice   Johnson \n ",alice@example.com,"  Computer\nScience ",2026\n'
            "  Bob Smith , , Mechanical , 2025 \n"
            ",,,\n"
        )
        records = load_dataset(content_bytes=csv_text.encode("utf-8"), filename="participants.csv")
        assert len(records) == 2
        assert records[0]["Full Name"] == "Alice Johnson"
        assert records[0]["Email"] == "alice@example.com"
        assert records[0]["Department"] == "Computer Science"
        assert records[0]["Year"] == "2026"
        assert records[1]["Full Name"] == "Bob Smith"
        assert records[1]["Email"] == ""

    def test_parse_xlsx_with_banner_rows_and_missing_values(self):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Autocert Export Report"])  # Single-cell banner row
        ws.append([None, None, None])          # Blank row
        ws.append(["Full Name", "Email", "Department", "Year"])
        ws.append(["  Carol\n  White  ", "carol@example.com", "Electronics", 2026])
        ws.append(["Dave Brown", None, "  Civil  ", None])

        buf = io.BytesIO()
        wb.save(buf)
        wb.close()

        records = load_dataset(content_bytes=buf.getvalue(), filename="roster.xlsx")
        assert len(records) == 2
        assert records[0]["Full Name"] == "Carol White"
        assert records[0]["Year"] == "2026"
        assert records[1]["Full Name"] == "Dave Brown"
        assert records[1]["Email"] == ""
        assert records[1]["Department"] == "Civil"
        assert records[1]["Year"] == ""

    def test_parse_json_list_and_wrapped_object(self):
        payload_list = [
            {"full_name": "Eve Adams", "email": "eve@example.com", "year": "2026"},
            {"full_name": "Frank Lee", "email": "", "year": None},
        ]
        records = load_dataset(
            content_bytes=json.dumps(payload_list).encode("utf-8"),
            filename="data.json",
        )
        assert len(records) == 2
        assert records[0]["full_name"] == "Eve Adams"

        wrapped = {"participants": payload_list}
        records_wrapped = load_dataset(
            content_bytes=json.dumps(wrapped).encode("utf-8"),
            filename="wrapped.json",
        )
        assert len(records_wrapped) == 2
        assert records_wrapped[1]["full_name"] == "Frank Lee"


# ---------------------------------------------------------------------------
# 2. Placeholder Extraction & Style Detection (PDF & PNG)
# ---------------------------------------------------------------------------

class TestTemplatePlaceholderExtraction:
    @pytest.mark.skipif(not HAS_PYMUPDF, reason="PyMuPDF unavailable in this environment")
    def test_sample_pdf_placeholder_extraction(self):
        from app.services import template_scanner

        sample_pdf = BACKEND_DIR / "sample_templates" / "sample cert 2.pdf"
        if not sample_pdf.exists():
            pytest.skip("sample cert 2.pdf not present")

        pdf_bytes = sample_pdf.read_bytes()
        if hasattr(template_scanner, "scan_template_details"):
            manifest, placeholders = template_scanner.scan_template_details(pdf_bytes, "sample cert 2.pdf")
            assert isinstance(manifest, TemplateManifest)
            assert isinstance(placeholders, list)
            assert len(placeholders) >= 1
            for p in placeholders:
                assert "key" in p and "token" in p and "label" in p
                assert "bold" in p and "italic" in p
        else:
            manifest = template_scanner.scan_template_placeholders(pdf_bytes, "sample cert 2.pdf")
            assert isinstance(manifest, TemplateManifest)
            assert len(manifest.fields) >= 1

    @pytest.mark.skipif(not HAS_PYMUPDF, reason="PyMuPDF unavailable in this environment")
    def test_synthetic_pdf_ignores_watermark_merges_split_spans_and_detects_styles(self):
        import pymupdf as fitz
        from app.services import template_scanner

        doc = fitz.open()
        page = doc.new_page(width=842, height=595)

        # Diagonal watermark that must be ignored
        page.insert_text(
            (200, 350),
            "{{watermark_fake}}",
            fontsize=40,
            morph=(fitz.Point(200, 350), fitz.Matrix(45)),
            color=(0.8, 0.8, 0.8),
        )

        # Bold placeholder
        page.insert_text((250, 220), "{{name}}", fontsize=28, fontname="hebo", color=(0.1, 0.2, 0.4))

        # Italic placeholder
        page.insert_text((250, 300), "{{award_title}}", fontsize=18, fontname="heit", color=(0.2, 0.2, 0.2))

        # Split spans on same horizontal baseline: "{{" + "custom_track" + "}}"
        page.insert_text((250, 380), "{{", fontsize=14, fontname="helv")
        page.insert_text((264, 380), "custom_track", fontsize=14, fontname="helv")
        page.insert_text((352, 380), "}}", fontsize=14, fontname="helv")

        pdf_bytes = doc.tobytes()
        doc.close()

        if hasattr(template_scanner, "scan_template_details"):
            manifest, placeholders = template_scanner.scan_template_details(pdf_bytes, "synthetic.pdf")
            keys = {p["key"]: p for p in placeholders}
            assert "watermark_fake" not in keys
            assert "watermark_fake" not in manifest.fields

            # Name should be extracted as bold
            name_key = "full_name" if "full_name" in keys else "name"
            assert name_key in keys
            assert keys[name_key]["bold"] is True

            # Italic style extracted
            assert "award_title" in keys
            assert keys["award_title"]["italic"] is True

            # Split spans merged
            assert "custom_track" in keys
        else:
            manifest = template_scanner.scan_template_placeholders(pdf_bytes, "synthetic.pdf")
            assert "watermark_fake" not in manifest.fields

    def test_png_template_scanning_returns_manifest(self):
        if not HAS_PYMUPDF:
            pytest.skip("template_scanner imports pymupdf at module load")
        from app.services import template_scanner

        png_bytes = _make_png_template()
        if hasattr(template_scanner, "scan_template_details"):
            manifest, placeholders = template_scanner.scan_template_details(png_bytes, "cert.png")
            assert isinstance(manifest, TemplateManifest)
            assert isinstance(placeholders, list)
            assert len(manifest.fields) >= 1
        else:
            manifest = template_scanner.scan_template_placeholders(png_bytes, "cert.png")
            assert isinstance(manifest, TemplateManifest)
            assert len(manifest.fields) >= 1


# ---------------------------------------------------------------------------
# 3. Font Scaling & Overflow Warning Reporting
# ---------------------------------------------------------------------------

class TestTextFittingAndOverflow:
    def test_binary_search_font_scaling_short_vs_long_name(self):
        service = TextFittingService()
        img = Image.new("RGB", (1200, 850), "white")
        draw = ImageDraw.Draw(img)

        _, short_size, short_w = service.fit_text_to_width(
            draw=draw,
            text="Ana",
            font_family="sans-serif",
            target_size=72,
            max_width=400,
            min_size=14,
        )
        _, long_size, long_w = service.fit_text_to_width(
            draw=draw,
            text="Alexandria Bartholomew-Montgomery III",
            font_family="sans-serif",
            target_size=72,
            max_width=400,
            min_size=14,
        )

        assert short_size > long_size
        assert short_w <= 400
        assert long_w <= 400

    def test_image_engine_flags_overflow_and_ellipsizes(self):
        service = TextFittingService()
        engine = PillowImageEngine(service)
        png_bytes = _make_png_template(1000, 700)

        # Very tight box + single line + high min_font_size_pct -> must trigger overflow
        manifest_flag = TemplateManifest(
            template_id="tight_flag",
            template_filename="tight.png",
            default_format="png",
            base_width=1000,
            base_height=700,
            fields={
                "full_name": FieldConfig(
                    name="full_name",
                    x_pct=0.5,
                    y_pct=0.5,
                    max_w_pct=0.20,
                    max_lines=1,
                    font_size_pct=0.05,
                    min_font_size_pct=0.035,
                    overflow_policy="flag_overflow",
                )
            },
        )
        res = engine.render(
            template_bytes=png_bytes,
            fields={"full_name": "Professor Maximilian Bartholomew-Featherstonehaugh"},
            manifest=manifest_flag,
        )
        assert res.content
        assert res.overflowed is True
        assert len(res.warnings) >= 1

        # Ellipsize policy should also produce valid image & fit within max_lines
        manifest_ellip = TemplateManifest(
            template_id="tight_ellip",
            template_filename="tight.png",
            default_format="png",
            base_width=1000,
            base_height=700,
            fields={
                "full_name": FieldConfig(
                    name="full_name",
                    x_pct=0.5,
                    y_pct=0.5,
                    max_w_pct=0.25,
                    max_lines=1,
                    font_size_pct=0.05,
                    min_font_size_pct=0.035,
                    overflow_policy="ellipsize",
                )
            },
        )
        res_ellip = engine.render(
            template_bytes=png_bytes,
            fields={"full_name": "Professor Maximilian Bartholomew-Featherstonehaugh"},
            manifest=manifest_ellip,
        )
        assert res_ellip.content.startswith(b"\x89PNG")


# ---------------------------------------------------------------------------
# 4. API Endpoints: /api/templates/inspect, /api/certificates/generate,
#    Path Traversal Protection, and Mocked SMTP Validation/Retry/Escaping
# ---------------------------------------------------------------------------

class TestApiEndpointsAndSecurity:
    def test_inspect_template_endpoint(self):
        client = _get_test_client()
        png_bytes = _make_png_template()

        resp = client.post(
            "/api/templates/inspect",
            files={"template": ("cert_template.png", png_bytes, "image/png")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("ok") is True
        assert "extracted_placeholders" in data
        assert isinstance(data["extracted_placeholders"], list)

        # Unsupported extension should return 400
        bad_resp = client.post(
            "/api/templates/inspect",
            files={"template": ("bad.txt", b"hello", "text/plain")},
        )
        assert bad_resp.status_code == 400

    def test_generate_with_dynamic_field_mapping_and_missing_name_isolation(self):
        client = _get_test_client()
        png_bytes = _make_png_template()

        participants = [
            {"LearnerName": "Ada Lovelace", "Track": "Quantum Computing", "Email": "ada@example.com"},
            {"LearnerName": "", "Track": "AI", "Email": "noname@example.com"},
        ]
        field_mapping = {
            "full_name": "LearnerName",
            "department": "Track",
            "email": "Email",
        }

        resp = client.post(
            "/api/certificates/generate",
            files={"template": ("cert.png", png_bytes, "image/png")},
            data={
                "participants": json.dumps(participants),
                "field_mapping": json.dumps(field_mapping),
                "format": "png",
                "send_emails": "false",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["generated_count"] == 1
        assert data["failed_count"] == 1
        assert data["batch_id"].startswith("batch_")

        cert_item = next(c for c in data["certificates"] if c["status"] == "Generated")
        assert cert_item["participant_name"] == "Ada Lovelace"
        assert cert_item["preview_url"].startswith(f"/api/certificates/download/{data['batch_id']}/")

        # Download the generated certificate via its batch-scoped URL
        dl_resp = client.get(cert_item["preview_url"])
        assert dl_resp.status_code == 200
        assert dl_resp.content.startswith(b"\x89PNG")

    def test_download_path_traversal_protection(self):
        client = _get_test_client()
        from app.main import _resolve_certificate_path

        # Direct unit checks
        assert _resolve_certificate_path("../.env") is None
        assert _resolve_certificate_path("..\\..\\.env") is None
        assert _resolve_certificate_path(".env", batch_id="..") is None

        # HTTP endpoint checks
        for bad_url in [
            "/api/certificates/download/..%2F..%2F.env",
            "/api/certificates/download/..%5C..%5C.env",
            "/api/certificates/download/batch_fake/..%2F..%2F.env",
            "/api/certificates/download/../.env",
        ]:
            resp = client.get(bad_url)
            assert resp.status_code in (400, 403, 404)
            assert "SUPABASE" not in resp.text

    def test_mocked_smtp_validation_retry_html_escaping_and_idempotency(self, tmp_path):
        client = _get_test_client()
        from app.core.config import Settings
        from app.main import OUTPUT_DIR

        # Create a dummy certificate file inside OUTPUT_DIR/test_batch_smtp
        batch_id = "test_batch_smtp"
        batch_dir = os.path.join(OUTPUT_DIR, batch_id)
        os.makedirs(batch_dir, exist_ok=True)
        cert_file = os.path.join(batch_dir, "CERT-XSS-1.png")
        with open(cert_file, "wb") as f:
            f.write(_make_png_template(400, 300))

        fake_settings = Settings(
            supabase_url=None,
            supabase_publishable_key=None,
            supabase_anon_key=None,
            supabase_service_key=None,
            database_url=None,
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_user="sender@example.com",
            smtp_password="app-password",
            smtp_from_email="sender@example.com",
            smtp_from_name="Autocert Test",
        )

        mock_server = MagicMock()
        # First send_message fails with transient SMTPException, second succeeds
        mock_server.send_message.side_effect = [
            smtplib.SMTPServerDisconnected("Transient drop"),
            None,
        ]
        mock_smtp_cm = MagicMock()
        mock_smtp_cm.__enter__.return_value = mock_server
        mock_smtp_cm.__exit__.return_value = False

        try:
            with (
                patch("app.main.load_settings", return_value=fake_settings),
                patch("app.main.smtplib.SMTP", return_value=mock_smtp_cm),
                patch("app.main.time.sleep", return_value=None),
            ):
                payload = {
                    "batch_id": batch_id,
                    "recipients": [
                        {
                            "certificate_id": "CERT-XSS-1",
                            "filename": "CERT-XSS-1.png",
                            "email": "valid.user@example.com",
                            "full_name": '<script>alert("xss")</script>',
                            "event_name": "<b>Summit</b>",
                        },
                        {
                            "certificate_id": "CERT-BAD-EMAIL",
                            "filename": "CERT-XSS-1.png",
                            "email": "not-an-email",
                            "full_name": "Bad Email User",
                        },
                    ],
                }
                resp = client.post("/api/certificates/send-batch-emails", json=payload)
                assert resp.status_code == 200
                results = resp.json()["results"]

                # First recipient succeeded after transient retry
                assert results[0]["status"] == "Sent"
                assert mock_server.send_message.call_count == 2

                # Verify HTML escaping in the HTML body part of the sent EmailMessage
                sent_msg = mock_server.send_message.call_args[0][0]
                html_part = sent_msg.get_body(preferencelist=("html",))
                assert html_part is not None
                html_body = html_part.get_content()
                assert "<script>alert" not in html_body
                assert "&lt;script&gt;" in html_body

                # Invalid email rejected without calling send_message
                assert results[1]["status"] == "Failed"

                # Second call for same batch_id + certificate_id is deduplicated
                resp2 = client.post("/api/certificates/send-batch-emails", json={
                    "batch_id": batch_id,
                    "recipients": [payload["recipients"][0]],
                })
                assert resp2.status_code == 200
                assert resp2.json()["results"][0]["deduplicated"] is True
                assert "Skipped" in resp2.json()["results"][0]["status"]
        finally:
            if os.path.exists(cert_file):
                os.remove(cert_file)
            if os.path.isdir(batch_dir):
                try:
                    os.rmdir(batch_dir)
                except OSError:
                    pass
