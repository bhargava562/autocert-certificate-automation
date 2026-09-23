#!/usr/bin/env python3
"""
Certificate Generation Test Runner
Executes the SOLID-based certificate generation pipeline against the mock participant dataset.
Supports:
  --mode local (default): Reads template from sample_templates/ and writes output to sample_templates/output/
  --mode cloud: Reads from Supabase Storage 'templates' bucket and writes to 'certificates' bucket

Only required data fields from the participant dataset are pulled per field mapping.
All dimensions are proportional (0.0-1.0) - zero fixed coordinates.
"""

import os
import sys
import json
import argparse

# Ensure backend root is on sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.config import load_settings
from app.services.models import TemplateManifest, FieldConfig
from app.services.text_fitting import TextFittingService
from app.services.engines.factory import CertificateEngineFactory
from app.services.providers.local_provider import LocalTemplateProvider, LocalDiskSink
from app.services.providers.supabase_provider import SupabaseTemplateProvider, SupabaseStorageSink
from app.services.pipeline import CertificatePipeline

def build_manifest(template_filename: str, output_format: str = "png") -> TemplateManifest:
    """
    Creates a normalized dynamic layout manifest for the given template file.
    All positions and sizes are proportional (0.0-1.0) relative to canvas dimensions.
    No fixed pixel values -- engine adapts to any resolution.
    """
    normalized_format = "pdf" if output_format.lower() == "pdf" else "png"
    fn_lower = template_filename.lower()

    if "white" in fn_lower or "green" in fn_lower or "completion" in fn_lower or "geometric" in fn_lower:
        # White Green Abstract Geometric Certificate of Completion
        # Layout: 'This is to certify that' (static) -> recipient name above line at ~48.8%
        #         achievement text block ~53-65%, issue date ~68%, signers pre-printed at ~73%+
        manifest = TemplateManifest(
            template_id="white_green_completion",
            template_filename=template_filename,
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
                    clear_bg_color="#F9F9F9"
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
                    clear_bg_color="#F9F9F9"
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
                    clear_bg_color="#F9F9F9"
                ),
            }
        )

    elif "internship" in fn_lower or "red" in fn_lower:
        # Red Gold and White Modern Internship Certificate
        manifest = TemplateManifest(
            template_id="red_gold_internship",
            template_filename=template_filename,
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
        # Fallback: Black Gold Formal Appreciation Certificate
        manifest = TemplateManifest(
            template_id="black_gold_appreciation",
            template_filename=template_filename,
            default_format=normalized_format,
            base_width=2000,
            base_height=1414,
            fields={
                "full_name": FieldConfig(
                    name="full_name",
                    x_pct=0.50,
                    y_pct=0.455,
                    max_w_pct=0.65,
                    font_family="script",
                    font_size_pct=0.065,
                    min_font_size_pct=0.018,
                    align="center",
                    color="#C5A059",
                    anchor_phrase="THIS CERTIFICATE IS PRESENTED TO",
                    clear_area=(0.20, 0.38, 0.80, 0.505),
                    clear_bg_color="#000000"
                ),
            }
        )
    return manifest

def resolve_template_filename(templates_dir: str, requested: str = None) -> str:
    """Finds matching template filename (image only) in templates directory."""
    if requested:
        if os.path.exists(os.path.join(templates_dir, requested)):
            return requested
        for fn in os.listdir(templates_dir):
            if requested.lower() in fn.lower() and fn.lower().endswith((".png", ".jpg", ".jpeg")):
                return fn

    # Auto-detect: prefer White Green Completion template if present
    available_pngs = [
        f for f in os.listdir(templates_dir)
        if f.lower().endswith((".png", ".jpg", ".jpeg"))
        and os.path.isfile(os.path.join(templates_dir, f))
    ]
    if not available_pngs:
        raise FileNotFoundError(f"No image templates found in {templates_dir}")

    # Priority: white-green > internship > first available
    for fn in available_pngs:
        fl = fn.lower()
        if "white" in fl or "green" in fl or "completion" in fl or "geometric" in fl:
            return fn
    for fn in available_pngs:
        if "internship" in fn.lower():
            return fn

    return available_pngs[0]


def normalize_participant(p: dict) -> dict:
    """
    Produces a normalized field map from a raw participant record.
    Only pulls required fields; no personal info beyond what's needed for the certificate.
    Field resolution order ensures fallback without duplication.
    """
    full_name = p.get("full_name") or p.get("recipient_name") or p.get("name") or ""
    achievement_text = p.get("achievement_text") or p.get("description") or ""
    return {
        "full_name": full_name,
        "certificate_id": p.get("certificate_id", ""),
        "achievement_title": p.get("achievement_title") or p.get("role") or "",
        "achievement_text": achievement_text,
        "issue_date": p.get("issue_date") or p.get("participated_date") or "",
        "signer_name": p.get("signer_name") or "",
        "signer_title": p.get("signer_title") or "",
        "organization_on_certificate": p.get("organization_on_certificate") or "",
        "event_name": p.get("event_name") or "",
        "participation_type": p.get("participation_type") or "",
        "gender": p.get("gender") or "",
    }

def run_pipeline(mode: str = "local", format_type: str = "png", template_name: str = None, clean: bool = True):
    settings = load_settings()
    templates_dir = os.path.join(backend_dir, "sample_templates")
    mock_data_path = os.path.join(backend_dir, "sample_data", "mock_participants.json")

    # Load participants and normalize to only required certificate fields
    with open(mock_data_path, "r", encoding="utf-8") as f:
        raw_participants = json.load(f)
    participants = [normalize_participant(p) for p in raw_participants]

    filename_target = resolve_template_filename(templates_dir, template_name)
    manifest = build_manifest(template_filename=filename_target, output_format=format_type)
    text_service = TextFittingService()
    engine_factory = CertificateEngineFactory(text_service)

    resolved_format = manifest.default_format.upper()
    print("=" * 70)
    print(f"AUTOCERT GENERATION PIPELINE - Mode: {mode.upper()} | Output Format: {resolved_format}")
    print("=" * 70)
    print(f"Active Master Template : {filename_target}")
    print(f"Output Type            : All {'PDF Documents' if resolved_format == 'PDF' else 'PNG Images'} (Separate Generation)")
    print(f"Participants Count     : {len(participants)}")
    print()
    for i, p in enumerate(participants, 1):
        print(f"  {i:2}. {p['full_name']} [{p['certificate_id']}]")
    print("-" * 70)

    if mode == "local":
        output_dir = os.path.join(templates_dir, "output")
        os.makedirs(output_dir, exist_ok=True)
        if clean:
            # Clean output directory - ensures outputs of different formats are never mixed
            removed = 0
            for f in os.listdir(output_dir):
                fp = os.path.join(output_dir, f)
                if os.path.isfile(fp):
                    os.remove(fp)
                    removed += 1
            print(f"Cleaned output directory ({removed} files removed): {output_dir}")

        provider = LocalTemplateProvider(templates_dir)
        sink = LocalDiskSink(output_dir)
        print(f"Source Folder : {templates_dir}")
        print(f"Output Folder : {output_dir}")
    else:
        if not settings.supabase_url or not settings.supabase_service_key:
            print("Error: Supabase credentials not found in .env. Cannot run cloud mode.", file=sys.stderr)
            sys.exit(1)
        provider = SupabaseTemplateProvider(settings, bucket_name="templates")
        sink = SupabaseStorageSink(settings, bucket_name="certificates")
        print(f"Source : Supabase Storage 'templates' bucket ({settings.supabase_url})")
        print(f"Output : Supabase Storage 'certificates' bucket")

    pipeline = CertificatePipeline(
        template_provider=provider,
        engine_factory=engine_factory,
        storage_sink=sink
    )

    print(f"\nExecuting batch certificate generation (Format: {resolved_format})...")
    results = pipeline.generate_batch(
        template_id=filename_target,
        participants=participants,
        manifest=manifest
    )

    print(f"\nGeneration completed - {len(results)} certificate(s) produced:")
    for loc in results:
        print(f"  -> {loc}")

    print("\n" + "=" * 70)
    return results

def main():
    parser = argparse.ArgumentParser(description="Autocert Certificate Generation Test")
    parser.add_argument(
        "--template",
        default=None,
        help="Template name or keyword to test (e.g. 'internship', 'black_gold')"
    )
    parser.add_argument(
        "--mode",
        choices=["local", "cloud"],
        default="local",
        help="Execution mode: local (folder-in/folder-out) or cloud (Supabase Storage)"
    )
    parser.add_argument(
        "--format",
        choices=["png", "image", "pdf"],
        default="png",
        help="Target output format: 'png'/'image' (generates all images) or 'pdf' (generates all PDFs)"
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="Do not clean output folder prior to batch generation"
    )
    args = parser.parse_args()
    chosen_fmt = "png" if args.format in ("png", "image") else "pdf"
    run_pipeline(
        mode=args.mode,
        format_type=chosen_fmt,
        template_name=args.template,
        clean=not args.no_clean
    )

if __name__ == "__main__":
    main()
