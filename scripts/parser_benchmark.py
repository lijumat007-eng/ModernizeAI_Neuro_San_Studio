#!/usr/bin/env python
# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
Runs the ModernizeAI parser pipeline against a real repository and prints
per-language coverage and cross-file reference resolution stats.

Usage:
    python scripts/parser_benchmark.py <path-to-repo>
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from coded_tools.modernize.memory.memory_manager_tool import MemoryFabric
from coded_tools.modernize.parsers.pipeline import parse_repository


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo_path", help="Directory to scan and parse")
    args = parser.parse_args()

    fabric = MemoryFabric()
    t0 = time.time()
    records = fabric.raw.ingest_directory(args.repo_path)
    t1 = time.time()
    report = parse_repository(fabric)
    t2 = time.time()

    print(f"Repository: {args.repo_path}")
    print(f"Files discovered: {len(records)} (ingested in {t1 - t0:.2f}s)")
    print(f"Files parsed: {report.files_parsed} / {report.files_seen}")
    print(f"By language: {report.by_language}")
    if report.files_unsupported:
        exts = {}
        for p in report.files_unsupported:
            ext = os.path.splitext(p)[1] or "(no ext)"
            exts[ext] = exts.get(ext, 0) + 1
        print(f"Unsupported extensions: {exts}")

    error_free = sum(
        1 for r in report.results if r.parse_coverage >= 0.999
    )
    print(f"Files with zero syntax errors: {error_free} / {len(report.results)} "
          f"({100 * error_free / max(1, len(report.results)):.1f}%)")

    print(f"Total symbols: {report.total_symbols}")
    print(f"Total references: {report.total_references}")
    print(f"Resolved references: {report.resolved_references} "
          f"({100 * report.resolved_references / max(1, report.total_references):.1f}%)")
    print(f"External (out-of-repo) references: {report.external_references}")
    print(f"Parse time: {t2 - t1:.2f}s")

    if report.diagnostics:
        print(f"\nDiagnostics ({len(report.diagnostics)}):")
        for d in report.diagnostics[:20]:
            print(f"  [{d['severity']}] {d['file_path']}: {d['message']}")
        if len(report.diagnostics) > 20:
            print(f"  ... and {len(report.diagnostics) - 20} more")


if __name__ == "__main__":
    main()
