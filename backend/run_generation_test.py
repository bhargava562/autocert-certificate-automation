#!/usr/bin/env python3
"""
Certificate Generation Test Runner
Executes the SOLID-based certificate generation pipeline against the 5-member mock dataset.
Supports:
  --mode local (default): Reads template from sample_templates/ and writes output to sample_templates/output/
  --mode cloud: Reads from Supabase Storage 'templates' bucket and writes to 'certificates' bucket
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
    """Creates a normalized dynamic layout manifest matching the template"""
    normalized_format = "pdf" if output_format.lower() == "pdf" else "png"

    if "internship" in template_filename.lower() or "red" in template_filename.lower():
        # Red Gold and White Modern Internship Certificate
        manifest = TemplateManifest(
            template_id="red_gold_internship",
            template_filename=template_filename,
            default_format=normalized_format,
            base_width=2000,
            base_height=1414,
            fields={
                "name": FieldConfig(
                    name="name",
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
                "role": FieldConfig(
                    name="role",
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
                "date": FieldConfig(
                    name="date",
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
                )
            }
        )
    else:
        # Black Gold Formal Appreciation Certificate
        manifest = TemplateManifest(
            template_id="black_gold_appreciation",
            template_filename=template_filename,
            default_format=normalized_format,
            base_width=2000,
            base_height=1414,
            fields={
                "recipient_name": FieldConfig(
                    name="recipient_name",
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
                    clear_bg_color="#FFFFFF"
                )
            }
        )
    return manifest

def resolve_template_filename(templates_dir: str, requested: str = None) -> str:
    """Finds matching template filename in templates directory"""
    if requested:
        if os.path.exists(os.path.join(templates_dir, requested)):
            return requested
        for fn in os.listdir(templates_dir):
            if requested.lower() in fn.lower() and fn.endswith((".png", ".jpg", ".jpeg")):
                return fn

    # Auto-detect newest or priority PNG template
    available_pngs = [
        f for f in os.listdir(templates_dir)
        if f.endswith((".png", ".jpg", ".jpeg")) and os.path.isfile(os.path.join(templates_dir, f))
    ]
    if not available_pngs:
        raise FileNotFoundError(f"No image templates found in {templates_dir}")

    # Prioritize Internship certificate if present
    for fn in available_pngs:
        if "internship" in fn.lower():
            return fn

    return available_pngs[0]

def run_pipeline(mode: str = "local", format_type: str = "png", template_name: str = None, clean: bool = True):
    settings = load_settings()
    templates_dir = os.path.join(backend_dir, "sample_templates")
    mock_data_path = os.path.join(backend_dir, "sample_data", "mock_participants.json")

    # Load 5 mock participants
    with open(mock_data_path, "r", encoding="utf-8") as f:
        participants = json.load(f)

    filename_target = resolve_template_filename(templates_dir, template_name)
    manifest = build_manifest(template_filename=filename_target, output_format=format_type)
    text_service = TextFittingService()
    engine_factory = CertificateEngineFactory(text_service)

    resolved_format = manifest.default_format.upper()
    print("=" * 70)
    print(f"AUTOCERT GENERATION PIPELINE — Mode: {mode.upper()} | Output Format: {resolved_format}")
    print("=" * 70)
    print(f"Active Master Template: {filename_target}")
    print(f"Output Type: All {'PDF Documents' if resolved_format == 'PDF' else 'PNG Images'} (Separate Generation)")
    print(f"Participants Count: {len(participants)}")
    for i, p in enumerate(participants, 1):
        print(f"  {i}. {p['recipient_name']} ({p['certificate_id']})")
    print("-" * 70)

    if mode == "local":
        output_dir = os.path.join(templates_dir, "output")
        os.makedirs(output_dir, exist_ok=True)
        if clean:
            # Clean output directory so outputs of different formats are never mixed
            for f in os.listdir(output_dir):
                fp = os.path.join(output_dir, f)
                if os.path.isfile(fp):
                    os.remove(fp)
            print(f"Cleaned output directory: {output_dir}")

        provider = LocalTemplateProvider(templates_dir)
        sink = LocalDiskSink(output_dir)
        print(f"Source Folder: {templates_dir}")
        print(f"Output Folder: {output_dir}")
    else:
        if not settings.supabase_url or not settings.supabase_service_key:
            print("Error: Supabase credentials not found in .env. Cannot run cloud mode.", file=sys.stderr)
            sys.exit(1)
        provider = SupabaseTemplateProvider(settings, bucket_name="templates")
        sink = SupabaseStorageSink(settings, bucket_name="certificates")
        print(f"Source: Supabase Storage 'templates' bucket ({settings.supabase_url})")
        print(f"Output: Supabase Storage 'certificates' bucket")

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

    print("\nGeneration completed successfully:")
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
