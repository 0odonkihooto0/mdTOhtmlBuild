#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run.py — Pipeline orchestrator for pdf-to-html.

Scans the input/ folder for PDF files and processes each one through:
  1. pdf_extract.py → work/<basename>.json (text + tables + figures)
  2. html_gen.py    → output/<basename>.html (self-contained Komplid HTML)

Usage:
  python run.py                    # process all PDFs in input/
  python run.py --force            # re-process even if output exists
  python run.py --file doc.pdf     # process a single file
  python run.py --clean            # clear work/ and output/ first

Requirements:
  pip install PyMuPDF
"""
import os, sys, glob, time, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(HERE, "input")
OUTPUT_DIR = os.path.join(HERE, "output")
WORK_DIR = os.path.join(HERE, "work")

# Auto-create folders
for d in [INPUT_DIR, OUTPUT_DIR, WORK_DIR]:
    os.makedirs(d, exist_ok=True)


def find_pdfs():
    """Find all .pdf files in input/ (case-insensitive)."""
    patterns = [
        os.path.join(INPUT_DIR, "*.pdf"),
        os.path.join(INPUT_DIR, "*.PDF"),
        os.path.join(INPUT_DIR, "**", "*.pdf"),
        os.path.join(INPUT_DIR, "**", "*.PDF"),
    ]
    seen = set()
    for pat in patterns:
        for f in glob.glob(pat, recursive=True):
            seen.add(os.path.abspath(f))
    return sorted(seen)


def process_one(pdf_path, force=False):
    """Process a single PDF file through the full pipeline."""
    basename = os.path.splitext(os.path.basename(pdf_path))[0]
    json_path = os.path.join(WORK_DIR, basename + ".json")
    html_path = os.path.join(OUTPUT_DIR, basename + ".html")

    if os.path.exists(html_path) and not force:
        print(f"  SKIP (already exists, use --force): {basename}.html")
        return "skipped"

    t0 = time.time()

    # Step 1: Extract (pdf_extract handles text+figures, auto-finds .md or calls parser)
    print(f"  [1/2] Extracting: {basename}")
    ret = subprocess.call(
        [sys.executable, os.path.join(HERE, "pdf_extract.py"), pdf_path, json_path]
    )
    if ret != 0:
        print(f"  ERROR: pdf_extract failed for {basename}")
        return "error"

    # Step 2: Generate HTML
    print(f"  [2/2] Generating HTML: {basename}")
    ret = subprocess.call(
        [sys.executable, os.path.join(HERE, "gen_html.py"), json_path, html_path]
    )
    if ret != 0:
        print(f"  ERROR: html_gen failed for {basename}")
        return "error"

    elapsed = time.time() - t0
    size_kb = os.path.getsize(html_path) // 1024
    print(f"  DONE: {basename}.html ({size_kb} KB, {elapsed:.1f}s)")
    return "done"


def main():
    args = sys.argv[1:]
    force = "--force" in args
    clean = "--clean" in args
    single = None
    if "--file" in args:
        idx = args.index("--file")
        if idx + 1 < len(args):
            single = args[idx + 1]

    if clean:
        import shutil
        for d in [WORK_DIR, OUTPUT_DIR]:
            if os.path.exists(d):
                shutil.rmtree(d)
            os.makedirs(d)
        print("Cleared work/ and output/")

    if single:
        if not os.path.isabs(single):
            single = os.path.join(INPUT_DIR, single)
        if not os.path.exists(single):
            print(f"File not found: {single}")
            sys.exit(1)
        pdfs = [os.path.abspath(single)]
    else:
        pdfs = find_pdfs()

    if not pdfs:
        print("No PDF files found in input/")
        print(f"  Put your .pdf files in: {INPUT_DIR}")
        sys.exit(0)

    print(f"\n{'=' * 60}")
    print(f"  pdf-to-html pipeline")
    print(f"  Found {len(pdfs)} PDF file(s)")
    print(f"{'=' * 60}\n")

    stats = {"done": 0, "skipped": 0, "error": 0}
    t_total = time.time()
    for pdf in pdfs:
        print(f"\n>>> {os.path.basename(pdf)}")
        result = process_one(pdf, force=force)
        stats[result] += 1

    print(f"\n{'=' * 60}")
    print(f"  COMPLETE: {stats['done']} done, {stats['skipped']} skipped, "
          f"{stats['error']} errors")
    print(f"  Total time: {time.time() - t_total:.1f}s")
    print(f"  Output: {OUTPUT_DIR}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
