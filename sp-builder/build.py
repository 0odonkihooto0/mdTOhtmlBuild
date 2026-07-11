#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CLI генератора СП-страниц.

Примеры:
  # один документ (картинки восстанавливаются из downloads_faufcc автоматически)
  python3 sp-builder/build.py "normative-md/SP_48.13330.2019_«СНиП 12-01-2004 Организация строительства».md" -o sp-html

  # ВСЕ документы из папки → HTML в папку (одной командой, без ИИ)
  python3 sp-builder/build.py --all -i normative-md -o output

  python3 sp-builder/build.py --scan            # обновить registry.json по корпусу
  python3 sp-builder/build.py <файл> --json     # дополнительно выгрузить модель в JSON
"""
from __future__ import annotations

import argparse
import html as H
import json
import re
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from cleanup import clean_lines  # noqa: E402
from parser import parse_file, designation_to_slug  # noqa: E402
from pdf_images import resolve_images  # noqa: E402
from renderer import Renderer  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = Path(__file__).resolve().parent / "registry.json"
DEFAULT_PDF_DIR = ROOT / "downloads_faufcc"
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


# ── Автопроверка полноты (blindspot: «ничего не теряется?») ──────────────────

_NORM_RE = re.compile(r"[^0-9a-zа-яё]+")


def _norm(s: str) -> str:
    return _NORM_RE.sub("", s.lower())


def _whitelisted(line: str, meta: dict) -> bool:
    """Легитимные потери: TOC с точками-лидерами, колонтитулы, повторы названия."""
    s = line.strip().lstrip("#").strip()
    if not s:
        return True
    if "……" in s or s.count("....") >= 1 or "…." in s:
        return True  # строки «Содержания»
    if re.search(r"…\s*\d*\s*$", s):
        return True  # строка оглавления с точками-лидерами и номером страницы
    if s in ("Предисловие", "Сведения о своде правил", "Содержание",
             "Наименование исполнительной документации", "Издание официальное",
             "Актуализированная редакция"):
        return True
    if s.startswith(("МИНИСТЕРСТВО ", "СВОД ПРАВИЛ", "СНиП ")):
        return True  # шапка титульного листа (утверждение и так в преамбуле)
    # повтор названия капсом (титульный лист в середине документа)
    cyr = re.sub(r"[^а-яА-ЯёЁ ]+", "", s).strip()
    if cyr and cyr == cyr.upper():
        key = _norm(s)[:18]
        if len(key) >= 10 and key in _norm(meta.get("title", "")):
            return True
    # англоязычный перевод названия на титульном листе
    if re.fullmatch(r"[A-Za-z0-9 ,.\-()']+", s) and len(s) < 130:
        return True
    designation = meta.get("designation", "")
    if designation and s.startswith(designation):
        return True  # колонтитулы
    title = meta.get("title", "")
    if title and s.upper() == title.upper():
        return True  # повтор названия капсом
    if s.startswith("СНиП ") and len(s) < 40:
        return True
    if s in ("<!-- image -->", "<!-- formula-not-decoded -->"):
        return True  # стабы обрабатываются отдельными блоками
    return False


def audit_coverage(src_lines: list[str], html_text: str, meta: dict) -> list[str]:
    """Строки источника, текст которых не найден в итоговом HTML."""
    text = re.sub(r"<script.*?</script>", " ", html_text, flags=re.S)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    hay = _norm(H.unescape(text))

    lost: list[str] = []
    for ln in src_lines:
        s = ln.strip()
        if not s or _whitelisted(s, meta):
            continue
        cells = ([c.strip() for c in s.strip("|").split("|")]
                 if s.startswith("|") else [s.lstrip("#- ").strip()])
        for cell in cells:
            if _whitelisted(cell, meta):
                continue
            key = _norm(cell)
            if len(key) < 12:
                continue
            if key[:70] not in hay:
                lost.append(cell[:110])
                break
    return lost


# ── Сборка одного документа ──────────────────────────────────────────────────

def build_one(md_path: Path, out_dir: Path, *, dump_json: bool = False,
              strict: bool = False, verbose: bool = False,
              pdf_dir: Path | None = None, quiet: bool = False,
              registry: dict | None = None) -> dict:
    if registry is None:
        registry = load_registry()
    doc = parse_file(md_path, registry)
    meta = doc["meta"]
    slug = meta["slug"]

    def log(msg: str) -> None:
        if not quiet:
            print(msg)

    q = doc["quality"]
    log(f"[i] {meta.get('designation', md_path.name)}: "
        f"formulaStubs={q['formulaStubs']} imageStubs={q['imageStubs']} "
        f"sections={len(doc['sections'])} glossary={len(doc['glossary'])} "
        f"appendices={len(doc['appendices'])} biblio={len(doc['biblio'])}")

    overlay_path = Path(__file__).resolve().parent / "overrides" / f"{slug}.json"
    overlay = None
    if overlay_path.exists():
        overlay = json.loads(overlay_path.read_text(encoding="utf-8"))
        log(f"[i] оверлей: {overlay_path.name}")
    else:
        log(f"[!] оверлей {overlay_path.name} не найден — генерирую без TL;DR/FAQ/статуса")

    # восстановление картинок из исходного PDF (если есть)
    images = resolve_images(md_path, pdf_dir, out_dir, slug, q["imageStubs"])
    if images:
        log(f"[i] картинки из PDF: {len(images)}/{q['imageStubs']}")

    html = Renderer(doc, overlay, registry, images).render()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{slug}.html"
    out_path.write_text(html, encoding="utf-8")

    # аудит полноты: каждая содержательная строка источника должна быть в HTML
    src_lines = clean_lines(md_path.read_text(encoding="utf-8"))
    lost = audit_coverage(src_lines, html, meta)
    q["lostLines"] = len(lost)
    if lost:
        log(f"[!] полнота: {len(lost)} строк источника не найдены в HTML"
            + ("" if verbose else " (подробности: --verbose)"))
        if verbose:
            for line in lost[:40]:
                log(f"      • {line}")

    size = out_path.stat().st_size
    status = "ok"
    log(f"[✓] {out_path} ({size / 1024:.0f} КБ)")
    if size > SIZE_FAIL:
        status = "warn"
        log(f"[x] размер превышает жёсткий лимит {SIZE_FAIL // 1_000_000} МБ — "
            f"нужен chunking (docs/01-SP-PAGES-PLAN.md §6)")
    elif size > SIZE_WARN:
        status = "warn"
        log(f"[!] размер превышает бюджет {SIZE_WARN / 1_000_000:.1f} МБ — проверь CWV")
    if q["formulaStubs"] > 0 or (q["imageStubs"] - len(images)) > 0 or lost:
        status = "warn" if status == "ok" else status
    if strict and status != "ok":
        raise SystemExit(f"[x] --strict: {slug} не проходит порог качества "
                         f"(formulaStubs={q['formulaStubs']}, "
                         f"imagesUnresolved={q['imageStubs'] - len(images)}, "
                         f"lostLines={len(lost)})")

    if dump_json:
        jp = out_dir / f"{slug}.json"
        doc_copy = {k: v for k, v in doc.items() if k != "preamble"}
        jp.write_text(json.dumps(doc_copy, ensure_ascii=False, indent=1),
                      encoding="utf-8")
        log(f"[✓] модель: {jp}")

    return {"slug": slug, "designation": meta.get("designation", ""),
            "file": md_path.name, "status": status, "sizeKb": size // 1024,
            "formulaStubs": q["formulaStubs"], "imageStubs": q["imageStubs"],
            "imagesResolved": len(images), "lostLines": len(lost),
            "sections": len(doc["sections"]), "glossary": len(doc["glossary"])}


# ── Батч: все .md из папки → HTML в папку ────────────────────────────────────

def build_all(in_dir: Path, out_dir: Path, *, pdf_dir: Path | None,
              limit: int | None, verbose: bool) -> None:
    files = sorted(in_dir.glob("*.md"))
    if limit:
        files = files[:limit]
    if not files:
        raise SystemExit(f"[x] в {in_dir} нет .md файлов")
    print(f"[i] батч: {len(files)} документов из {in_dir} → {out_dir}\n")
    # все документы прогона окажутся в одной папке — упоминания «СП NNN»
    # в текстах становятся рабочими кросс-ссылками (published в памяти)
    registry = load_registry()
    file_names = {f.name for f in files}
    for entry in registry.values():
        if entry.get("file") in file_names:
            entry["published"] = True
    t0 = time.time()
    report: list[dict] = []
    for i, f in enumerate(files, 1):
        try:
            r = build_one(f, out_dir, pdf_dir=pdf_dir, quiet=True,
                          registry=registry)
        except Exception as e:  # не прерываем прогон
            r = {"slug": f.stem[:60], "file": f.name, "status": "fail",
                 "error": f"{type(e).__name__}: {e}"}
            if verbose:
                traceback.print_exc()
        report.append(r)
        mark = {"ok": "✓", "warn": "!", "fail": "✗"}[r["status"]]
        extra = ""
        if r["status"] == "warn":
            bits = []
            if r.get("formulaStubs"):
                bits.append(f"формулы:{r['formulaStubs']}")
            unres = r.get("imageStubs", 0) - r.get("imagesResolved", 0)
            if unres > 0:
                bits.append(f"картинки без PDF:{unres}")
            if r.get("lostLines"):
                bits.append(f"потери:{r['lostLines']}")
            if r.get("sizeKb", 0) > SIZE_WARN // 1024:
                bits.append(f"размер:{r['sizeKb']}КБ")
            extra = " (" + ", ".join(bits) + ")"
        elif r["status"] == "fail":
            extra = f" ({r['error']})"
        print(f"  [{mark}] {i}/{len(files)} {r['slug']}{extra}")

    counts = {s: sum(1 for r in report if r["status"] == s)
              for s in ("ok", "warn", "fail")}
    rp = out_dir / "build-report.json"
    rp.write_text(json.dumps(
        {"generatedAt": time.strftime("%Y-%m-%d %H:%M:%S"),
         "input": str(in_dir), "counts": counts, "docs": report},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n[✓] за {time.time() - t0:.0f} с: ok={counts['ok']} "
          f"warn={counts['warn']} fail={counts['fail']} → отчёт {rp}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Генератор интерактивных HTML из СП-markdown")
    ap.add_argument("file", nargs="?", help="путь к .md из normative-md/")
    ap.add_argument("--all", action="store_true",
                    help="собрать все .md из папки -i в папку -o")
    ap.add_argument("-i", "--input", default=None,
                    help="папка с .md для --all (default: input/, если нет — normative-md/)")
    ap.add_argument("-o", "--out", default=None,
                    help="папка вывода (default: output/ для --all, sp-html/ для одного файла)")
    ap.add_argument("--pdf-dir", default=None,
                    help=f"папка с исходными PDF для восстановления картинок "
                         f"(default: {DEFAULT_PDF_DIR.name}/, если существует)")
    ap.add_argument("--json", action="store_true", help="выгрузить промежуточную модель")
    ap.add_argument("--strict", action="store_true", help="отказ при плохих метриках качества")
    ap.add_argument("--verbose", action="store_true", help="подробности: потерянные строки, трейсбеки")
    ap.add_argument("--limit", type=int, default=None, help="ограничить число документов в --all")
    ap.add_argument("--scan", action="store_true", help="обновить registry.json по корпусу")
    args = ap.parse_args()

    if args.scan:
        registry = scan_corpus()
        REGISTRY_PATH.write_text(
            json.dumps(registry, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"[✓] registry.json: {len(registry)} документов")
        return

    pdf_dir = Path(args.pdf_dir) if args.pdf_dir else (
        DEFAULT_PDF_DIR if DEFAULT_PDF_DIR.is_dir() else None)

    if args.all:
        in_dir = Path(args.input) if args.input else (
            ROOT / "input" if (ROOT / "input").is_dir() else ROOT / "normative-md")
        out_dir = Path(args.out) if args.out else ROOT / "output"
        build_all(in_dir, out_dir, pdf_dir=pdf_dir, limit=args.limit,
                  verbose=args.verbose)
        return

    if not args.file:
        ap.error("укажите файл .md, либо --all, либо --scan")
    out_dir = Path(args.out) if args.out else ROOT / "sp-html"
    build_one(Path(args.file), out_dir, dump_json=args.json, strict=args.strict,
              verbose=args.verbose, pdf_dir=pdf_dir)


if __name__ == "__main__":
    main()
