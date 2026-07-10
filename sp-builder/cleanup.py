# -*- coding: utf-8 -*-
"""Чистка Docling-артефактов в markdown-текстах СП.

Правила: исправляем только форму (глифы, разрядку, переносы, мусорные строки),
никогда не трогаем числовые значения и формулировки норм.
"""
from __future__ import annotations

import re

# Docling мапит математические курсивные буквы в хангыль-кодпоинты.
# Таблица перенесена из pdf-to-html/pdf_extract.py.
HANGUL = {
    "푏": "b", "퐿": "L", "푧": "z", "푇": "T", "퐵": "B", "푉": "V", "푚": "m",
    "푓": "f", "푑": "d", "ℎ": "h", "퐷": "D", "퐶": "C", "퐴": "A", "푟": "r",
    "푘": "k", "푛": "n", "푙": "l", "푁": "N", "푥": "x", "푦": "y", "푠": "s",
    "푝": "p", "휉": "ξ", "휓": "ψ", "푞": "q", "푢": "u", "푡": "t",
}

# Разряженные ключевые слова из PDF-вёрстки: «Т а б л и ц а» → «Таблица»
_SPACED_WORDS = ["Таблица", "Примечание", "Примечания", "СВОД ПРАВИЛ"]

# Отдельно стоящие номера страниц и римские цифры колонтитулов
_PAGE_NUM_RE = re.compile(r"^\s*(?:\d{1,3}|[IVXLC]{1,5})\s*$")

# Плоские степени единиц: «м 3 /с» → «м³/с». Только после самих единиц измерения —
# иначе портится обычный текст («Часть 2.» ≠ «Часть²»).
_SUPERSCRIPT_RE = re.compile(r"(?<![а-яёa-z])(мм|см|дм|км|м)\s([23])(?![0-9.,]?\d)")
_SUP_MAP = {"2": "²", "3": "³"}


def _unspace_word(word: str) -> re.Pattern:
    # «Т а б л и ц а» — буквы через одиночные пробелы
    pattern = r"\s?".join(re.escape(ch) for ch in word.replace(" ", ""))
    return re.compile(pattern)


def clean_text(text: str) -> str:
    """Чистка всего исходного текста до разбиения на строки."""
    for k in sorted(HANGUL, key=len, reverse=True):
        text = text.replace(k, HANGUL[k])
    # экранированные скобки из Docling
    text = text.replace(r"\[", "[").replace(r"\]", "]")
    return text


def clean_line(line: str) -> str | None:
    """Чистка одной строки. None — строку нужно выбросить."""
    line = line.rstrip()
    if _PAGE_NUM_RE.match(line):
        return None
    # неразрывные и двойные пробелы схлопываем ДО поиска разрядки
    # (markdown-таблицы не трогаем)
    line = line.replace(" ", " ")
    if not line.lstrip().startswith("|"):
        line = re.sub(r"[ \t]{2,}", " ", line)
    # разрядка ключевых слов: «Т а б л и ц а» → «Таблица»
    if " " in line:
        for word in _SPACED_WORDS:
            spaced = " ".join(word.replace(" ", ""))
            if spaced in line:
                line = line.replace(spaced, word)
    # степени единиц: «м 3 /с» → «м³/с» (только после единиц измерения)
    line = _SUPERSCRIPT_RE.sub(lambda m: m.group(1) + _SUP_MAP[m.group(2)], line)
    return line


def clean_lines(text: str) -> list[str]:
    text = clean_text(text)
    out: list[str] = []
    for raw in text.split("\n"):
        line = clean_line(raw)
        if line is None:
            continue
        out.append(line)
    return out
