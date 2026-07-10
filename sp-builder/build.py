#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CLI генератора СП-страниц.

Примеры:
  python3 sp-builder/build.py "normative-md/SP_48.13330.2019_«СНиП 12-01-2004 Организация строительства».md" -o sp-html
  python3 sp-builder/build.py --scan            # обновить registry.json по корпусу
  python3 sp-builder/build.py <файл> --json     # дополнительно выгрузить модель в JSON
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from parser import parse_file, designation_to_slug  # noqa: E402
from renderer import Renderer  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = Path(__file__).resolve().parent / "registry.json"
SIZE_WARN = 1_500_000   # blindspot C-1: бюджет размера страницы
SIZE_FAIL = 3_000_000


def load_registry() -> dict:
    if REGISTRY_PATH.exists():
        return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    return {}


def scan_corpus() -> dict:
    """Строит реестр корпуса из имён файлов normative-md/ (обогащается вручную)."""
    old = load_registry()
    registry: dict = {}
    for f in sorted((ROOT / "normative-md").glob("SP_*.md")):
        m = re.match(r"SP_([\d.]+)_«(.+?)»?$", f.stem)
        if not m:
            continue
        designation = "СП " + m.group(1)
        inner = m.group(2).rstrip("»")
        sm = re.match(r"(СНиП\s+\S+)\s+(.*)$", inner)
        entry = {
            "slug": designation_to_slug(designation),
            "file": f.name,
            "title": (sm.group(2) if sm else inner).strip(),
            "snip": sm.group(1) if sm else None,
            "published": False,
        }
        prev = old.get(designation)
        if prev:  # сохраняем ручные поля (published, status и т.п.)
            entry.update({k: v for k, v in prev.items()
                          if k not in ("file", "title", "snip")})
        registry[designation] = entry
    return registry


def build_one(md_path: Path, out_dir: Path, dump_json: bool, strict: bool) -> Path:
    registry = load_registry()
    doc = parse_file(md_path, registry)
    meta = doc["meta"]
    slug = meta["slug"]

    q = doc["quality"]
    print(f"[i] {meta.get('designation', md_path.name)}: "
          f"formulaStubs={q['formulaStubs']} imageStubs={q['imageStubs']} "
          f"sections={len(doc['sections'])} glossary={len(doc['glossary'])} "
          f"appendices={len(doc['appendices'])} biblio={len(doc['biblio'])}")
    if strict and (q["formulaStubs"] > 0 or q["imageStubs"] > 3):
        raise SystemExit(f"[x] --strict: документ не проходит порог качества "
                         f"(formulaStubs={q['formulaStubs']}, imageStubs={q['imageStubs']})")

    overlay_path = Path(__file__).resolve().parent / "overrides" / f"{slug}.json"
    overlay = None
    if overlay_path.exists():
        overlay = json.loads(overlay_path.read_text(encoding="utf-8"))
        print(f"[i] оверлей: {overlay_path.name}")
    else:
        print(f"[!] оверлей {overlay_path.name} не найден — генерирую без TL;DR/FAQ/статуса")

    html = Renderer(doc, overlay, registry).render()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{slug}.html"
    out_path.write_text(html, encoding="utf-8")

    size = out_path.stat().st_size
    print(f"[✓] {out_path} ({size / 1024:.0f} КБ)")
    if size > SIZE_FAIL:
        print(f"[x] размер превышает жёсткий лимит {SIZE_FAIL // 1_000_000} МБ — "
              f"нужен chunking (docs/01-SP-PAGES-PLAN.md §6)")
    elif size > SIZE_WARN:
        print(f"[!] размер превышает бюджет {SIZE_WARN / 1_000_000:.1f} МБ — проверь CWV")

    if dump_json:
        jp = out_dir / f"{slug}.json"
        doc_copy = {k: v for k, v in doc.items() if k != "preamble"}
        jp.write_text(json.dumps(doc_copy, ensure_ascii=False, indent=1),
                      encoding="utf-8")
        print(f"[✓] модель: {jp}")
    return out_path


def main() -> None:
    ap = argparse.ArgumentParser(description="Генератор интерактивных HTML из СП-markdown")
    ap.add_argument("file", nargs="?", help="путь к .md из normative-md/")
    ap.add_argument("-o", "--out", default="sp-html", help="папка вывода (default: sp-html)")
    ap.add_argument("--json", action="store_true", help="выгрузить промежуточную модель")
    ap.add_argument("--strict", action="store_true", help="отказ при плохих метриках качества")
    ap.add_argument("--scan", action="store_true", help="обновить registry.json по корпусу")
    args = ap.parse_args()

    if args.scan:
        registry = scan_corpus()
        REGISTRY_PATH.write_text(
            json.dumps(registry, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"[✓] registry.json: {len(registry)} документов")
        return

    if not args.file:
        ap.error("укажите файл .md или --scan")
    build_one(Path(args.file), ROOT / args.out, args.json, args.strict)


if __name__ == "__main__":
    main()
