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

def build_manifest(output_format: str = "png") -> TemplateManifest:
    """Creates a normalized layout manifest matching the Black Gold Appreciation Certificate"""
    normalized_format = "pdf" if output_format.lower() == "pdf" else "png"

    manifest = TemplateManifest(
        template_id="black_gold_appreciation",
        template_filename="Black Gold Formal Appreciation Certificate.png",
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

def run_pipeline(mode: str = "local", format_type: str = "png", clean: bool = True):
    settings = load_settings()
    templates_dir = os.path.join(backend_dir, "sample_templates")
    mock_data_path = os.path.join(backend_dir, "sample_data", "mock_participants.json")

    # Load 5 mock participants
    with open(mock_data_path, "r", encoding="utf-8") as f:
        participants = json.load(f)

    # Master template is always the PNG asset (PDF template lacks placeholders)
    filename_target = "Black Gold Formal Appreciation Certificate.png"
    manifest = build_manifest(output_format=format_type)
    text_service = TextFittingService()
    engine_factory = CertificateEngineFactory(text_service)

    resolved_format = manifest.default_format.upper()
    print("=" * 70)
    print(f"AUTOCERT GENERATION PIPELINE — Mode: {mode.upper()} | Output Format: {resolved_format}")
    print("=" * 70)
    print(f"Master Template: {filename_target}")
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
    run_pipeline(mode=args.mode, format_type=chosen_fmt, clean=not args.no_clean)

if __name__ == "__main__":
    main()
