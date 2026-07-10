#!/usr/bin/env python3
"""
gen_html.py — Восстановленная логика оригинального gen.py.
Section-specific rendering + TOC-based subsection titles + ivory/clay CSS.
"""
import json, io, os, re, sys, html as H

# ═══ CSS (оригинальный ivory/clay с serif) ═══
CSS = r"""*{box-sizing:border-box;margin:0;padding:0}
:root{
  --ivory:#FAF9F5;--slate:#141413;--clay:#D97757;--oat:#E3DACC;
  --olive:#788C5D;--rust:#B04A3F;
  --gray-100:#F0EEE6;--gray-150:#F5F3EC;--gray-300:#D1CFC5;
  --gray-500:#87867F;--gray-700:#3D3D3A;--white:#FFF;
  --serif:ui-serif,Georgia,"Times New Roman",serif;
  --sans:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  --mono:ui-monospace,"SF Mono",Menlo,Monaco,monospace;
  --bg:var(--ivory);--ink:var(--slate);--card:var(--white);
  --border:var(--gray-300);--muted:var(--gray-500);
}
html.dark{
  --bg:#1A1A18;--ink:#E8E6E0;--card:#262624;
  --border:#3A3A36;--muted:#9A9890;
  --gray-100:#2A2A28;--gray-150:#222220;--gray-300:#3A3A36;
}
html{scroll-behavior:smooth}
body{font-family:var(--sans);background:var(--bg);color:var(--ink);
  line-height:1.6;padding:0;-webkit-font-smoothing:antialiased;font-size:15px}
.layout{display:grid;grid-template-columns:240px 1fr;max-width:1200px;margin:0 auto}
.toc{position:sticky;top:0;align-self:start;max-height:100vh;overflow-y:auto;
  padding:48px 24px 48px 32px;border-right:1px solid var(--border);font-size:13px;background:var(--bg)}
.toc h3{font-family:var(--mono);font-size:11px;text-transform:uppercase;
  letter-spacing:.08em;color:var(--muted);margin-bottom:16px}
.toc ul{list-style:none}.toc li{margin:0 0 6px}
.toc a{color:var(--ink);text-decoration:none;display:block;padding:4px 8px;
  border-radius:6px;transition:background .15s}
.toc a:hover{background:var(--gray-100);color:var(--clay)}
.main{padding:48px 56px 120px;max-width:880px}
header.doc-head{margin-bottom:48px;padding-bottom:32px;border-bottom:1.5px solid var(--border)}
.eyebrow{font-family:var(--mono);font-size:12px;text-transform:uppercase;
  letter-spacing:.08em;color:var(--clay);margin-bottom:12px}
h1.doc-title{font-family:var(--serif);font-weight:500;font-size:34px;
  line-height:1.2;letter-spacing:-.01em;margin-bottom:16px}
.doc-sub{font-size:16px;color:var(--muted);margin-bottom:24px}
.tldr{background:var(--card);border:1.5px solid var(--border);
  border-left:4px solid var(--clay);border-radius:12px;padding:20px 24px;font-size:14px}
.tldr strong{font-family:var(--serif);font-weight:500}
.sec{margin-bottom:56px;scroll-margin-top:24px}
.sec-head{margin-bottom:24px}
.sec-head .num{display:inline-flex;align-items:center;justify-content:center;
  min-width:28px;height:28px;padding:0 8px;background:var(--oat);color:var(--slate);
  font-family:var(--mono);font-size:12px;font-weight:600;border-radius:6px;
  margin-right:12px;vertical-align:middle}
html.dark .sec-head .num{color:var(--ink);background:#3A3530}
.sec-head h2{display:inline;font-family:var(--serif);font-weight:500;
  font-size:26px;letter-spacing:-.01em;vertical-align:middle}
.sec-intro{color:var(--muted);font-size:14px;margin-top:8px;max-width:640px}
.clause{margin:0 0 12px;padding-left:64px;position:relative;font-size:14.5px}
.clause .cnum{position:absolute;left:0;top:0;font-family:var(--mono);
  font-size:11px;color:var(--clay);font-weight:600;min-width:56px;text-align:left}
.ctext{display:inline}.lead{font-size:16px;color:var(--ink);margin-bottom:16px}
p.body-p{margin:0 0 12px;font-size:14.5px;line-height:1.6}
.callout{background:var(--gray-100);border:1px solid var(--border);
  border-left:3px solid var(--clay);border-radius:8px;padding:14px 18px;margin:16px 0;font-size:13.5px}
.callout-label{font-family:var(--mono);font-size:11px;text-transform:uppercase;
  letter-spacing:.06em;color:var(--clay);font-weight:600;display:block;margin-bottom:6px}
details.subsec,details.subsub{margin:16px 0;border:1.5px solid var(--border);
  border-radius:10px;background:var(--card);overflow:hidden}
details.subsec>summary,details.subsub>summary{cursor:pointer;padding:14px 18px;
  font-family:var(--serif);font-size:18px;font-weight:500;list-style:none;
  display:flex;align-items:center;gap:10px;user-select:none}
details.subsub>summary{font-size:15px;padding:10px 14px}
details.subsec>summary::before,details.subsub>summary::before{
  content:"\25B8";font-family:var(--mono);color:var(--clay);transition:transform .2s;font-size:14px}
details[open].subsec>summary::before,details[open].subsub>summary::before{transform:rotate(90deg)}
details.subsec>summary .cnum{font-family:var(--mono);font-size:12px;color:var(--clay);font-weight:600}
.subsec-body{padding:8px 18px 18px}
dl.glossary{display:grid;grid-template-columns:1fr;gap:0}
dl.glossary dt{font-family:var(--serif);font-weight:500;font-size:15px;padding:12px 0 4px;border-top:1px solid var(--border)}
dl.glossary dt:first-child{border-top:none}
dl.glossary .term-num{font-family:var(--mono);font-size:11px;color:var(--clay);margin-right:8px;font-weight:600}
dl.glossary dd{font-size:14px;color:var(--ink);padding:0 0 12px 0;margin-left:0;line-height:1.55}
ul.ref-list{list-style:none;padding:0}
ul.ref-list li{font-size:13.5px;padding:7px 0;border-bottom:1px solid var(--gray-100);line-height:1.5}
ul.ref-list li:last-child{border-bottom:none}
ol.biblio{padding-left:0;list-style:none;counter-reset:bib}
ol.biblio li{counter-increment:bib;font-size:13px;padding:8px 0 8px 34px;position:relative;border-bottom:1px solid var(--gray-100);line-height:1.5}
ol.biblio li::before{content:"["counter(bib)"]";position:absolute;left:0;font-family:var(--mono);font-size:11px;color:var(--clay);font-weight:600}
figure.tbl{margin:24px 0;border:1.5px solid var(--border);border-radius:12px;overflow:hidden;background:var(--card)}
figure.tbl figcaption{font-family:var(--mono);font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);padding:10px 16px;background:var(--gray-100);border-bottom:1px solid var(--border)}
figure.tbl table{width:100%;border-collapse:collapse;font-size:13.5px}
figure.tbl th{font-family:var(--mono);font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);text-align:left;padding:10px 14px;background:var(--gray-100);border-bottom:1.5px solid var(--border)}
figure.tbl td{padding:10px 14px;border-bottom:1px solid var(--gray-100);vertical-align:top}
figure.tbl tbody tr:last-child td{border-bottom:none}
figure.tbl tbody tr:hover{background:var(--gray-150)}
figure.fig{margin:24px 0;border:1.5px solid var(--border);border-radius:12px;overflow:hidden;background:var(--card);text-align:center}
figure.fig img{max-width:100%;height:auto;display:block;margin:0 auto}
figure.fig figcaption{font-family:var(--mono);font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);padding:10px 16px;background:var(--gray-100);border-top:1px solid var(--border)}
.eq{display:flex;justify-content:space-between;align-items:center;background:var(--gray-100);border:1px solid var(--border);border-radius:8px;padding:10px 16px;margin:12px 0;font-family:var(--mono);font-size:14px}
.eq-body{font-style:italic}.eq-num{color:var(--clay);font-weight:600;font-size:12px}
.std{font-family:var(--mono);font-size:12.5px;color:var(--olive);font-weight:600}
html.dark .std{color:#9CB87C}.ref{font-family:var(--mono);font-size:11px;color:var(--muted)}
.eqref{font-family:var(--mono);font-size:11px;color:var(--clay);font-weight:600}
.theme-toggle{position:fixed;top:16px;right:16px;z-index:100;background:var(--card);border:1.5px solid var(--border);border-radius:8px;padding:8px 14px;font-family:var(--mono);font-size:12px;cursor:pointer;color:var(--ink);transition:all .15s}
.theme-toggle:hover{border-color:var(--clay);color:var(--clay)}
footer.doc-foot{margin-top:80px;padding-top:24px;border-top:1px solid var(--border);font-size:12px;color:var(--muted);font-family:var(--mono)}
@media(max-width:900px){.layout{grid-template-columns:1fr}.toc{position:relative;max-height:none;border-right:none;border-bottom:1px solid var(--border);padding:24px}.main{padding:24px}}"""

PAGE = """<!doctype html><html lang="ru">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<script>(function(){var s=localStorage.getItem('eh-theme');if(!s)s=window.matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light';if(s==='dark')document.documentElement.classList.add('dark');})();</script>
<style>__CSS__</style></head>
<body><button class="theme-toggle" onclick="var h=document.documentElement;h.classList.toggle('dark');localStorage.setItem('eh-theme',h.classList.contains('dark')?'dark':'light');">&#9788; / &#9789;</button>
<div class="layout">__TOC__<main class="main">__HEADER____BODY__<footer class="doc-foot">Источник: __SOURCE__</footer></main></div></body></html>"""

# ═══ HELPERS (из оригинального gen.py) ═══
def esc(s): return H.escape(str(s) if s else "", quote=False)

def inline(s):
    s = esc(s)
    s = re.sub(r"\[(\d+(?:,\s*статья\s*\d+)?)\]", r'<span class="ref">[\1]</span>', s)
    s = re.sub(r"(ГОСТ(?:\s+Р)?(?:\s+\d+(?:\.\d+)*[.\-]?\d*)?)", r'<span class="std">\1</span>', s)
    s = re.sub(r"\b(СП\s*[\d.]+(?:\.\d+)*)", r'<span class="std">\1</span>', s)
    s = re.sub(r"\((\d+\.\d+)\)", r'<span class="eqref">(\1)</span>', s)
    return s

def extract_notes(text):
    notes = []; pat = re.compile(r"П\s*р\s*и\s*м\s*е\s*ч\s*а\s*н\s*и\s*(?:е|я)\s*[–\-]?\s*")
    ms = list(pat.finditer(text))
    if not ms: return text, []
    main = text[:ms[0].start()].strip()
    for i, m in enumerate(ms):
        end = ms[i+1].start() if i+1 < len(ms) else len(text)
        notes.append(text[m.end():end].strip())
    return main, notes

def render_formulas(main):
    eqs = []
    def repl(m):
        lhs, eqn = m.group(1).strip(), m.group(2)
        idx = len(eqs)
        eqs.append(f'<div class="eq"><span class="eq-body">{inline(lhs)}</span><span class="eq-num">({eqn})</span></div>')
        return f"\x00EQ{idx}\x00"
    main = re.sub(r"([A-Za-z]+\s*[=][^;()\n]+?);\s*\((\d+\.\d+)\)", repl, main)
    return main, eqs

def render_clause(num, body, sid):
    main, notes = extract_notes(body)
    main, eqs = render_formulas(main)
    main = inline(main)
    for i, eq in enumerate(eqs): main = main.replace(f"\x00EQ{i}\x00", eq)
    cid = f"{sid}-{num}" if num else sid
    cnum = f'<span class="cnum">{esc(num)}</span>' if num else ""
    out = f'<p class="clause" id="{esc(cid)}">{cnum}<span class="ctext">{main}</span></p>'
    for n in notes:
        out += f'<aside class="callout"><span class="callout-label">Примечание</span><p>{inline(n)}</p></aside>'
    return out

def split_clauses(body):
    clauses = []
    pat = re.compile(r"(?<=\S)\s+(?=(?:\d+(?:\.\d+){1,3}|[А-Я]\.\d+)\s+[А-ЯЁ«])")
    for p in pat.split(body):
        p = p.strip()
        if not p: continue
        m = re.match(r"^(\d+(?:\.\d+){1,3}|[А-Я]\.\d+)\s+(.+)$", p, re.DOTALL)
        if m: clauses.append((m.group(1), m.group(2).strip()))
        elif clauses: n, t = clauses[-1]; clauses[-1] = (n, t + " " + p)
        else: clauses.append(("", p))
    return clauses

def render_table(tbl):
    h = "".join(f"<th>{esc(c)}</th>" for c in tbl["headers"])
    rows = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in tbl["rows"])
    return (f'<figure class="tbl" id="{esc(tbl["id"])}"><figcaption>{esc(tbl.get("caption",""))}</figcaption>'
            f'<table><thead><tr>{h}</tr></thead><tbody>{rows}</tbody></table></figure>')

def render_figure(fig):
    fid = fig["id"].replace(".", "_"); cap = esc(fig.get("caption", f"Рисунок {fig['id']}"))
    return (f'<figure class="fig" id="fig-{fid}"><img src="data:image/png;base64,{fig["b64"]}" '
            f'alt="{cap}" width="{fig["w"]}" height="{fig["h"]}" loading="lazy">'
            f'<figcaption>Рисунок {esc(fig["id"])} — {cap}</figcaption></figure>')

def split_title_body(text):
    VERBS = ("следует","должны","необходимо","выполняют","проектируют","определяют",
             "размещают","предусматривают","оборудуют","используют","допускается",
             "выбирают","применяют","устанавливают","рассчитывают","назначают",
             "проверяют","учитывают","обеспечивают","требуют")
    for kw in VERBS:
        m = re.match(r"^(.{5,60}?)\s+" + re.escape(kw) + r"\b", text)
        if m: return m.group(1).strip(), text[len(m.group(1)):].strip()
    m = re.match(r"^([^.]{5,60})\.\s*(.+)$", text, re.DOTALL)
    if m: return m.group(1).strip(), m.group(2).strip()
    words = text.split()
    if len(words) > 8: return " ".join(words[:6]), " ".join(words[6:])
    return text[:40], text[40:].strip()

# ═══ SECTION-SPECIFIC RENDERERS ═══
def render_preface(body, sid):
    out = [f'<section id="{sid}" class="sec"><div class="sec-head"><span class="num">·</span>'
           f'<h2>Предисловие</h2><p class="sec-intro">Сведения о разработчике, утверждении и регистрации.</p></div>']
    for cnum, ctext in split_clauses(body):
        if cnum: out.append(render_clause(cnum, ctext, sid))
        elif ctext.strip(): out.append(f'<p class="body-p">{inline(ctext)}</p>')
    out.append('</section>')
    return "\n".join(out)

def render_intro(body, sid):
    return (f'<section id="{sid}" class="sec"><div class="sec-head"><span class="num">·</span><h2>Введение</h2></div>'
            f'<p class="lead">{inline(body)}</p></section>')

def render_simple_clauses(body, sid, num, title, tables_map, fig_map, placed):
    """Для секций 1, 4, 8, 9 — простые clauses + таблицы."""
    num_padded = str(int(num)).zfill(2) if num else "·"
    out = [f'<section id="{sid}" class="sec"><div class="sec-head"><span class="num">{esc(num_padded)}</span>'
           f'<h2>{esc(title)}</h2></div>']
    for cnum, ctext in split_clauses(body):
        if cnum:
            out.append(render_clause(cnum, ctext, sid))
            # Вставка таблиц/рисунков по ссылке
            for ref, html in list(tables_map.items()):
                if (f"таблице {ref}" in ctext.lower() or f"таблица {ref}" in ctext.lower()
                    or f"таблиц {ref}" in ctext.lower() or f"таблицей {ref}" in ctext.lower()
                    or f"таблицы {ref}" in ctext.lower()) and html not in placed:
                    out.append(html); placed.add(html)
            for fid, fhtml in list(fig_map.items()):
                if (f"рисунке {fid}" in ctext.lower() or f"рисунок {fid}" in ctext.lower()
                    or f"рисунка {fid}" in ctext.lower()) and fhtml not in placed:
                    out.append(fhtml); placed.add(fhtml)
        elif ctext.strip():
            out.append(f'<p class="body-p">{inline(ctext)}</p>')
    out.append('</section>')
    return "\n".join(out)

def render_refs(body, sid):
    """Секция 2 — список ГОСТ/СП ссылок."""
    out = [f'<section id="{sid}" class="sec"><div class="sec-head"><span class="num">02</span>'
           f'<h2>Нормативные ссылки</h2><p class="sec-intro">Перечень документов, на которые есть ссылки.</p></div>']
    # Extract intro text
    intro_m = re.match(r"^(.+?:)\s", body)
    if intro_m:
        out.append(f'<p class="lead">{inline(intro_m.group(0).strip())}</p>')
        body = body[intro_m.end():].strip()
    # Split into refs
    refs = re.split(r"(?=(?:ГОСТ(?:\s+Р)?|СП)\s*\d)", body)
    out.append('<ul class="ref-list">')
    for r in refs:
        r = r.strip()
        if not r: continue
        if "Примечание" in r or "П р и м е ч а н и е" in r:
            main, notes = extract_notes(r)
            if main.strip(): out.append(f'<li>{inline(main.strip())}</li>')
            out.append('</ul>')
            for n in notes:
                out.append(f'<aside class="callout"><span class="callout-label">Примечание</span><p>{inline(n)}</p></aside>')
        else:
            out.append(f'<li>{inline(r)}</li>')
    if not out[-1].endswith('</ul>'): out.append('</ul>')
    out.append('</section>')
    return "\n".join(out)

def render_glossary(body, sid, glossary):
    """Секция 3 — термины и определения."""
    out = [f'<section id="{sid}" class="sec"><div class="sec-head"><span class="num">03</span>'
           f'<h2>Термины и определения</h2>'
           f'<p class="sec-intro">Термины по ГОСТ Р 70214, ГОСТ Р 57618.1 и следующие.</p></div>']
    out.append('<dl class="glossary">')
    for t in glossary:
        out.append(f'<dt id="term-{esc(t["num"])}"><span class="term-num">{esc(t["num"])}</span>{inline(t["term"])}</dt>')
        out.append(f'<dd>{inline(t["definition"])}</dd>')
    out.append('</dl></section>')
    return "\n".join(out)

def render_subsections(body, sid, num, title, subsections, toc_subs, tables_map, fig_map, placed):
    """Секции 5, 6, 7 — иерархия subsections/sub-subs."""
    num_padded = str(int(num)).zfill(2)
    out = [f'<section id="{sid}" class="sec"><div class="sec-head"><span class="num">{esc(num_padded)}</span>'
           f'<h2>{esc(title)}</h2></div>']
    
    all_clauses = split_clauses(body)
    
    # Распределение clauses по подсекциям
    sub_clauses = {}
    pre_clauses = []
    for cnum, ctext in all_clauses:
        if cnum:
            parts = cnum.split(".")
            if len(parts) >= 2:
                parent = ".".join(parts[:2])
                if any(s["num"] == parent for s in subsections):
                    sub_clauses.setdefault(parent, []).append((cnum, ctext))
                    continue
        pre_clauses.append((cnum, ctext))
    
    # Pre-clauses
    for cnum, ctext in pre_clauses:
        if cnum: out.append(render_clause(cnum, ctext, sid))
        elif ctext.strip(): out.append(f'<p class="body-p">{inline(ctext)}</p>')
    
    # Subsections
    for sub in subsections:
        sub_num = sub["num"]
        sub_title = sub.get("title", sub_num)
        sub_id = f"{sid}-{sub_num.replace('.', '-')}"
        out.append(f'<details class="subsec" open id="{sub_id}">'
                   f'<summary><span class="cnum">{esc(sub_num)}</span>{esc(sub_title)}</summary>'
                   f'<div class="subsec-body">')
        
        clauses = sub_clauses.get(sub_num, [])
        # Группировка по sub-subsections
        ss_groups = {}
        remaining = []
        for cnum, ctext in clauses:
            parts = cnum.split(".")
            if len(parts) >= 3:
                ss_key = ".".join(parts[:3])
                ss_groups.setdefault(ss_key, []).append((cnum, ctext))
            else:
                remaining.append((cnum, ctext))
        
        toc_subsubs = {ss["num"]: ss for ss in sub.get("subsections", [])}
        
        # Sub-subsections
        for ss_num in sorted(ss_groups.keys(), key=lambda x: tuple(int(p) for p in x.split("."))):
            ss_clauses = ss_groups[ss_num]
            ss_info = toc_subsubs.get(ss_num, {})
            ss_title = ss_info.get("title", ss_num)
            ss_id = f"{sub_id}-{ss_num.split('.')[-1]}"
            
            # Извлечь заголовок из первого clause
            if ss_clauses:
                ext_title, body_rest = split_title_body(ss_clauses[0][1])
                if body_rest: ss_clauses[0] = (ss_clauses[0][0], body_rest)
                if ext_title and len(ext_title) > 5: ss_title = ext_title
            
            out.append(f'<details class="subsub" id="{ss_id}">'
                       f'<summary><span class="cnum">{esc(ss_num)}</span>{esc(ss_title)}</summary>')
            for cnum, ctext in ss_clauses:
                out.append(render_clause(cnum, ctext, ss_id))
                for fid, fhtml in list(fig_map.items()):
                    if (f"рисунке {fid}" in ctext.lower() or f"рисунок {fid}" in ctext.lower()
                        or f"рисунка {fid}" in ctext.lower()) and fhtml not in placed:
                        out.append(fhtml); placed.add(fhtml)
                for ref, thtml in list(tables_map.items()):
                    if (f"таблице {ref}" in ctext.lower() or f"таблица {ref}" in ctext.lower()
                        or f"таблиц {ref}" in ctext.lower() or f"таблицей {ref}" in ctext.lower()
                        or f"таблицы {ref}" in ctext.lower()) and thtml not in placed:
                        out.append(thtml); placed.add(thtml)
            out.append('</details>')
        
        # Remaining clauses in subsection
        for cnum, ctext in remaining:
            out.append(render_clause(cnum, ctext, sub_id))
        
        out.append('</div></details>')
    
    # Оставшиеся таблицы/рисунки для секции
    sec_text = body
    for fid, fhtml in list(fig_map.items()):
        if (f"рисунок {fid}" in sec_text.lower() or f"рисунке {fid}" in sec_text.lower()) and fhtml not in placed:
            out.append(fhtml); placed.add(fhtml)
    for ref, thtml in list(tables_map.items()):
        if (f"таблица {ref}" in sec_text.lower() or f"таблице {ref}" in sec_text.lower()
            or f"таблицей {ref}" in sec_text.lower() or f"таблицы {ref}" in sec_text.lower()
            or f"таблиц {ref}" in sec_text.lower()) and thtml not in placed:
            out.append(thtml); placed.add(thtml)
    
    out.append('</section>')
    return "\n".join(out)

def render_appendix(body, sid, fig_map, tables_map, placed):
    """Приложение А — clauses + figures + таблица."""
    out = [f'<section id="{sid}" class="sec"><div class="sec-head"><span class="num">А</span>'
           f'<h2>Приложение А. Расчётные характеристики яхт</h2>'
           f'<p class="sec-intro">Графики и таблица для определения параметров яхт.</p></div>']
    for cnum, ctext in split_clauses(body):
        if cnum: out.append(render_clause(cnum, ctext, sid))
        elif ctext.strip(): out.append(f'<p class="body-p">{inline(ctext)}</p>')
    # Все рисунки А.x (только не размещённые ранее)
    for fid in sorted(fig_map.keys()):
        if fid.startswith("А.") and fig_map[fid] not in placed:
            out.append(fig_map[fid]); placed.add(fig_map[fid])
    # Таблица А.1
    for ref, thtml in list(tables_map.items()):
        if ref.startswith("А.") and thtml not in placed:
            out.append(thtml); placed.add(thtml)
    out.append('</section>')
    return "\n".join(out)

def render_biblio(body, sid):
    """Библиография — нумерованный список."""
    out = [f'<section id="{sid}" class="sec"><div class="sec-head"><span class="num">§</span><h2>Библиография</h2></div>']
    refs = re.split(r"\s+(?=\[\d+\])", body)
    out.append('<ol class="biblio">')
    for r in refs:
        r = r.strip()
        if r: out.append(f'<li>{inline(r)}</li>')
    out.append('</ol></section>')
    return "\n".join(out)

# ═══ MAIN ═══
def generate_html(data, out_path):
    meta = data["meta"]; sections = data["sections"]
    tables = data["tables"]; figures = data["figures"]
    glossary = data.get("glossary", [])
    toc_subs = data.get("toc_subsections", {})

    # Maps
    fig_map = {f["id"]: render_figure(f) for f in figures}
    tables_map = {}
    for t in tables:
        m = re.search(r"([0-9А-Я]+\.[0-9А-Я]+)", t.get("caption", ""))
        if m: tables_map[m.group(1)] = render_table(t)

    # TOC
    toc = ['<nav class="toc"><h3>Содержание</h3><ul>']
    for i, sec in enumerate(sections):
        sid = f"sec-{i+1}"; num = sec.get("num",""); title = sec.get("title","")
        toc.append(f'<li><a href="#{sid}">{esc(num+" " if num else "")}{esc(title)}</a></li>')
    toc.append('</ul></nav>')

    # Header
    title = meta.get("title", "Документ")
    header = (f'<header class="doc-head"><div class="eyebrow">Свод правил · {esc(meta.get("source",""))}</div>'
              f'<h1 class="doc-title">{esc(title)}</h1>'
              f'<div class="tldr"><strong>Кратко.</strong> {esc(meta.get("source",""))}</div></header>')

    # Body — section-specific rendering
    body_parts = []
    placed = set()  # track placed figures/tables to prevent duplicates
    for i, sec in enumerate(sections):
        sid = f"sec-{i+1}"; num = sec.get("num",""); title = sec.get("title","")
        body = sec.get("body",""); subsections = sec.get("subsections", [])

        if title == "Предисловие":
            body_parts.append(render_preface(body, sid))
        elif title == "Введение":
            body_parts.append(render_intro(body, sid))
        elif num == "2":
            body_parts.append(render_refs(body, sid))
        elif num == "3":
            body_parts.append(render_glossary(body, sid, glossary))
        elif num in ("5", "6", "7"):
            body_parts.append(render_subsections(body, sid, num, title, subsections, toc_subs, tables_map, fig_map, placed))
        elif title == "Приложение А":
            body_parts.append(render_appendix(body, sid, fig_map, tables_map, placed))
        elif title == "Библиография":
            body_parts.append(render_biblio(body, sid))
        else:
            body_parts.append(render_simple_clauses(body, sid, num, title, tables_map, fig_map, placed))

    # Unplaced figures/tables
    for fhtml in fig_map.values():
        if fhtml not in placed: body_parts.append(fhtml); placed.add(fhtml)
    for thtml in tables_map.values():
        if thtml not in placed: body_parts.append(thtml); placed.add(thtml)

    # Assemble
    page = PAGE
    page = page.replace("__TITLE__", esc(title))
    page = page.replace("__CSS__", CSS)
    page = page.replace("__TOC__", "\n".join(toc))
    page = page.replace("__HEADER__", header)
    page = page.replace("__BODY__", "\n".join(body_parts))
    page = page.replace("__SOURCE__", esc(meta.get("source", "")))

    with io.open(out_path, "w", encoding="utf-8") as f:
        f.write(page)
    return len(page)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python gen_html.py work/doc.json output/doc.html")
        sys.exit(1)
    with io.open(sys.argv[1], "r", encoding="utf-8") as f:
        data = json.load(f)
    size = generate_html(data, sys.argv[2])
    print(f"  Generated: {sys.argv[2]} ({size//1024} KB)")
