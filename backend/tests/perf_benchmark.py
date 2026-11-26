"""
Performance Benchmark for Autocert Certificate Generation Engine.

Measures:
- Batch generation for N=50, N=250, and N=1000 records.
- Concurrent batch requests (multiple batches running simultaneously).
- Total wall time, average per-certificate latency, p95 per-certificate latency,
  throughput (certs/sec), and peak traced memory (tracemalloc).

Usage:
    backend\\.venv\\Scripts\\python backend/tests/perf_benchmark.py
"""

import io
import os
import sys
import tempfile
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List

from PIL import Image, ImageDraw

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.engines.image_engine import PillowImageEngine
from app.services.models import FieldConfig, TemplateManifest
from app.services.text_fitting import TextFittingService


def _create_benchmark_template(width: int = 1600, height: int = 1131) -> bytes:
    """Generates a realistic in-memory PNG template for benchmarking."""
    img = Image.new("RGB", (width, height), color=(252, 250, 245))
    draw = ImageDraw.Draw(img)
    draw.rectangle([(40, 40), (width - 40, height - 40)], outline=(197, 160, 89), width=8)
    draw.text((width // 2 - 180, 140), "CERTIFICATE OF ACHIEVEMENT", fill=(26, 92, 71))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _build_manifest() -> TemplateManifest:
    return TemplateManifest(
        template_id="bench_template",
        template_filename="bench_template.png",
        default_format="png",
        base_width=1600,
        base_height=1131,
        fields={
            "full_name": FieldConfig(
                name="full_name",
                x_pct=0.50,
                y_pct=0.45,
                max_w_pct=0.65,
                max_lines=2,
                font_family="script",
                font_size_pct=0.065,
                min_font_size_pct=0.018,
                color="#1A5C47",
            ),
            "department": FieldConfig(
                name="department",
                x_pct=0.50,
                y_pct=0.58,
                max_w_pct=0.45,
                max_lines=1,
                font_family="sans-serif",
                font_size_pct=0.028,
                min_font_size_pct=0.014,
                color="#334155",
            ),
            "year": FieldConfig(
                name="year",
                x_pct=0.50,
                y_pct=0.66,
                max_w_pct=0.20,
                max_lines=1,
                font_family="sans-serif",
                font_size_pct=0.024,
                min_font_size_pct=0.014,
                color="#475569",
            ),
        },
    )


def _generate_records(n: int) -> List[Dict[str, str]]:
    names = [
        "Alice Johnson",
        "Bob Smith",
        "Catherine Alexandria Montgomery",
        "David Chen",
        "Elena Rostova-Vance",
    ]
    depts = ["Computer Science", "Mechanical Engineering", "Data Science", "Biotechnology"]
    return [
        {
            "certificate_id": f"BENCH-{i:04d}",
            "full_name": f"{names[i % len(names)]} #{i}",
            "department": depts[i % len(depts)],
            "year": "2026",
        }
        for i in range(1, n + 1)
    ]


def _percentile(sorted_vals: List[float], pct: float) -> float:
    if not sorted_vals:
        return 0.0
    idx = min(len(sorted_vals) - 1, max(0, int(round((pct / 100.0) * (len(sorted_vals) - 1)))))
    return sorted_vals[idx]


def run_batch_benchmark(
    n: int,
    template_bytes: bytes,
    manifest: TemplateManifest,
    engine: PillowImageEngine,
    out_dir: str,
    max_workers: int,
) -> Dict[str, float]:
    records = _generate_records(n)

    def _render_one(rec: Dict[str, str]) -> float:
        t0 = time.perf_counter()
        res = engine.render(template_bytes=template_bytes, fields=rec, manifest=manifest)
        out_path = os.path.join(out_dir, f"{rec['certificate_id']}.png")
        with open(out_path, "wb") as f:
            f.write(res.content)
        return (time.perf_counter() - t0) * 1000.0

    tracemalloc.start()
    wall_start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        latencies_ms = list(pool.map(_render_one, records))
    wall_s = time.perf_counter() - wall_start
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    latencies_ms.sort()
    avg_ms = sum(latencies_ms) / len(latencies_ms)
    p95_ms = _percentile(latencies_ms, 95.0)
    throughput = n / wall_s if wall_s > 0 else 0.0
    peak_mb = peak_bytes / (1024.0 * 1024.0)

    return {
        "n": n,
        "wall_s": wall_s,
        "avg_ms": avg_ms,
        "p95_ms": p95_ms,
        "throughput": throughput,
        "peak_mb": peak_mb,
    }


def run_concurrent_batches_benchmark(
    num_batches: int,
    records_per_batch: int,
    template_bytes: bytes,
    manifest: TemplateManifest,
    engine: PillowImageEngine,
    base_dir: str,
) -> Dict[str, float]:
    tracemalloc.start()
    wall_start = time.perf_counter()

    def _run_one_batch(batch_idx: int) -> List[float]:
        b_dir = os.path.join(base_dir, f"concurrent_{batch_idx}")
        os.makedirs(b_dir, exist_ok=True)
        recs = _generate_records(records_per_batch)
        lats = []
        for rec in recs:
            t0 = time.perf_counter()
            res = engine.render(template_bytes=template_bytes, fields=rec, manifest=manifest)
            with open(os.path.join(b_dir, f"{rec['certificate_id']}.png"), "wb") as f:
                f.write(res.content)
            lats.append((time.perf_counter() - t0) * 1000.0)
        return lats

    with ThreadPoolExecutor(max_workers=num_batches) as pool:
        nested = list(pool.map(_run_one_batch, range(num_batches)))

    wall_s = time.perf_counter() - wall_start
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    all_lats = sorted(lat for sub in nested for lat in sub)
    total_n = len(all_lats)
    return {
        "n": total_n,
        "batches": num_batches,
        "wall_s": wall_s,
        "avg_ms": sum(all_lats) / total_n,
        "p95_ms": _percentile(all_lats, 95.0),
        "throughput": total_n / wall_s if wall_s > 0 else 0.0,
        "peak_mb": peak_bytes / (1024.0 * 1024.0),
    }


def main() -> None:
    template_bytes = _create_benchmark_template()
    manifest = _build_manifest()
    text_service = TextFittingService()
    engine = PillowImageEngine(text_service)
    max_workers = min(16, (os.cpu_count() or 1) + 4)

    print(f"Autocert Performance Benchmark (workers={max_workers})")
    print("-" * 86)
    print(f"{'Scenario':<26} {'Wall (s)':>10} {'Avg (ms)':>10} {'P95 (ms)':>10} {'Certs/s':>10} {'Peak MB':>10}")
    print("-" * 86)

    with tempfile.TemporaryDirectory(prefix="autocert_bench_") as tmp_dir:
        for n in (50, 250, 1000):
            batch_dir = os.path.join(tmp_dir, f"batch_{n}")
            os.makedirs(batch_dir, exist_ok=True)
            stats = run_batch_benchmark(n, template_bytes, manifest, engine, batch_dir, max_workers)
            print(
                f"{f'Batch N={n}':<26} "
                f"{stats['wall_s']:>10.3f} "
                f"{stats['avg_ms']:>10.2f} "
                f"{stats['p95_ms']:>10.2f} "
                f"{stats['throughput']:>10.2f} "
                f"{stats['peak_mb']:>10.2f}"
            )

        conc_stats = run_concurrent_batches_benchmark(
            num_batches=4,
            records_per_batch=50,
            template_bytes=template_bytes,
            manifest=manifest,
            engine=engine,
            base_dir=tmp_dir,
        )
        print(
            f"{'Concurrent 4x50 (N=200)':<26} "
            f"{conc_stats['wall_s']:>10.3f} "
            f"{conc_stats['avg_ms']:>10.2f} "
            f"{conc_stats['p95_ms']:>10.2f} "
            f"{conc_stats['throughput']:>10.2f} "
            f"{conc_stats['peak_mb']:>10.2f}"
        )
    print("-" * 86)


if __name__ == "__main__":
    main()
