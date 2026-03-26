#!/usr/bin/env python3
"""Verify deterministic generation by running the same request twice and diffing outputs."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Fields that legitimately differ between runs
IGNORE_KEYS = {"generatedAt", "filePath", "outputFolder", "resolvedOutputFolder",
               "requestJsonPath", "manifestPath", "registryPath", "generatedFiles"}

RENDERER = Path(__file__).resolve().parent / "render_invoice_batch.py"


def normalize(obj: object) -> object:
    """Recursively strip run-specific fields for comparison."""
    if isinstance(obj, dict):
        return {k: normalize(v) for k, v in obj.items() if k not in IGNORE_KEYS}
    if isinstance(obj, list):
        return [normalize(v) for v in obj]
    return obj


def run_render(request_path: Path, output_folder: Path) -> int:
    return subprocess.call(
        [sys.executable, str(RENDERER),
         "--request-json", str(request_path),
         "--output-folder", str(output_folder)],
    )


def collect_json(folder: Path) -> dict[str, object]:
    """Load all JSON files from a folder into a name-keyed dict, normalized."""
    result = {}
    for f in sorted(folder.glob("*.json")):
        raw = json.loads(f.read_text(encoding="utf-8-sig"))
        result[f.name] = normalize(raw)
    return result


def diff_results(a: dict, b: dict) -> list[str]:
    errors = []
    all_keys = sorted(set(a) | set(b))
    for key in all_keys:
        if key not in a:
            errors.append(f"  Missing in run A: {key}")
        elif key not in b:
            errors.append(f"  Missing in run B: {key}")
        elif a[key] != b[key]:
            errors.append(f"  Differs: {key}")
    return errors


def main() -> int:
    requests = sorted(Path(__file__).resolve().parent.parent.glob("specs/*_sample_request.json")) + \
               sorted(Path(__file__).resolve().parent.parent.glob("specs/*_html_sample_request.json"))

    if not requests:
        print("FAIL: No sample request fixtures found.")
        return 1

    # Dedupe by name
    seen = set()
    unique = []
    for r in requests:
        if r.name not in seen:
            seen.add(r.name)
            unique.append(r)
    requests = unique

    all_errors: list[str] = []
    for request_path in requests:
        label = request_path.stem
        with tempfile.TemporaryDirectory(prefix=f"det_a_{label}_") as dir_a, \
             tempfile.TemporaryDirectory(prefix=f"det_b_{label}_") as dir_b:
            print(f"--- {label} ---")
            rc_a = run_render(request_path, Path(dir_a))
            if rc_a != 0:
                all_errors.append(f"  [{label}] Run A failed with exit code {rc_a}")
                continue
            # Artifacts (JSON, manifest) are written next to the request file
            artifacts_folder = request_path.parent / f"artifacts_{request_path.stem}"

            # Snapshot run A's artifacts before run B overwrites them
            artifacts_a_snapshot = Path(dir_a) / "_artifacts_snapshot"
            if artifacts_folder.is_dir():
                shutil.copytree(artifacts_folder, artifacts_a_snapshot)

            rc_b = run_render(request_path, Path(dir_b))
            if rc_b != 0:
                all_errors.append(f"  [{label}] Run B failed with exit code {rc_b}")
                continue

            # Collect from output dirs (PDFs) and isolated artifact snapshots (JSON)
            jsons_a = collect_json(Path(dir_a))
            jsons_b = collect_json(Path(dir_b))
            if artifacts_a_snapshot.is_dir():
                jsons_a.update(collect_json(artifacts_a_snapshot))
            if artifacts_folder.is_dir():
                jsons_b.update(collect_json(artifacts_folder))

            # For true determinism, compare PDFs by size as a basic check
            pdfs_a = sorted(Path(dir_a).glob("*.pdf"))
            pdfs_b = sorted(Path(dir_b).glob("*.pdf"))
            if len(pdfs_a) != len(pdfs_b):
                all_errors.append(f"  [{label}] Different PDF count: {len(pdfs_a)} vs {len(pdfs_b)}")
            else:
                for pa, pb in zip(pdfs_a, pdfs_b):
                    if pa.name != pb.name:
                        all_errors.append(f"  [{label}] PDF name mismatch: {pa.name} vs {pb.name}")
                    elif pa.stat().st_size != pb.stat().st_size:
                        all_errors.append(f"  [{label}] PDF size differs: {pa.name}")

            errs = diff_results(jsons_a, jsons_b)
            if errs:
                all_errors.extend(f"  [{label}] {e}" for e in errs)
                print(f"  FAIL: {len(errs)} difference(s)")
            else:
                file_count = len(jsons_a) + len(pdfs_a)
                print(f"  PASS ({file_count} file(s) matched)")

    print()
    if all_errors:
        print(f"FAIL ({len(all_errors)}):")
        for e in all_errors:
            print(e)
        return 1

    print("PASS: All determinism checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
