# -*- coding: utf-8 -*-
"""Парсер Docling-markdown СП → структурная модель документа.

Модель (dict, JSON-совместимая) — контракт для рендереров (standalone HTML
сейчас, Next.js-роут в komplid-marketing потом), см. docs/01-SP-PAGES-PLAN.md §2.2.
"""
from __future__ import annotations

import re
from pathlib import Path

from cleanup import clean_lines

# ── Регулярные выражения структуры ──────────────────────────────────────────

HEADING_RE = re.compile(r"^##\s+(.*)$")
# «## 8 Производство…», «## 8.2 Исполнительная документация», «## 3.53»
NUM_HEADING_RE = re.compile(r"^(\d{1,2})(?:\.(\d{1,2}))?(?:\.(\d{1,2}))?\s*(.*)$")
APPENDIX_RE = re.compile(r"^Приложение\s+([А-Я])\b\s*(.*)$")
APPENDIX_SUB_RE = re.compile(r"^([А-Я])\.(\d{1,2})\s+(.+)$")
# пункт: «4.1 Текст», «- 4.1 Текст», «8.2.3 Текст»
CLAUSE_RE = re.compile(r"^(?:-\s*)?(\d{1,2}\.\d{1,2}(?:\.\d{1,2})?)\s+(\S.*)$", re.S)
BARE_NUM_RE = re.compile(r"^(?:-\s*)?(\d{1,2}\.\d{1,2}(?:\.\d{1,2})?)$")
# буллет: «- текст» и «-текст» (Docling теряет пробел)
BULLET_RE = re.compile(r"^-\s*(\S.*)$")
BIB_ITEM_RE = re.compile(r"^\[(\d+)\]\s*(.+)$", re.S)
TERM_RE = re.compile(r"^(?:(\d{1,2}\.\d{1,2})\s+)?(.+?)\s*:\s*(.+)$", re.S)
SOURCE_REF_RE = re.compile(r"^\[[^\]]+\]$")

DESIGNATION_RE = re.compile(r"СП\s+(\d+\.\d+(?:\.\d+)?\.(\d{4}))")
APPROVAL_RE = re.compile(
    r"УТВЕРЖДЕН\s+приказом\s+(.+?)\s+от\s+(\d+\s+\w+\s+\d{4})\s*г\.?\s*№?\s*([\d/]+\S*)"
    r"(?:\s+и\s+введен\s+в\s+действие\s+с\s+(\d+\s+\w+\s+\d{4}))?",
    re.S,
)

MONTHS = {
    "января": "01", "февраля": "02", "марта": "03", "апреля": "04",
    "мая": "05", "июня": "06", "июля": "07", "августа": "08",
    "сентября": "09", "октября": "10", "ноября": "11", "декабря": "12",
}


def ru_date_iso(s: str) -> str | None:
    m = re.match(r"(\d+)\s+(\w+)\s+(\d{4})", s.strip())
    if not m or m.group(2).lower() not in MONTHS:
        return None
    return f"{m.group(3)}-{MONTHS[m.group(2).lower()]}-{int(m.group(1)):02d}"


def designation_to_slug(designation: str) -> str:
    """«СП 48.13330.2019» → «sp-48-13330-2019» — публичный контракт, не менять."""
    return "sp-" + re.sub(r"[^\d]+", "-", designation).strip("-")


def anchor_for_clause(num: str) -> str:
    """«8.2.3» → «p-8-2-3» — публичный контракт, не менять."""
    return "p-" + num.replace(".", "-")


# ── Блочная сегментация ──────────────────────────────────────────────────────

def split_blocks(lines: list[str]) -> list[dict]:
    """Строки → блоки: heading | table | para. Списки остаются строками в para."""
    blocks: list[dict] = []
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        m = HEADING_RE.match(line)
        if m:
            blocks.append({"t": "heading", "text": m.group(1).strip()})
            i += 1
            continue
        if line.lstrip().startswith("|"):
            rows = []
            while i < n and lines[i].lstrip().startswith("|"):
                rows.append(lines[i].strip())
                i += 1
            blocks.append({"t": "table", "rows": rows})
            continue
        # параграф: до пустой строки / заголовка / таблицы / нового пункта списка.
        # Docling часто НЕ отделяет соседние пункты списка пустой строкой —
        # поэтому строка, начинающаяся с «- », всегда открывает новый блок.
        def is_list_start(s: str) -> bool:
            return bool(re.match(r"^-\s*\S", s))

        para: list[str] = [lines[i].strip()]
        i += 1
        while i < n and lines[i].strip() and not HEADING_RE.match(lines[i]) \
                and not lines[i].lstrip().startswith("|") \
                and not is_list_start(lines[i]):
            para.append(lines[i].strip())
            i += 1
        blocks.append({"t": "para", "text": "\n".join(para)})
    return blocks


def parse_table(rows: list[str]) -> dict | None:
    """GFM-таблица → {header: [...], body: [[...]]}. None — мусор (TOC с точками)."""
    def cells(row: str) -> list[str]:
        return [c.strip() for c in row.strip().strip("|").split("|")]

    parsed = [cells(r) for r in rows]
    # выбрасываем разделительную строку |---|---|
    body = [r for r in parsed if not all(re.fullmatch(r":?-{2,}:?", c or "-") for c in r)]
    if not body:
        return None
    # вырожденная TOC-таблица: одна колонка, точки-лидеры
    joined = " ".join(c for r in body for c in r)
    if "……" in joined or joined.count(".....") > 2:
        return None
    header, data = body[0], body[1:]
    if not data:  # таблица из одной строки — рендерим без шапки
        return {"header": [], "body": [header]}
    return {"header": header, "body": data}


# ── Основной парсер ──────────────────────────────────────────────────────────

class SpParser:
    def __init__(self, md_path: Path, registry: dict | None = None):
        self.path = Path(md_path)
        self.registry = registry or {}
        self.warnings: list[str] = []

    # -- метаданные ------------------------------------------------------------
    def _meta_from_filename(self) -> dict:
        # SP_48.13330.2019_«СНиП 12-01-2004 Организация строительства».md
        name = self.path.stem
        meta: dict = {}
        m = re.match(r"SP_([\d.]+)_«(.+)»?$", name)
        if m:
            meta["designation"] = "СП " + m.group(1)
            inner = m.group(2).rstrip("»")
            sm = re.match(r"(СНиП\s+\S+)\s+(.*)$", inner)
            if sm:
                meta["snip"] = sm.group(1)
                meta["title"] = sm.group(2).strip()
            else:
                meta["title"] = inner.strip()
        return meta

    def _meta_from_preamble(self, text: str, meta: dict) -> None:
        if "designation" not in meta:
            dm = DESIGNATION_RE.search(text)
            if dm:
                meta["designation"] = "СП " + dm.group(1)
        am = APPROVAL_RE.search(text)
        if am:
            meta["approval"] = {
                "authority": re.sub(r"\s+", " ", am.group(1)).strip(),
                "date": ru_date_iso(am.group(2)),
                "order": "№ " + am.group(3).rstrip(".,"),
                "effective": ru_date_iso(am.group(4)) if am.group(4) else None,
            }

    # -- разбор ------------------------------------------------------------------
    def parse(self) -> dict:
        raw = self.path.read_text(encoding="utf-8")
        lines = clean_lines(raw)
        blocks = split_blocks(lines)

        meta = self._meta_from_filename()
        doc: dict = {
            "meta": meta,
            "intro": [],          # блоки «Введения»
            "sections": [],       # дерево разделов
            "glossary": [],       # термины §3
            "appendices": [],
            "biblio": [],
            "keywords": "",
            "quality": {"formulaStubs": raw.count("formula-not-decoded"),
                         "imageStubs": raw.count("<!-- image -->"),
                         "warnings": self.warnings},
        }

        designation = meta.get("designation", "")
        # Колонтитулы: «## СП 48.13330.2019» и заголовки-повторы названия
        title_upper = meta.get("title", "").upper()

        state = "preamble"
        preamble_text: list[str] = []
        cur_section: dict | None = None     # текущий topлевел-раздел
        cur_sub: dict | None = None         # текущий подраздел
        cur_appendix: dict | None = None
        expected_section = 1
        pending_num: str | None = None      # «3.53» из вырожденного заголовка

        def content_target() -> list:
            """Куда класть контент-блоки в текущем состоянии."""
            if state == "appendix":
                return (cur_appendix.get("_cur_sub") or cur_appendix)["blocks"]
            if cur_sub is not None:
                return cur_sub["blocks"]
            if cur_section is not None:
                return cur_section["blocks"]
            return doc["intro"]

        def close_section() -> None:
            nonlocal cur_section, cur_sub
            cur_sub = None
            cur_section = None

        is_terms = False  # находимся в разделе «Термины и определения»

        for blk in blocks:
            t = blk["t"]

            # ── ЗАГОЛОВКИ ──────────────────────────────────────────────
            if t == "heading":
                text = blk["text"].strip()
                bare = re.sub(r"\s+", " ", text)

                # колонтитулы и повторы названия — везде мусор
                if designation and bare.startswith(designation):
                    continue
                if bare in ("СВОД ПРАВИЛ", "Предисловие", "Сведения о своде правил",
                            "Содержание"):
                    if bare == "Содержание":
                        state = "toc"
                    continue
                if title_upper and bare.upper() == title_upper:
                    continue
                if bare.startswith("СНиП "):
                    continue
                if bare == "Введение":
                    state = "intro"
                    continue
                if bare == "Библиография":
                    state = "biblio"
                    close_section()
                    continue
                if bare.startswith("УДК"):
                    state = "trailing"
                    continue
                if bare == "Исполнитель":
                    state = "trailing"
                    continue

                am = APPENDIX_RE.match(bare)
                if am:
                    state = "appendix"
                    close_section()
                    cur_appendix = {"letter": am.group(1),
                                    "title": am.group(2).strip(),
                                    "id": f"pril-{_translit_letter(am.group(1))}",
                                    "subs": [], "blocks": [], "_cur_sub": None}
                    doc["appendices"].append(cur_appendix)
                    continue

                if state == "appendix" and cur_appendix is not None:
                    # первый заголовок после «Приложение X» без своего названия — это название
                    if not cur_appendix["title"] and not NUM_HEADING_RE.match(bare):
                        cur_appendix["title"] = bare
                        continue
                    sm = APPENDIX_SUB_RE.match(bare)
                    if sm and sm.group(1) == cur_appendix["letter"]:
                        sub = {"num": f"{sm.group(1)}.{sm.group(2)}",
                               "title": sm.group(3).strip(),
                               "id": f"{cur_appendix['id']}-{sm.group(2)}",
                               "blocks": []}
                        cur_appendix["subs"].append(sub)
                        cur_appendix["_cur_sub"] = sub
                        continue
                    # повторяющаяся шапка таблиц приложения Б
                    if bare == "Наименование исполнительной документации":
                        continue
                    # промоутнутые элементы: «## 9 Исполнительные…» → пункт списка,
                    # «## Система водоотведения» → под-заголовок группы
                    if re.match(r"^\d", bare):
                        target = content_target()
                        if target and target[-1]["t"] == "list":
                            target[-1]["items"].append(bare)
                        else:
                            target.append({"t": "list", "items": [bare]})
                    else:
                        content_target().append({"t": "subhead", "text": bare})
                    continue

                nm = NUM_HEADING_RE.match(bare)
                if nm and state in ("preamble", "toc", "intro", "body"):
                    n1, n2, n3, title = nm.group(1), nm.group(2), nm.group(3), nm.group(4)
                    if not title.strip() and n2 is not None:
                        # вырожденный «## 3.53» — номер термина/пункта
                        pending_num = f"{n1}.{n2}" + (f".{n3}" if n3 else "")
                        continue
                    if n2 is None:
                        num = int(n1)
                        if num == expected_section or (state != "body" and num == 1):
                            state = "body"
                            expected_section = num + 1
                            cur_section = {"num": n1, "title": title.strip(),
                                           "id": f"sec-{n1}", "blocks": [],
                                           "subs": [], "clauses": []}
                            cur_sub = None
                            doc["sections"].append(cur_section)
                            is_terms = "термины" in title.lower()
                            continue
                        # число вне последовательности — промоутнутый мусор
                        content_target().append({"t": "para", "text": bare})
                        continue
                    # подраздел N.M
                    if cur_section is not None and n1 == cur_section["num"] and n3 is None:
                        cur_sub = {"num": f"{n1}.{n2}", "title": title.strip(),
                                   "id": f"sec-{n1}-{n2}", "blocks": []}
                        cur_section["subs"].append(cur_sub)
                        continue
                    content_target().append({"t": "para", "text": bare})
                    continue

                # заголовок без числа в теле — под-заголовок
                if state in ("intro", "body"):
                    content_target().append({"t": "subhead", "text": bare})
                continue

            # ── ТАБЛИЦЫ ────────────────────────────────────────────────
            if t == "table":
                if state in ("preamble", "toc", "trailing"):
                    continue
                parsed = parse_table(blk["rows"])
                if parsed:
                    content_target().append({"t": "table", **parsed})
                continue

            # ── ПАРАГРАФЫ ──────────────────────────────────────────────
            text = blk["text"].strip()
            if not text:
                continue
            if state in ("preamble", "toc"):
                preamble_text.append(text)
                continue
            if state == "trailing":
                if text.lower().startswith("ключевые слова"):
                    doc["keywords"] = re.sub(r"^ключевые слова:\s*", "", text,
                                             flags=re.I).strip()
                continue
            if state == "biblio":
                bm = BIB_ITEM_RE.match(text)
                if bm:
                    doc["biblio"].append({"n": int(bm.group(1)),
                                          "text": re.sub(r"\s*\n\s*", " ", bm.group(2))})
                elif doc["biblio"]:
                    doc["biblio"][-1]["text"] += " " + re.sub(r"\s*\n\s*", " ", text)
                continue

            if pending_num:
                text = f"{pending_num} {text}"
                pending_num = None

            # заголовок приложения, не ставший markdown-заголовком (Приложение И)
            if state == "appendix" and cur_appendix is not None \
                    and not cur_appendix["title"] and len(text) < 200 \
                    and not re.match(r"^[-\d]", text):
                cur_appendix["title"] = re.sub(r"\s*\n\s*", " ", text)
                continue

            if is_terms:
                self._feed_term(doc["glossary"], text)
                continue

            self._feed_content(content_target(), text, cur_section)

        self._meta_from_preamble("\n".join(preamble_text), meta)
        meta["slug"] = designation_to_slug(meta.get("designation", self.path.stem))
        doc["preamble"] = preamble_text
        return doc

    # -- термины -----------------------------------------------------------------
    def _feed_term(self, glossary: list, text: str) -> None:
        text = re.sub(r"\s*\n\s*", " ", text)
        text = re.sub(r"^-\s*", "", text)  # термин может быть пунктом списка
        if SOURCE_REF_RE.match(text):
            if glossary:
                glossary[-1]["source"] = text.strip("[]")
            return
        # вводная фраза раздела
        if text.lower().startswith("в настоящем своде правил"):
            return
        bm = BARE_NUM_RE.match(text)
        if bm:
            glossary.append({"num": bm.group(1), "term": "", "def": ""})
            return
        tm = TERM_RE.match(text)
        if tm and (tm.group(1) or (glossary and not glossary[-1]["term"])
                   or len(tm.group(2)) < 90):
            num, term, definition = tm.group(1), tm.group(2), tm.group(3)
            term = term.lstrip("- ").strip()
            if not num and glossary and not glossary[-1]["term"]:
                glossary[-1]["term"] = term
                glossary[-1]["def"] = definition.strip()
                return
            glossary.append({"num": num or "", "term": term,
                             "def": definition.strip()})
            return
        # продолжение определения
        if glossary:
            glossary[-1]["def"] = (glossary[-1]["def"] + " " + text).strip()

    # -- контент разделов ----------------------------------------------------------
    def _feed_content(self, target: list, text: str, cur_section: dict | None) -> None:
        # многострочный параграф может содержать пункт + продолжение
        text = re.sub(r"\s*\n\s*", " ", text)
        cm = CLAUSE_RE.match(text)
        if cm and cur_section is not None \
                and cm.group(1).split(".")[0] == cur_section["num"]:
            num, body = cm.group(1), cm.group(2)
            target.append({"t": "clause", "num": num,
                           "id": anchor_for_clause(num), "text": body.strip()})
            return
        bm = BARE_NUM_RE.match(text)
        if bm and cur_section is not None \
                and bm.group(1).split(".")[0] == cur_section["num"]:
            target.append({"t": "clause", "num": bm.group(1),
                           "id": anchor_for_clause(bm.group(1)), "text": ""})
            return
        lm = BULLET_RE.match(text)
        if lm or text.startswith("-"):
            item = text.lstrip("- ").lstrip("-")
            # прикрепляем к предыдущему пункту как подсписок
            if target and target[-1]["t"] in ("clause", "list"):
                if target[-1]["t"] == "clause":
                    target.append({"t": "list", "items": [item]})
                else:
                    target[-1]["items"].append(item)
                return
            target.append({"t": "list", "items": [item]})
            return
        # продолжение предыдущего пункта или обычный абзац
        if target and target[-1]["t"] == "clause" and not target[-1]["text"]:
            target[-1]["text"] = text
            return
        # Docling рвёт строки посреди предложения: абзац с маленькой буквы —
        # продолжение предыдущего пункта списка или пункта раздела
        if target and text and text[0].islower():
            last = target[-1]
            if last["t"] == "list":
                last["items"][-1] += " " + text
                return
            if last["t"] == "clause":
                last["text"] += " " + text
                return
            if last["t"] == "para":
                last["text"] += " " + text
                return
        target.append({"t": "para", "text": text})


_LETTER_TRANSLIT = {
    "А": "a", "Б": "b", "В": "v", "Г": "g", "Д": "d", "Е": "e", "Ж": "zh",
    "И": "i", "К": "k", "Л": "l", "М": "m", "Н": "n", "П": "p", "Р": "r",
    "С": "s", "Т": "t", "У": "u", "Ф": "f", "Х": "h", "Ц": "c", "Ш": "sh",
    "Щ": "shch", "Э": "e2", "Ю": "yu", "Я": "ya",
}


def _translit_letter(letter: str) -> str:
    return _LETTER_TRANSLIT.get(letter, letter.lower())


def parse_file(md_path: str | Path, registry: dict | None = None) -> dict:
    return SpParser(Path(md_path), registry).parse()
