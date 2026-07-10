#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""html_gen.py v2 — renders hierarchical section structure to Komplid HTML."""
import json, io, os, re, sys, html as H

# ── CSS ──
CSS = r"""*{box-sizing:border-box;margin:0;padding:0}
:root{
  --font-ui:'Inter',system-ui,-apple-system,"Segoe UI",sans-serif;
  --font-mono:'JetBrains Mono',ui-monospace,Menlo,Monaco,monospace;
  --r-2:6px;--r-3:8px;--r-4:12px;--r-pill:999px;
  --bg:oklch(0.985 0.002 85);--ink:oklch(0.28 0.02 255);
  --card:#FFFFFF;--border:oklch(0.90 0.004 255);
  --muted:oklch(0.55 0.01 255);--inset:oklch(0.95 0.003 85);
  --accent:oklch(0.72 0.14 65);--accent-soft:oklch(0.72 0.14 65 / 0.14);
  --accent-ink:oklch(0.45 0.10 65);--ok:oklch(0.62 0.14 145);
  --warn:oklch(0.72 0.14 75);--err:oklch(0.58 0.18 25);--info:oklch(0.55 0.14 250);
  --shadow-1:0 1px 3px oklch(0.20 0.01 255 / 0.06);--shadow-2:0 4px 12px oklch(0.20 0.01 255 / 0.08);
}
html[data-theme="dark"]{
  --bg:oklch(0.17 0.01 255);--ink:oklch(0.94 0.004 255);
  --card:oklch(0.22 0.01 255);--border:oklch(0.32 0.01 255);
  --muted:oklch(0.62 0.01 255);--inset:oklch(0.20 0.01 255);
  --accent:oklch(0.75 0.13 65);--accent-soft:oklch(0.75 0.13 65 / 0.18);
  --accent-ink:oklch(0.82 0.10 65);--shadow-1:0 1px 3px oklch(0 0 0 / 0.3);--shadow-2:0 4px 12px oklch(0 0 0 / 0.4);
}
html{scroll-behavior:smooth}
body{font-family:var(--font-ui);background:var(--bg);color:var(--ink);
  line-height:1.6;padding:0;-webkit-font-smoothing:antialiased;font-size:15px}
.layout{display:grid;grid-template-columns:240px 1fr;max-width:1200px;margin:0 auto;gap:0}
.toc{position:sticky;top:0;align-self:start;max-height:100vh;overflow-y:auto;
  padding:48px 24px 48px 32px;border-right:1px solid var(--border);font-size:13px;background:var(--bg)}
.toc h3{font-family:var(--font-mono);font-size:11px;text-transform:uppercase;
  letter-spacing:.10em;color:var(--muted);margin-bottom:16px;font-weight:600}
.toc ul{list-style:none}.toc li{margin:0 0 4px}
.toc a{color:var(--ink);text-decoration:none;display:block;padding:5px 10px;
  border-radius:var(--r-2);transition:.15s;font-size:13px}
.toc a:hover{background:var(--accent-soft);color:var(--accent-ink)}
.main{padding:48px 56px 120px;max-width:880px}
header.doc-head{margin-bottom:48px;padding-bottom:28px;border-bottom:1px solid var(--border)}
.eyebrow{font-family:var(--font-mono);font-size:11px;text-transform:uppercase;
  letter-spacing:.12em;color:var(--accent);margin-bottom:12px;font-weight:600}
h1.doc-title{font-family:var(--font-ui);font-weight:600;font-size:32px;
  line-height:1.25;letter-spacing:-.02em;margin-bottom:14px}
.doc-sub{font-size:15px;color:var(--muted);margin-bottom:24px}
.tldr{background:var(--card);border:1px solid var(--border);border-left:3px solid var(--accent);
  border-radius:var(--r-3);padding:20px 24px;font-size:14px;box-shadow:var(--shadow-1)}
.tldr strong{font-weight:600}
.sec{margin-bottom:56px;scroll-margin-top:24px}
.sec-head{margin-bottom:24px}
.sec-head .num{display:inline-flex;align-items:center;justify-content:center;
  min-width:26px;height:26px;padding:0 8px;background:var(--accent-soft);
  color:var(--accent-ink);font-family:var(--font-mono);font-size:11px;font-weight:600;
  border-radius:var(--r-2);margin-right:10px;vertical-align:middle;letter-spacing:.04em}
.sec-head h2{display:inline;font-family:var(--font-ui);font-weight:600;
  font-size:24px;letter-spacing:-.01em;vertical-align:middle}
.clause{margin:0 0 12px;padding-left:64px;position:relative;font-size:14.5px}
.clause .cnum{position:absolute;left:0;top:1px;font-family:var(--font-mono);
  font-size:11px;color:var(--accent);font-weight:600;min-width:56px;text-align:left;letter-spacing:.02em}
.ctext{display:inline}
p.body-p{margin:0 0 12px;font-size:14.5px;line-height:1.6}
.callout{background:var(--inset);border:1px solid var(--border);border-left:3px solid var(--accent);
  border-radius:var(--r-2);padding:14px 18px;margin:16px 0;font-size:13.5px}
.callout-label{font-family:var(--font-mono);font-size:10px;text-transform:uppercase;
  letter-spacing:.10em;color:var(--accent);font-weight:600;display:block;margin-bottom:6px}
details.subsec,details.subsub{margin:16px 0;border:1px solid var(--border);
  border-radius:var(--r-3);background:var(--card);overflow:hidden;box-shadow:var(--shadow-1)}
details.subsec>summary,details.subsub>summary{cursor:pointer;padding:14px 18px;
  font-family:var(--font-ui);font-size:17px;font-weight:600;list-style:none;
  display:flex;align-items:center;gap:10px;user-select:none}
details.subsub>summary{font-size:14px;padding:10px 14px}
details.subsec>summary::before,details.subsub>summary::before{
  content:"\25B8";font-family:var(--font-mono);color:var(--accent);transition:transform .2s;font-size:13px}
details[open].subsec>summary::before,details[open].subsub>summary::before{transform:rotate(90deg)}
details.subsec>summary .cnum{font-family:var(--font-mono);font-size:11px;
  color:var(--accent);font-weight:600;letter-spacing:.02em}
.subsec-body,subsub-body{padding:8px 18px 18px}
dl.glossary{display:grid;grid-template-columns:1fr;gap:0}
dl.glossary dt{font-family:var(--font-ui);font-weight:600;font-size:14.5px;
  padding:12px 0 4px;border-top:1px solid var(--border)}
dl.glossary dt:first-child{border-top:none}
dl.glossary .term-num{font-family:var(--font-mono);font-size:10px;color:var(--accent);
  margin-right:8px;font-weight:600;letter-spacing:.04em}
dl.glossary dd{font-size:14px;color:var(--ink);padding:0 0 12px 0;margin-left:0;line-height:1.55}
figure.tbl{margin:24px 0;border:1px solid var(--border);border-radius:var(--r-3);
  overflow:hidden;background:var(--card);box-shadow:var(--shadow-1)}
figure.tbl figcaption{font-family:var(--font-mono);font-size:10px;text-transform:uppercase;
  letter-spacing:.08em;color:var(--muted);padding:10px 16px;background:var(--inset);
  border-bottom:1px solid var(--border);font-weight:600}
figure.tbl table{width:100%;border-collapse:collapse;font-size:13.5px}
figure.tbl th{font-family:var(--font-mono);font-size:10px;text-transform:uppercase;
  letter-spacing:.06em;color:var(--muted);text-align:left;padding:10px 14px;
  background:var(--inset);border-bottom:1px solid var(--border);font-weight:600}
figure.tbl td{padding:10px 14px;border-bottom:1px solid var(--inset);vertical-align:top}
figure.tbl tbody tr:last-child td{border-bottom:none}
figure.tbl tbody tr:hover{background:var(--inset)}
figure.fig{margin:24px 0;border:1px solid var(--border);border-radius:var(--r-3);
  overflow:hidden;background:var(--card);text-align:center;box-shadow:var(--shadow-1)}
figure.fig img{max-width:100%;height:auto;display:block;margin:0 auto}
figure.fig figcaption{font-family:var(--font-mono);font-size:10px;text-transform:uppercase;
  letter-spacing:.08em;color:var(--muted);padding:10px 16px;background:var(--inset);
  border-top:1px solid var(--border);font-weight:600}
.std{font-family:var(--font-mono);font-size:12px;color:var(--ok);font-weight:600}
html[data-theme="dark"] .std{color:oklch(0.70 0.14 145)}
.ref{font-family:var(--font-mono);font-size:10px;color:var(--muted)}
.eqref{font-family:var(--font-mono);font-size:10px;color:var(--accent);font-weight:600}
.theme-toggle{position:fixed;top:16px;right:16px;z-index:100;
  background:var(--card);border:1px solid var(--border);border-radius:var(--r-2);
  padding:8px 14px;font-family:var(--font-mono);font-size:11px;cursor:pointer;
  color:var(--ink);transition:.15s;font-weight:600;letter-spacing:.04em}
.theme-toggle:hover{border-color:var(--accent);color:var(--accent)}
footer.doc-foot{margin-top:80px;padding-top:24px;border-top:1px solid var(--border);
  font-size:11px;color:var(--muted);font-family:var(--font-mono)}
@media(max-width:900px){
  .layout{grid-template-columns:1fr}
  .toc{position:relative;max-height:none;border-right:none;border-bottom:1px solid var(--border);padding:24px}
  .main{padding:24px}
}"""

PAGE_TEMPLATE = """<!doctype html>
<html lang="ru" data-theme="light">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<script>
(function(){
  var s=localStorage.getItem('komplid-theme');
  if(!s)s=window.matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light';
  document.documentElement.setAttribute('data-theme',s);
})();
</script>
<style>__CSS__</style></head>
<body>
<button class="theme-toggle" onclick="
  var h=document.documentElement;
  var cur=h.getAttribute('data-theme');
  var next=cur==='dark'?'light':'dark';
  h.setAttribute('data-theme',next);
  localStorage.setItem('komplid-theme',next);
">THEME</button>
<div class="layout">
__TOC__
<main class="main">
__HEADER__
__BODY__
<footer class="doc-foot">Источник: __SOURCE__ · Docling + PyMuPDF · Komplid design</footer>
</main></div></body></html>"""

# ── Helpers ──
def esc(s):
    return H.escape(str(s) if s else "", quote=False)

def inline(s):
    s = esc(s)
    s = re.sub(r"\[(\d+(?:,\s*статья\s*\d+)?)\]", r'<span class="ref">[\1]</span>', s)
    s = re.sub(r"(ГОСТ(?:\s+Р)?(?:\s+\d+(?:\.\d+)*[.\-]?\d*)?)", r'<span class="std">\1</span>', s)
    s = re.sub(r"\b(СП\s*[\d.]+(?:\.\d+)*)", r'<span class="std">\1</span>', s)
    s = re.sub(r"\((\d+\.\d+)\)", r'<span class="eqref">(\1)</span>', s)
    return s

def render_clause(num, text, sid):
    cid = f"{sid}-{num}" if num else sid
    cnum = f'<span class="cnum">{esc(num)}</span>' if num else ""
    # Note callout
    main, note = text, ""
    nm = re.search(r"(П\s*р\s*и\s*м\s*е\s*ч\s*а\s*н\s*и\s*[ея]\s*[–\-]?\s*)", main)
    if nm:
        note = main[nm.end():].strip()
        main = main[:nm.start()].strip()
    html = f'<p class="clause" id="{esc(cid)}">{cnum}<span class="ctext">{inline(main)}</span></p>'
    if note:
        html += f'<aside class="callout"><span class="callout-label">Примечание</span><p>{inline(note)}</p></aside>'
    return html

def render_table(tbl):
    h = "".join(f"<th>{esc(c)}</th>" for c in tbl.get("headers", []))
    rows = "".join(
        "<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>"
        for r in tbl.get("rows", [])
    )
    return (f'<figure class="tbl" id="{esc(tbl["id"])}">'
            f'<figcaption>{esc(tbl.get("caption",""))}</figcaption>'
            f'<table><thead><tr>{h}</tr></thead><tbody>{rows}</tbody></table>'
            f'</figure>')

def render_figure(fig):
    fid = fig["id"].replace(".", "_")
    cap = esc(fig.get("caption", f"Рисунок {fig['id']}"))
    return (f'<figure class="fig" id="fig-{fid}">'
            f'<img src="data:image/png;base64,{fig["b64"]}" alt="{cap}" '
            f'width="{fig["w"]}" height="{fig["h"]}" loading="lazy">'
            f'<figcaption>Рисунок {esc(fig["id"])} — {cap}</figcaption></figure>')

# ── MAIN ──
def generate_html(data, out_path):
    meta = data["meta"]
    sections = data["sections"]
    tables = data["tables"]
    figures = data["figures"]
    glossary = data.get("glossary", [])

    # TOC
    toc = ['<nav class="toc"><h3>Содержание</h3><ul>']
    for i, sec in enumerate(sections):
        sid = f"sec-{i+1}"
        toc.append(f'<li><a href="#{sid}">{esc(sec["num"] + " " if sec["num"] else "")}{esc(sec["title"])}</a></li>')
    toc.append('</ul></nav>')

    # Header
    title = meta.get("title", "Документ")
    hdr = (f'<header class="doc-head">'
           f'<div class="eyebrow">Документ · {esc(meta.get("source",""))}</div>'
           f'<h1 class="doc-title">{esc(title)}</h1>'
           f'<div class="tldr"><strong>Кратко.</strong> '
           f'Свод правил СП {esc(meta.get("source",""))} — структурированный документ.</div>'
           f'</header>')

    # Body
    body_parts = []
    fig_by_ref = {fig["id"]: render_figure(fig) for fig in figures}
    tbl_by_cap = {}
    for tbl in tables:
        cap = tbl.get("caption", "")
        m = re.search(r"([0-9А-Я]+\.[0-9А-Я]+)", cap)
        if m:
            tbl_by_cap[m.group(1)] = render_table(tbl)

    for i, sec in enumerate(sections):
        sid = f"sec-{i+1}"
        num = sec["num"]
        title = sec["title"]
        is_glossary = "ермин" in title.lower() or "пределен" in title.lower()

        body_parts.append(
            f'<section id="{sid}" class="sec">'
            f'<div class="sec-head"><span class="num">{esc(num or "·")}</span>'
            f'<h2>{esc(title)}</h2></div>'
        )

        if is_glossary and glossary:
            body_parts.append('<dl class="glossary">')
            for t in glossary:
                body_parts.append(
                    f'<dt id="term-{esc(t["num"])}"><span class="term-num">{esc(t["num"])}</span>'
                    f'{inline(t["term"])}</dt><dd>{inline(t["definition"])}</dd>'
                )
            body_parts.append('</dl>')
        else:
            body = sec.get("body", "").strip()
            subsections = sec.get("subsections", [])

            if subsections:
                # Parse body into clauses
                clause_pat = re.compile(r"(?:^|\n)(\d+(?:\.\d+){1,})\s+")
                parts = clause_pat.split(body)
                pre_clauses = []
                sub_clauses = {}  # sub_num → list of (cnum, ctext)

                if parts[0].strip():
                    pre_clauses.append(("", parts[0].strip()))
                for j in range(1, len(parts), 2):
                    cnum = parts[j]
                    ctext = parts[j+1].strip() if j+1 < len(parts) else ""
                    # Determine which subsection this belongs to
                    p_parts = cnum.split(".")
                    if len(p_parts) >= 2:
                        parent_sub = ".".join(p_parts[:2])  # e.g., "5.2"
                        if parent_sub not in sub_clauses:
                            sub_clauses[parent_sub] = []
                        sub_clauses[parent_sub].append((cnum, ctext))
                    elif len(p_parts) == 1:
                        pre_clauses.append((cnum, ctext))

                # Also check sub-subsections (3-part keys in TOC)
                for sub_num in list(sub_clauses.keys()):
                    sub_sub_clauses = {}
                    remaining = []
                    for cnum, ctext in sub_clauses[sub_num]:
                        p_parts = cnum.split(".")
                        if len(p_parts) >= 3:
                            ss_key = ".".join(p_parts[:3])
                            sub_sub_clauses.setdefault(ss_key, []).append((cnum, ctext))
                        else:
                            remaining.append((cnum, ctext))
                    sub_clauses[sub_num] = {"intro": "", "clauses": remaining, "subsubs": sub_sub_clauses}

                # Render pre-clauses
                for cnum, ctext in pre_clauses:
                    if cnum:
                        body_parts.append(render_clause(cnum, ctext, sid))
                    elif ctext:
                        body_parts.append(f'<p class="body-p">{inline(ctext)}</p>')

                # Render subsections with their clauses
                for sub in subsections:
                    sub_num = sub["num"]
                    sub_title = sub["title"]
                    sub_id = f"{sid}-{sub_num.replace('.', '-')}"
                    body_parts.append(
                        f'<details class="subsec" open id="{sub_id}">'
                        f'<summary><span class="cnum">{esc(sub_num)}</span>{esc(sub_title)}</summary>'
                        f'<div class="subsec-body">'
                    )

                    sc = sub_clauses.get(sub_num, {})
                    sc_intro = sc.get("intro", "")
                    sc_clauses = sc.get("clauses", [])
                    sc_subsubs = sc.get("subsubs", {})
                    sc_toc_subsubs = {ss["num"]: ss for ss in sub.get("subsections", [])}

                    if sc_intro:
                        body_parts.append(f'<p class="body-p">{inline(sc_intro)}</p>')

                    # Render sub-subsections with their clauses
                    for ss_num in sorted(sc_subsubs.keys(),
                                          key=lambda x: tuple(int(p) for p in x.split("."))):
                        ss_clauses = sc_subsubs[ss_num]
                        ss_info = sc_toc_subsubs.get(ss_num, {})
                        ss_title = ss_info.get("title", ss_num)
                        ss_id = f"{sub_id}-{ss_num.split('.')[-1]}"
                        body_parts.append(
                            f'<details class="subsub" id="{ss_id}">'
                            f'<summary><span class="cnum">{esc(ss_num)}</span>{esc(ss_title)}</summary>'
                        )
                        for cnum, ctext in ss_clauses:
                            body_parts.append(render_clause(cnum, ctext, ss_id))
                            # Place figures/tables inside subsub
                            for ref_id, fig_html in list(fig_by_ref.items()):
                                if (f"рисунок {ref_id}" in ctext.lower() or 
                                    f"рисунке {ref_id}" in ctext.lower()):
                                    body_parts.append(fig_html)
                            for ref_num, tbl_html in list(tbl_by_cap.items()):
                                if (f"таблица {ref_num}" in ctext.lower() or 
                                    f"таблице {ref_num}" in ctext.lower()):
                                    body_parts.append(tbl_html)
                        body_parts.append('</details>')

                    # Render remaining clauses directly in subsection
                    for cnum, ctext in sc_clauses:
                        body_parts.append(render_clause(cnum, ctext, sub_id))
                        for ref_id, fig_html in list(fig_by_ref.items()):
                            if (f"рисунок {ref_id}" in ctext.lower() or 
                                f"рисунке {ref_id}" in ctext.lower()):
                                body_parts.append(fig_html)
                        for ref_num, tbl_html in list(tbl_by_cap.items()):
                            if (f"таблица {ref_num}" in ctext.lower() or 
                                f"таблице {ref_num}" in ctext.lower()):
                                body_parts.append(tbl_html)

                    body_parts.append('</div></details>')

            elif body:
                # No subsections — render body as clauses
                clause_pat = re.compile(r"(?:^|\n)(\d+(?:\.\d+){1,})\s+")
                parts = clause_pat.split(body)
                if len(parts) > 1:
                    if parts[0].strip():
                        body_parts.append(f'<p class="body-p">{inline(parts[0].strip())}</p>')
                    for j in range(1, len(parts), 2):
                        body_parts.append(render_clause(parts[j], parts[j+1].strip() if j+1<len(parts) else "", sid))
                else:
                    body_parts.append(f'<p class="body-p">{inline(body)}</p>')

        # Insert remaining tables/figures for this section
        sec_text = sec.get("body", "")
        for sub2 in sec.get("subsections", []):
            sec_text += " " + sub2.get("body", "")
            for ss3 in sub2.get("subsections", []):
                sec_text += " " + ss3.get("body", "")
        for ref_id, fig_html in list(fig_by_ref.items()):
            if (f"рисунок {ref_id}" in sec_text.lower() or 
                f"рисунке {ref_id}" in sec_text.lower()) and fig_html not in body_parts:
                body_parts.append(fig_html)
                fig_by_ref.pop(ref_id, None)
        for ref_num, tbl_html in list(tbl_by_cap.items()):
            if (f"таблица {ref_num}" in sec_text.lower() or 
                f"таблице {ref_num}" in sec_text.lower()) and tbl_html not in body_parts:
                body_parts.append(tbl_html)
                tbl_by_cap.pop(ref_num, None)

        body_parts.append('</section>')

    # Append any unplaced tables/figures
    placed_html = set()
    for bp in body_parts:
        if '<figure' in bp:
            placed_html.add(bp)
    for fig_html in fig_by_ref.values():
        if fig_html not in placed_html:
            body_parts.append(fig_html)
    for tbl_html in tbl_by_cap.values():
        if tbl_html not in placed_html:
            body_parts.append(tbl_html)

    # Assemble
    body_html = "\n".join(body_parts)
    page = PAGE_TEMPLATE
    page = page.replace("__TITLE__", esc(title))
    page = page.replace("__CSS__", CSS)
    page = page.replace("__TOC__", "\n".join(toc))
    page = page.replace("__HEADER__", hdr)
    page = page.replace("__BODY__", body_html)
    page = page.replace("__SOURCE__", esc(meta.get("source", "")))

    with io.open(out_path, "w", encoding="utf-8") as f:
        f.write(page)

    return len(page)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python html_gen.py work/doc.json output/doc.html")
        sys.exit(1)
    with io.open(sys.argv[1], "r", encoding="utf-8") as f:
        data = json.load(f)
    size = generate_html(data, sys.argv[2])
    print(f"  Generated: {sys.argv[2]} ({size//1024} KB)")
