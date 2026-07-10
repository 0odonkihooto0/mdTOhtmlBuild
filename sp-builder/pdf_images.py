# -*- coding: utf-8 -*-
"""Извлечение растровых изображений из исходных PDF (downloads_faufcc/).

Docling выбросил картинки при конвертации PDF→md, оставив стабы `<!-- image -->`.
Здесь извлекаем растры из PDF в порядке чтения и сопоставляем со стабами по порядку.
Требует pymupdf (единственная опциональная зависимость проекта): pip install pymupdf
"""
from __future__ import annotations

from pathlib import Path

# фильтр мелочи: логотипы, линейки, декоративные элементы
MIN_WIDTH = 200
MIN_HEIGHT = 120
MAX_WIDTH = 1400


def extract_images(pdf_path: Path, out_dir: Path) -> list[Path]:
    """Извлекает растровые изображения PDF в порядке чтения → out_dir/fig-N.png."""
    # кэш: PDF не меняются — повторные прогоны переиспользуют извлечённое
    if out_dir.is_dir():
        cached = sorted(out_dir.glob("fig-*.png"),
                        key=lambda p: int(p.stem.split("-")[1]))
        if cached:
            return cached

    import fitz  # PyMuPDF

    doc = fitz.open(str(pdf_path))
    pixmaps = []
    seen: set[int] = set()
    for page in doc:
        for info in page.get_image_info(xrefs=True):
            xref = info.get("xref", 0)
            if not xref or xref in seen:
                continue  # повтор xref = колонтитул/логотип на каждой странице
            seen.add(xref)
            if info["width"] < MIN_WIDTH or info["height"] < MIN_HEIGHT:
                continue
            pix = fitz.Pixmap(doc, xref)
            if pix.colorspace is None:  # трафаретные маски
                continue
            if pix.n - pix.alpha > 3:  # CMYK и пр. → RGB
                pix = fitz.Pixmap(fitz.csRGB, pix)
            if pix.alpha:
                pix = fitz.Pixmap(pix, 0)
            while pix.width > MAX_WIDTH:  # даунскейл вдвое до бюджета
                pix.shrink(1)
            pixmaps.append(pix)
    doc.close()

    paths: list[Path] = []
    if pixmaps:
        out_dir.mkdir(parents=True, exist_ok=True)
        for i, pix in enumerate(pixmaps, 1):
            p = out_dir / f"fig-{i}.png"
            pix.save(str(p))
            paths.append(p)
    return paths


def resolve_images(md_path: Path, pdf_dir: Path | None, out_dir: Path,
                   slug: str, stub_count: int) -> dict[int, str]:
    """Стаб №n → относительный путь картинки. Пустой dict — деградация в плашки."""
    if stub_count == 0 or pdf_dir is None:
        return {}
    pdf = pdf_dir / (md_path.stem + ".pdf")
    if not pdf.exists():
        print(f"[!] PDF не найден: {pdf.name} — картинки останутся плашками")
        return {}
    try:
        import fitz  # noqa: F401
    except ImportError:
        print("[!] pymupdf не установлен (pip install pymupdf) — картинки останутся плашками")
        return {}
    paths = extract_images(pdf, out_dir / "img" / slug)
    if len(paths) != stub_count:
        print(f"[!] стабов картинок в md: {stub_count}, растров в PDF: {len(paths)} — "
              f"сопоставляю по порядку, лишние стабы получат плашку")
    mapping: dict[int, str] = {}
    for n in range(1, stub_count + 1):
        if n <= len(paths):
            mapping[n] = f"img/{slug}/{paths[n - 1].name}"
    return mapping
