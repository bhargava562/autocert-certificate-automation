#!/usr/bin/env python3
"""
Test Email Dispatcher - Multi-Participant Distinct Certificate Dispatch
Sends distinct personalized certificates to distinct recipient emails.
Uses Python standard smtplib + email.message.EmailMessage + Jinja2.
"""

import os
import sys
import json
import smtplib
import argparse
from email.message import EmailMessage
import jinja2

# Ensure backend root is on sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.config import load_settings
from run_generation_test import build_manifest, resolve_template_filename, normalize_participant
from app.services.text_fitting import TextFittingService
from app.services.engines.factory import CertificateEngineFactory
from app.services.providers.local_provider import LocalTemplateProvider, LocalDiskSink
from app.services.pipeline import CertificatePipeline

def ensure_certificate_pdf(participant: dict) -> str:
    """Generates the certificate PDF if not already present, returns filepath."""
    templates_dir = os.path.join(backend_dir, "sample_templates")
    output_dir = os.path.join(templates_dir, "output")
    os.makedirs(output_dir, exist_ok=True)

    cert_id = participant.get("certificate_id", "cert")
    safe_name = participant.get("full_name", "recipient").replace(" ", "_")
    pdf_filename = f"{cert_id}_{safe_name}.pdf"
    pdf_path = os.path.join(output_dir, pdf_filename)

    if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
        return pdf_path

    # Generate on the fly using local pipeline
    print(f"Generating PDF certificate for {participant['full_name']}...")
    filename_target = resolve_template_filename(templates_dir)
    manifest = build_manifest(template_filename=filename_target, output_format="pdf")
    text_service = TextFittingService()
    engine_factory = CertificateEngineFactory(text_service)
    provider = LocalTemplateProvider(templates_dir)
    sink = LocalDiskSink(output_dir)

    pipeline = CertificatePipeline(
        template_provider=provider,
        engine_factory=engine_factory,
        storage_sink=sink
    )
    pipeline.generate_batch(
        template_id=filename_target,
        participants=[participant],
        manifest=manifest
    )
    return pdf_path

def send_distinct_emails(
    sender_email: str,
    sender_pwd: str,
    recipient_participant_pairs: list,
    template_path: str = None,
    smtp_host: str = "smtp.gmail.com",
    smtp_port: int = 587
):
    """
    Renders unique HTML templates and attaches distinct certificates for each recipient.
    recipient_participant_pairs: list of tuples (recipient_email, participant_dict)
    """
    if not template_path:
        template_path = os.path.join(backend_dir, "sample_templates", "sample_email_template.html")

    with open(template_path, "r", encoding="utf-8") as f:
        html_template = f.read()

    jinja_tmpl = jinja2.Template(html_template)
    clean_pwd = sender_pwd.replace(" ", "").strip()

    print("=" * 70)
    print("AUTOCERT DISTINCT CERTIFICATE EMAIL DISPATCH")
    print("=" * 70)
    print(f"SMTP Server : {smtp_host}:{smtp_port}")
    print(f"Sender      : {sender_email}")
    print(f"Dispatches  : {len(recipient_participant_pairs)} distinct recipients & certificates")
    print("-" * 70)

    for i, (rcpt, part) in enumerate(recipient_participant_pairs, 1):
        print(f"  {i}. {rcpt} -> {part.get('full_name')} [{part.get('certificate_id')}]")
    print("-" * 70)

    print(f"Connecting to {smtp_host}:{smtp_port} via STARTTLS...")
    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        print(f"Authenticating as {sender_email}...")
        server.login(sender_email, clean_pwd)
        print("Authentication successful!\n")

        for idx, (recipient, participant) in enumerate(recipient_participant_pairs, 1):
            recipient = recipient.strip()
            full_name = participant.get("full_name")
            cert_id = participant.get("certificate_id")

            # 1. Ensure participant's distinct PDF is generated
            pdf_path = ensure_certificate_pdf(participant)
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
            pdf_filename = os.path.basename(pdf_path)

            # 2. Render participant's personalized HTML email
            html_content = jinja_tmpl.render(**participant)

            # 3. Construct email message
            msg = EmailMessage()
            msg["Subject"] = f"Your Certificate of Achievement - {participant.get('event_name')}"
            msg["From"] = f"Autocert Certificates <{sender_email}>"
            msg["To"] = recipient

            # Plaintext fallback
            msg.set_content(
                f"Dear {full_name},\n\n"
                f"Congratulations! You have received your certificate for {participant.get('achievement_title')}.\n"
                f"Please find your certificate attached as a PDF.\n\n"
                f"Certificate ID: {cert_id}\n"
                f"Issue Date: {participant.get('issue_date')}\n"
            )

            # HTML content
            msg.add_alternative(html_content, subtype="html")

            # Unique PDF attachment
            msg.add_attachment(
                pdf_bytes,
                maintype="application",
                subtype="pdf",
                filename=pdf_filename
            )

            print(f"[{idx}/{len(recipient_participant_pairs)}] Sending to {recipient}...")
            print(f"      Participant: {full_name} ({cert_id})")
            print(f"      Attachment : {pdf_filename} ({len(pdf_bytes):,} bytes)")
            server.send_message(msg)
            print(f"      [SUCCESS] Dispatched to {recipient}\n")

    print("=" * 70)
    print("All distinct certificate emails dispatched successfully!")
    print("=" * 70)

def main():
    settings = load_settings()
    parser = argparse.ArgumentParser(description="Test Distinct Certificate Email Dispatch")
    parser.add_argument("--sender", default=settings.smtp_user, help="Sender email address")
    parser.add_argument("--pwd", default=settings.smtp_password, help="SMTP password / App password")
    parser.add_argument(
        "--recipients",
        nargs="+",
        default=[
            "bhaargavkc07@gmail.com",
            "suhasinikc1982@gmail.com",
            "240187.cb@rmkec.ac.in"
        ],
        help="Recipient email address(es)"
    )
    parser.add_argument("--host", default=settings.smtp_host, help="SMTP host")
    parser.add_argument("--port", type=int, default=settings.smtp_port, help="SMTP port")
    parser.add_argument("--start-idx", type=int, default=0, help="Starting index in mock_participants.json")

    args = parser.parse_args()

    # Load mock participants dataset
    mock_data_path = os.path.join(backend_dir, "sample_data", "mock_participants.json")
    with open(mock_data_path, "r", encoding="utf-8") as f:
        participants = json.load(f)

    # Map each recipient to a distinct participant
    pairs = []
    for i, rcpt in enumerate(args.recipients):
        part_idx = (args.start_idx + i) % len(participants)
        raw_p = participants[part_idx]
        normalized_p = normalize_participant(raw_p)
        if not normalized_p.get("organization"):
            normalized_p["organization"] = (
                raw_p.get("organization_on_certificate") or raw_p.get("organization") or "Borcelle Company"
            )
        pairs.append((rcpt, normalized_p))

    send_distinct_emails(
        sender_email=args.sender,
        sender_pwd=args.pwd,
        recipient_participant_pairs=pairs,
        smtp_host=args.host,
        smtp_port=args.port
    )

if __name__ == "__main__":
    main()
