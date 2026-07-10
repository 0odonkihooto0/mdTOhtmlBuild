#!/usr/bin/env python3
"""pdf_extract.py — text from .md/firecrawl, figures from PyMuPDF, TOC auto-detect."""
import fitz, io, os, re, sys, json, base64

SRC_PDF = sys.argv[1] if len(sys.argv) > 1 else r"C:\HTMLart\pdf-to-html\input\СП_док476010.pdf"
OUT = sys.argv[2] if len(sys.argv) > 2 else r"C:\HTMLart\pdf-to-html\work\test.json"

NAMED = {"Предисловие","Введение","Содержание","Библиография",
         "Приложение А","Приложение Б","Приложение В"}

# ═══════════════════════════════════════════════════════════
# 0. FIND OR CREATE .md FOR THIS PDF
# ═══════════════════════════════════════════════════════════
basename = os.path.splitext(os.path.basename(SRC_PDF))[0]
SRC_MD = None

candidates = [
    os.path.join(os.path.dirname(SRC_PDF), basename + ".md"),
    os.path.join(os.path.dirname(os.path.dirname(SRC_PDF)), basename + "_struct.md"),
    os.path.join(os.path.dirname(os.path.dirname(SRC_PDF)), basename + ".md"),
    os.path.join(r"C:\HTMLart", basename + "_struct.md"),
    os.path.join(r"C:\HTMLart", basename + ".md"),
]
for cand in candidates:
    if os.path.exists(cand) and os.path.getsize(cand) > 100:
        SRC_MD = cand
        print(f"    Found .md: {os.path.basename(cand)}")
        break

if not SRC_MD:
    service_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "service")
    sys.path.insert(0, service_dir)
    try:
        from parser import ensure_markdown
        md_path = ensure_markdown(SRC_PDF)
        if md_path:
            SRC_MD = md_path
    except ImportError:
        pass

if not SRC_MD:
    print(f"ERROR: No .md file and parser unavailable for {basename}")
    print(f"  Put .md in: {os.path.dirname(SRC_PDF)}")
    print(f"  Or: cd C:\\parser\\parser && npm run dev  (then re-run)")
    print(f"  Or: set FIRECRAWL_API_KEY in environment")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════
# 1. READ & PREPARE MARKDOWN
# ═══════════════════════════════════════════════════════════
print(f">>> Reading markdown...")
with io.open(SRC_MD, "r", encoding="utf-8") as f:
    raw = f.read()

# Fix Hangul math letters (firecrawl artifact)
HANGUL = {
    "푏":"b","퐿":"L","푧":"z","푇":"T","퐵":"B","푉":"V","푚":"m","푓":"f","푑":"d",
    "ℎ":"h","퐷":"D","퐶":"C","퐴":"A","푟":"r","푘":"k","푛":"n","푙":"l",
    "푁":"N","푥":"x","푦":"y","푠":"s","푝":"p","휉":"xi","휓":"psi","푞":"q","푢":"u","푡":"t",
}
for k in sorted(HANGUL, key=len, reverse=True):
    raw = raw.replace(k, HANGUL[k])
raw = re.sub(r"#\s*((?:\d+\.)*\d+)", r"(\1)", raw)
raw = re.sub(r"[ \t]{2,}", " ", raw)
raw = raw.replace(r"\[", "[").replace(r"\]", "]")

# Structure: split into lines
raw = re.sub(r"\s(?=(\d{1,2}(?:\.\d{1,2}){0,2})\s+[А-ЯЁ])", r"\n", raw)
raw = re.sub(r"([.!?])\s+(?=[А-ЯЁ«])", r"\1\n", raw)
raw = re.sub(r"\n{3,}", "\n\n", raw)
lines = [ln.strip() for ln in raw.split("\n") if ln.strip()]
print(f"    Lines: {len(lines)}")

# ═══════════════════════════════════════════════════════════
# 2. PARSE TOC
# ═══════════════════════════════════════════════════════════
toc_subsections = {}
toc_sections = {}
in_toc = False
for ln in lines:
    if ln.endswith("Содержание") or ln == "Содержание":
        in_toc = True; continue
    if not in_toc: continue
    if ln.startswith("Введение") or ln == "Введение": break
    if re.match(r"^\d{1,2}\s+[А-ЯЁ]", ln) and "......" not in ln and "…" not in ln: break
    if not ln.strip(): continue
    clean = re.sub(r"[\.…]{2,}\s*\d*$", "", ln).strip()
    if not clean: continue
    m = re.match(r"^(\d+(?:\.\d+){0,2})\s+(.+?)$", clean)
    if m:
        num = m.group(1); title = m.group(2).strip()
        if "." in num: toc_subsections[num] = title
        else: toc_sections[num] = title
print(f"    TOC: {len(toc_sections)} sections, {len(toc_subsections)} subsections")

# ═══════════════════════════════════════════════════════════
# 3. SPLIT INTO SECTIONS
# ═══════════════════════════════════════════════════════════
SECTION_ANCHORS = [
    ("Предисловие","","Предисловие"),
    ("Введение","","Введение"),
    *[(f"{n} {toc_sections.get(str(n),'')}", str(n), toc_sections.get(str(n),f"Section {n}"))
      for n in range(1, 10)],
    ("Приложение А","","Приложение А"),
    ("Библиография","","Библиография"),
]

# Find Введение — only process after it (skip TOC)
intro_idx = next((i for i, ln in enumerate(lines) if ln == "Введение" or ln.startswith("Введение ")), 0)

buckets = {}
current = None
for ln in lines[intro_idx+1:]:
    if "......" in ln or "…." in ln: continue
    matched = None
    for anchor, num, title in SECTION_ANCHORS:
        if ln.startswith(anchor):
            matched = (num, title)
            buckets.setdefault(matched, []).append(ln[len(anchor):].strip())
            break
    if matched: current = matched
    elif current: buckets[current].append(ln)

# Add preface from before intro
if intro_idx:
    pre = []
    for i, ln in enumerate(lines[:intro_idx]):
        if ln.rstrip().endswith("Предисловие"):
            for ln2 in lines[i+1:]:
                if ln2 in ("Содержание","Введение") or "......" in ln2: break
                pre.append(ln2)
    if pre: buckets[("","Предисловие")] = pre
    buckets.setdefault(("","Введение"), [])

sections = []
for (num, title), body_lines in buckets.items():
    body = "\n".join(b for b in body_lines if b).strip()
    body = re.sub(r"\bСП\s*\d+(?:\.\d+)*\s*\d{1,2}\b", "", body)
    # Удалить текст таблиц из body (оставить только clauses)
    # Таблицы распознаём по паттерну "Т а б л и ц а N.M"
    body = re.sub(r"Т\s*а\s*б\s*л\s*и\s*ц\s*а\s*\d+[\.\d]*.*?(?=\d+\.\d+\s+[А-ЯЁ]|$)", "", body, flags=re.DOTALL)
    # Удалить сырые данные таблиц (строки с "IV" и цифрами)
    body = re.sub(r"\n\d+\s+[А-ЯЁ].*?IV\s*\d+", "", body)
    body = re.sub(r"\s{2,}", " ", body)
    if not body and title not in NAMED: continue

    subs = []
    if num:
        for tnum, ttitle in sorted(toc_subsections.items(),
                                     key=lambda x: tuple(int(p) for p in x[0].split("."))):
            parts = tnum.split(".")
            if parts[0] == num and len(parts) == 2:
                subs.append({"num":tnum,"title":ttitle,"body":"","subsections":[]})
            elif parts[0] == num and len(parts) == 3 and subs:
                parent = ".".join(parts[:2])
                if subs[-1]["num"] == parent:
                    subs[-1]["subsections"].append({"num":tnum,"title":ttitle,"body":""})

    sections.append({
        "num": num if title not in NAMED else "",
        "title": title, "body": body, "subsections": subs, "level": 1,
    })

# Разделить Приложение А и Библиографию если они слиты
for s in sections:
    if s["title"] == "Приложение А" and "Библиография" in s["body"]:
        idx = s["body"].find("Библиография")
        biblio_body = s["body"][idx + len("Библиография"):].strip()
        s["body"] = s["body"][:idx].strip()
        sections.append({
            "num": "", "title": "Библиография",
            "body": biblio_body, "subsections": [], "level": 1,
        })
        break

def sort_key(s):
    if s["num"]: return (0, int(s["num"]))
    return (1, {"Предисловие":0,"Введение":1,"Приложение А":2,"Библиография":3}.get(s["title"],99))
sections.sort(key=sort_key)
print(f"    Sections: {len(sections)}")

# ═══════════════════════════════════════════════════════════
# 4. TABLES
# ═══════════════════════════════════════════════════════════
tables = [
    {"id":"tbl-4-1","caption":"Таблица 4.1 — Классы ответственности и сроки службы ГТС",
     "headers":["№","Гидротехническое сооружение","Класс","Срок службы, лет"],
     "rows":[["1","Временные (некапитальные) причальные сооружения","IV","5"],
             ["2","Плавучие причалы, муринги, буи, закольные сваи","IV","20"],
             ["3","Стационарные (постоянные) причальные сооружения","IV","25"],
             ["4","Берегоукрепительные сооружения","IV","25"],
             ["5","Плавучие элементы оградительных сооружений","III","25"],
             ["6","Оградительные сооружения (молы, волноломы, дамбы)","III","50"],
             ["7","Настилы, заменяемые элементы, декор","—","10"]]},
    {"id":"tbl-5-1","caption":"Таблица 5.1 — Запас от волновых воздействий z₂",
     "headers":["Длина расчётного судна","z₂, м"],
     "rows":[["Lс ≤ 8 м","0,2"],["8 < Lс ≤ 24 м","0,3"],["24 < Lс ≤ 50 м","0,4"]]},
    {"id":"tbl-5-2","caption":"Таблица 5.2 — Диаметр кранцев",
     "headers":["Расчётная длина судна, м","fd, м"],
     "rows":[["< 6","0,15"],["6–8","0,2"],["8–12","0,25"],["12–16","0,35"],
             ["16–24","0,5"],["24–45","0,6"],["46–60","0,9"],["61–75","1,2"],["76–91+","1,5"]]},
    {"id":"tbl-5-3","caption":"Таблица 5.3 — Допустимые высоты волн",
     "headers":["Длина судна","h 5% (1/год), м","h 1% (1/25 лет), м"],
     "rows":[["Lс ≤ 8 м","0,2","0,3"],["8 < Lс ≤ 24 м","0,3","0,4"],["Lс > 24 м","0,4","0,5"]]},
    {"id":"tbl-A-1","caption":"Таблица А.1 — Надводные площади парусности",
     "headers":["L, м","Моторные лоб.","Моторные бок.","Парусные лоб.","Парусные бок."],
     "rows":[["8","5","16","4","11"],["10","7","22","5","15"],["12","11","29","6","20"],
             ["15","18","45","9","28"],["18","22","64","11","40"],["20","24","76","12","44"],
             ["25","30","95","15","60"],["30","45","120","35","92"],["35","54","167","36","122"],
             ["40","78","213","40","182"],["45","85","264","50","210"],["50","90","285","60","249"]]},
]

# ═══════════════════════════════════════════════════════════
# 5. FIGURES via PyMuPDF
# ═══════════════════════════════════════════════════════════
print(">>> PyMuPDF: extracting figures...")
pdf = fitz.open(SRC_PDF)
fig_pages = {}
for pnum in range(pdf.page_count):
    pt = pdf[pnum].get_text("text")
    for m in re.finditer(r"(?:Рисунок|Figure)\s*([\d]+\.\d+|[А-Я]\.\d+)\s*[\u2013\-]", pt):
        fid = m.group(1)
        rest = pt[m.end():m.end()+200]
        cm = re.match(r"([^.\n]{5,120})", rest)
        cap = cm.group(1).strip() if cm else ""
        if fid not in fig_pages: fig_pages[fid] = (pnum, cap)

figures = []
for fid, (pnum, cap) in sorted(fig_pages.items()):
    page = pdf[pnum]
    x0=y0=float("inf"); x1=y1=float("-inf")
    for d in page.get_drawings():
        r=d["rect"]
        if r.width<5 or r.height<5: continue
        x0=min(x0,r.x0);y0=min(y0,r.y0);x1=max(x1,r.x1);y1=max(y1,r.y1)
    for b in page.get_text("dict")["blocks"]:
        if b.get("type")==1:
            bb=fitz.Rect(b["bbox"])
            if bb.width>20 and bb.height>20: x0=min(x0,bb.x0);y0=min(y0,bb.y0);x1=max(x1,bb.x1);y1=max(y1,bb.y1)
    for img_info in page.get_images():
        for r in page.get_image_rects(img_info[0]):
            if r.width>20 and r.height>20: x0=min(x0,r.x0);y0=min(y0,r.y0);x1=max(x1,r.x1);y1=max(y1,r.y1)
    if x0==float("inf"): clip=fitz.Rect(0,0,page.rect.width,page.rect.height*0.55)
    else:
        pad=15; clip=fitz.Rect(max(0,x0-pad),max(0,y0-pad),min(page.rect.width,x1+pad),min(page.rect.height,y1+pad))
    if clip.width<50 or clip.height<50: clip=fitz.Rect(0,0,page.rect.width,page.rect.height*0.55)
    mat=fitz.Matrix(3.0,3.0)
    pix=page.get_pixmap(matrix=mat,clip=clip)
    b64=base64.b64encode(pix.tobytes("png")).decode("ascii")
    figures.append({"id":fid,"caption":cap,"b64":b64,"w":pix.width,"h":pix.height,"page":pnum+1})
    pix=None
pdf.close()
print(f"    Figures: {len(figures)}")

# ═══════════════════════════════════════════════════════════
# 6. GLOSSARY — парсим термины из секции 3
# ═══════════════════════════════════════════════════════════
glossary = []
for s in sections:
    if s["num"] == "3":
        body = s.get("body","")
        # Удаляем intro строку перед терминами
        intro_m = re.match(r"^.*?определения[:\.]?\s*", body)
        if intro_m: body = body[intro_m.end():]
        # Парсим термины: "3.1term:definition" или "3.1 term: definition"
        # Разделяем по паттерну "3.N" в начале слова
        term_parts = re.split(r"(?=(?:^|\s)(3\.\d+)\s*)", body)
        for p in term_parts:
            p = p.strip()
            if not p: continue
            m = re.match(r"^(3\.\d+)\s*(.+)", p, re.DOTALL)
            if m:
                num = m.group(1)
                rest = m.group(2).strip()
                # Разделяем term:definition по первому двоеточию или тире
                cm = re.match(r"^([^:\n—–]{3,80})[:\n—–]\s*(.+)$", rest, re.DOTALL)
                if cm:
                    glossary.append({
                        "num": num,
                        "term": cm.group(1).strip(),
                        "definition": cm.group(2).strip()[:500],
                    })
                else:
                    glossary.append({"num": num, "term": rest[:60], "definition": ""})
print(f"    Glossary: {len(glossary)}")

# ═══════════════════════════════════════════════════════════
# 7. SAVE
# ═══════════════════════════════════════════════════════════
result = {
    "meta":{"source":os.path.basename(SRC_PDF),"title": sections[0]["title"] if sections else "Document"},
    "sections":sections, "tables":tables, "figures":figures,
    "glossary":glossary, "toc_subsections":toc_subsections,
}
with io.open(OUT, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False)
print(f"\nSaved: {OUT} ({os.path.getsize(OUT)//1024} KB)")
