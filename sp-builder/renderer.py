# -*- coding: utf-8 -*-
"""Рендерер: модель документа + оверлей → самодостаточный HTML (тема Komplid oklch).

Ни одного внешнего запроса: системные шрифтовые стеки, весь CSS/JS инлайном
(см. docs/00-STRATEGY-SEO-AEO-GEO.md, blindspot D-4).
"""
from __future__ import annotations

import html as H
import json
import re

# ── CSS (токены Komplid oklch — из pdf-to-html/html_gen.py ≡ design-эталона) ──

CSS = r"""
*{box-sizing:border-box;margin:0;padding:0}
:root{
  --font-ui:'Inter',system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  --font-mono:'JetBrains Mono',ui-monospace,Menlo,Monaco,monospace;
  --r-2:6px;--r-3:8px;--r-4:12px;
  --bg:oklch(0.985 0.002 85);--ink:oklch(0.28 0.02 255);
  --card:#fff;--border:oklch(0.90 0.004 255);
  --muted:oklch(0.55 0.01 255);--inset:oklch(0.95 0.003 85);
  --accent:oklch(0.72 0.14 65);--accent-soft:oklch(0.72 0.14 65 / 0.14);
  --accent-ink:oklch(0.45 0.10 65);--ok:oklch(0.62 0.14 145);
  --warn:oklch(0.72 0.14 75);--err:oklch(0.58 0.18 25);--info:oklch(0.55 0.14 250);
  --shadow-1:0 1px 3px oklch(0.20 0.01 255/0.06);--shadow-2:0 4px 12px oklch(0.20 0.01 255/0.08);
}
html[data-theme="dark"]{
  --bg:oklch(0.17 0.01 255);--ink:oklch(0.94 0.004 255);
  --card:oklch(0.22 0.01 255);--border:oklch(0.32 0.01 255);
  --muted:oklch(0.62 0.01 255);--inset:oklch(0.20 0.01 255);
  --accent:oklch(0.75 0.13 65);--accent-soft:oklch(0.75 0.13 65/0.18);
  --accent-ink:oklch(0.82 0.10 65);
  --shadow-1:0 1px 3px oklch(0 0 0/0.3);--shadow-2:0 4px 12px oklch(0 0 0/0.4);
}
html{scroll-behavior:smooth}
body{font-family:var(--font-ui);background:var(--bg);color:var(--ink);line-height:1.6;
  font-size:15px;-webkit-font-smoothing:antialiased}
a{color:var(--accent-ink);text-decoration:none}
a:hover{text-decoration:underline}
#progress{position:fixed;top:0;left:0;height:3px;width:0;background:var(--accent);z-index:60}
.topbar{position:sticky;top:0;z-index:50;display:flex;align-items:center;gap:14px;
  padding:10px 20px;background:color-mix(in oklch,var(--bg) 88%,transparent);
  backdrop-filter:blur(10px);border-bottom:1px solid var(--border)}
.topbar .crumbs{font-size:12.5px;color:var(--muted);white-space:nowrap;overflow:hidden;
  text-overflow:ellipsis}
.topbar .crumbs a{color:var(--muted)}
.topbar .spacer{flex:1}
.iconbtn{width:34px;height:34px;border-radius:var(--r-2);border:1px solid var(--border);
  background:var(--card);color:var(--ink);cursor:pointer;display:grid;place-items:center;
  font-size:15px;flex:none}
.iconbtn:hover{background:var(--accent-soft)}
#tocToggle{display:none}
.layout{display:grid;grid-template-columns:290px minmax(0,1fr);max-width:1280px;margin:0 auto}
.toc{position:sticky;top:55px;align-self:start;max-height:calc(100vh - 55px);overflow-y:auto;
  padding:28px 20px 48px 28px;border-right:1px solid var(--border);font-size:13px}
.toc h3{font-family:var(--font-mono);font-size:10.5px;text-transform:uppercase;
  letter-spacing:.12em;color:var(--muted);margin:18px 0 10px;font-weight:600}
.toc ul{list-style:none}
.toc li{margin:1px 0}
.toc a{color:var(--ink);display:block;padding:4px 9px;border-radius:var(--r-2);
  font-size:12.8px;line-height:1.35}
.toc a:hover{background:var(--accent-soft);color:var(--accent-ink);text-decoration:none}
.toc a.active{background:var(--accent-soft);color:var(--accent-ink);font-weight:600}
.toc .sub a{padding-left:22px;font-size:12.3px;color:var(--muted)}
.toc .num{font-family:var(--font-mono);font-size:10.5px;color:var(--accent);margin-right:6px}
#search{width:100%;padding:8px 11px;border:1px solid var(--border);border-radius:var(--r-2);
  background:var(--card);color:var(--ink);font:inherit;font-size:13px}
#search:focus{outline:2px solid var(--accent-soft);border-color:var(--accent)}
#sres{margin-top:8px}
#sres .hit{display:block;padding:7px 9px;border:1px solid var(--border);border-radius:var(--r-2);
  margin-bottom:6px;background:var(--card);cursor:pointer;font-size:12px;line-height:1.4}
#sres .hit:hover{border-color:var(--accent)}
#sres .hit .n{font-family:var(--font-mono);color:var(--accent);font-size:10.5px;font-weight:600}
#sres mark{background:var(--accent-soft);color:var(--accent-ink);border-radius:2px;padding:0 1px}
#sres .more{font-size:11.5px;color:var(--muted);padding:4px 9px}
.main{padding:36px 52px 120px;max-width:860px;min-width:0}
.doc-head{margin-bottom:40px;padding-bottom:26px;border-bottom:1px solid var(--border)}
.eyebrow{font-family:var(--font-mono);font-size:11px;text-transform:uppercase;
  letter-spacing:.12em;color:var(--accent-ink);margin-bottom:10px;font-weight:600}
h1{font-weight:650;font-size:30px;line-height:1.22;letter-spacing:-.02em;margin-bottom:14px}
.badges{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0}
.badge{display:inline-flex;align-items:center;gap:6px;font-family:var(--font-mono);
  font-size:11px;padding:4px 10px;border-radius:999px;border:1px solid var(--border);
  background:var(--card);color:var(--muted)}
.badge b{color:var(--ink);font-weight:600}
.badge.st-active{border-color:color-mix(in oklch,var(--ok) 40%,transparent);color:var(--ok)}
.badge.st-active b{color:var(--ok)}
.disclaimer{font-size:12.5px;color:var(--muted);background:var(--inset);
  border:1px solid var(--border);border-radius:var(--r-3);padding:10px 14px;margin:14px 0}
.tldr{background:var(--card);border:1px solid var(--border);border-left:3px solid var(--accent);
  border-radius:var(--r-3);padding:18px 22px;font-size:14.5px;box-shadow:var(--shadow-1);margin:18px 0}
.tldr .lbl{font-family:var(--font-mono);font-size:10px;text-transform:uppercase;
  letter-spacing:.11em;color:var(--accent-ink);font-weight:600;display:block;margin-bottom:7px}
.hl-chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}
.hl-chips a{font-size:12.5px;border:1px solid var(--border);border-radius:999px;
  padding:5px 12px;background:var(--card);color:var(--ink)}
.hl-chips a:hover{border-color:var(--accent);color:var(--accent-ink);text-decoration:none}
.sec{margin-bottom:52px;scroll-margin-top:70px}
.sec>h2{font-size:22px;font-weight:650;letter-spacing:-.01em;margin-bottom:18px;
  padding-bottom:8px;border-bottom:1px solid var(--border);scroll-margin-top:70px}
.sec>h2 .num,.subsec>h3 .num{display:inline-flex;align-items:center;justify-content:center;
  min-width:26px;height:24px;padding:0 8px;background:var(--accent-soft);color:var(--accent-ink);
  font-family:var(--font-mono);font-size:11px;font-weight:600;border-radius:var(--r-2);
  margin-right:10px;vertical-align:2px}
.subsec{margin:26px 0;scroll-margin-top:70px}
.subsec>h3{font-size:17px;font-weight:650;margin-bottom:12px;scroll-margin-top:70px}
h4.subhead{font-size:14.5px;font-weight:650;margin:20px 0 10px;color:var(--accent-ink)}
.clause{position:relative;margin:0 0 12px;padding-left:66px;font-size:14.5px;
  scroll-margin-top:70px;border-radius:var(--r-2)}
.clause .cnum{position:absolute;left:0;top:2px;font-family:var(--font-mono);font-size:11.5px;
  font-weight:600;letter-spacing:.02em}
.clause .cnum a{color:var(--accent)}
.clause .cnum a:hover{text-decoration:none;color:var(--accent-ink)}
.acopy{position:absolute;left:-26px;top:0;width:22px;height:22px;border:none;cursor:pointer;
  background:transparent;color:var(--muted);font-size:13px;opacity:0;border-radius:var(--r-2)}
.clause:hover .acopy{opacity:1}
.acopy:hover{color:var(--accent-ink);background:var(--accent-soft)}
.clause.flash{background:var(--accent-soft);transition:background 1.2s}
p.bp{margin:0 0 12px;font-size:14.5px}
ul.cl{margin:2px 0 14px 84px;font-size:14.2px}
ul.cl li{margin:0 0 7px;padding-left:2px}
figure.tbl{margin:20px 0;overflow-x:auto;border:1px solid var(--border);
  border-radius:var(--r-3);box-shadow:var(--shadow-1)}
figure.tbl table{border-collapse:collapse;width:100%;font-size:13.5px;background:var(--card)}
figure.tbl th{font-family:var(--font-mono);font-size:11px;text-transform:uppercase;
  letter-spacing:.06em;text-align:left;color:var(--muted);padding:10px 14px;
  border-bottom:2px solid var(--border);background:var(--inset)}
figure.tbl td{padding:9px 14px;border-bottom:1px solid var(--border);vertical-align:top}
figure.tbl tr:last-child td{border-bottom:none}
figure.tbl tr:hover td{background:var(--accent-soft)}
dl.glossary dt{font-weight:650;font-size:14.5px;padding:13px 0 3px;border-top:1px solid var(--border);
  scroll-margin-top:70px}
dl.glossary dt .num{font-family:var(--font-mono);font-size:11px;color:var(--accent);margin-right:8px}
dl.glossary dd{font-size:14px;color:var(--ink);padding:0 0 12px;margin:0}
dl.glossary .src{display:block;font-family:var(--font-mono);font-size:11px;color:var(--muted);margin-top:4px}
.std{font-family:var(--font-mono);font-size:12.5px;color:var(--ok);white-space:nowrap}
a.std:hover{text-decoration:underline}
a.bibref{font-family:var(--font-mono);font-size:12px}
ol.biblio{margin:14px 0 0 22px;font-size:13.5px}
ol.biblio li{margin-bottom:10px;scroll-margin-top:70px}
.cta{display:flex;gap:14px;align-items:center;background:var(--accent-soft);
  border:1px solid color-mix(in oklch,var(--accent) 35%,transparent);
  border-radius:var(--r-3);padding:16px 20px;margin:22px 0;font-size:14px}
.cta a{font-weight:600;white-space:nowrap}
.faq details{border:1px solid var(--border);border-radius:var(--r-3);background:var(--card);
  margin-bottom:10px;box-shadow:var(--shadow-1)}
.faq summary{cursor:pointer;padding:14px 18px;font-weight:600;font-size:14.5px;list-style:none;
  display:flex;gap:10px;align-items:center}
.faq summary::before{content:"▸";font-family:var(--font-mono);color:var(--accent);
  transition:transform .2s;font-size:12px}
.faq details[open] summary::before{transform:rotate(90deg)}
.faq .a{padding:0 18px 16px 40px;font-size:14px;color:var(--ink)}
.related{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:12px;margin-top:14px}
.related a{display:block;border:1px solid var(--border);border-radius:var(--r-3);
  background:var(--card);padding:14px 16px;font-size:13.5px;box-shadow:var(--shadow-1)}
.related a:hover{border-color:var(--accent);text-decoration:none}
.related .k{font-family:var(--font-mono);font-size:10px;text-transform:uppercase;
  letter-spacing:.1em;color:var(--muted);display:block;margin-bottom:5px}
footer.doc-foot{margin-top:64px;padding-top:22px;border-top:1px solid var(--border);
  font-size:12.5px;color:var(--muted)}
details.docinfo{margin:16px 0;font-size:13px}
details.docinfo summary{cursor:pointer;color:var(--muted);font-size:13px}
details.docinfo .body{padding:12px 0 0;color:var(--muted)}
details.docinfo .body p{margin-bottom:8px}
@media (max-width:960px){
  .layout{grid-template-columns:1fr}
  .toc{position:fixed;left:0;top:55px;bottom:0;width:min(320px,86vw);background:var(--bg);
    z-index:55;transform:translateX(-102%);transition:transform .2s;border-right:1px solid var(--border);
    box-shadow:var(--shadow-2);max-height:none}
  .toc.open{transform:none}
  #tocToggle{display:grid}
  .main{padding:28px 20px 90px}
  .clause{padding-left:0;padding-top:20px}
  .clause .cnum{top:0}
  .acopy{left:auto;right:0;opacity:.5}
  ul.cl{margin-left:22px}
}
@media print{
  .topbar,.toc,#progress,.acopy,#search,#sres,.cta,.related{display:none!important}
  .layout{display:block}
  .main{max-width:none;padding:0}
  body{font-size:11.5pt;background:#fff;color:#000}
  .sec{break-inside:avoid-page}
  a{color:#000}
}
"""

# ── JS ────────────────────────────────────────────────────────────────────────

JS = r"""
(function(){
  // Тема
  var tbtn=document.getElementById('themeBtn');
  tbtn.addEventListener('click',function(){
    var cur=document.documentElement.getAttribute('data-theme')==='dark'?'light':'dark';
    document.documentElement.setAttribute('data-theme',cur);
    try{localStorage.setItem('komplid-theme',cur)}catch(e){}
  });
  // Прогресс чтения
  var bar=document.getElementById('progress');
  addEventListener('scroll',function(){
    var h=document.documentElement,max=h.scrollHeight-h.clientHeight;
    bar.style.width=(max>0?(h.scrollTop/max*100):0)+'%';
  },{passive:true});
  // Мобильное оглавление
  var toc=document.getElementById('toc'),tt=document.getElementById('tocToggle');
  tt.addEventListener('click',function(){toc.classList.toggle('open')});
  toc.addEventListener('click',function(e){if(e.target.tagName==='A')toc.classList.remove('open')});
  // Scroll-spy
  var links={},heads=document.querySelectorAll('.sec[id],.subsec[id]');
  toc.querySelectorAll('a[href^="#"]').forEach(function(a){links[a.getAttribute('href').slice(1)]=a});
  var active=null;
  var io=new IntersectionObserver(function(es){
    es.forEach(function(en){
      if(en.isIntersecting){
        var a=links[en.target.id];
        if(a){if(active)active.classList.remove('active');a.classList.add('active');active=a;}
      }
    });
  },{rootMargin:'0px 0px -75% 0px'});
  heads.forEach(function(s){io.observe(s)});
  // Копирование якорной ссылки
  document.querySelectorAll('.acopy').forEach(function(b){
    b.addEventListener('click',function(){
      var url=location.origin+location.pathname+'#'+b.getAttribute('data-id');
      (navigator.clipboard?navigator.clipboard.writeText(url):Promise.reject())
        .catch(function(){var i=document.createElement('input');i.value=url;
          document.body.appendChild(i);i.select();document.execCommand('copy');i.remove();})
        .finally(function(){b.textContent='✓';setTimeout(function(){b.textContent='⧉'},1200)});
    });
  });
  // Подсветка цели перехода
  function flash(){
    var el=location.hash&&document.getElementById(location.hash.slice(1));
    if(el&&el.classList.contains('clause')){el.classList.add('flash');
      setTimeout(function(){el.classList.remove('flash')},1600)}
  }
  addEventListener('hashchange',flash);flash();
  // Поиск по документу (DOM-индекс, без внешних запросов).
  // Морфология по-простому: слова длиннее 5 символов усекаются на 2 символа
  // окончания — «скрытые работы» находит «скрытых работ».
  var input=document.getElementById('search'),res=document.getElementById('sres');
  var items=[].map.call(document.querySelectorAll('[data-s][id]'),function(el){
    var t,ct=el.querySelector('.ctext');
    if(ct){t=ct.textContent}
    else if(el.tagName==='DT'){
      var dd=el.nextElementSibling,ns=el.querySelector('.num');
      t=el.textContent+(dd&&dd.tagName==='DD'?' — '+dd.textContent:'');
      if(ns)t=t.replace(ns.textContent,'').trim();
    } else {t=el.textContent}
    return {el:el,id:el.id,num:el.getAttribute('data-n')||'',
            text:t.replace(/\s+/g,' ').trim()};
  });
  function norm(s){return s.toLowerCase().replace(/ё/g,'е')}
  function stems(q){
    return norm(q).split(/[^a-zа-я0-9.\-]+/).filter(function(w){return w.length>=2})
      .map(function(w){return w.length>5?w.slice(0,-2):w});
  }
  var t=null;
  input.addEventListener('input',function(){
    clearTimeout(t);t=setTimeout(run,120);
  });
  function run(){
    var q=input.value.trim();res.innerHTML='';
    if(q.length<3)return;
    var st=stems(q);if(!st.length)return;
    var hits=[],i,it,txt,pos,ok,j;
    for(i=0;i<items.length&&hits.length<80;i++){
      it=items[i];txt=norm(it.text);ok=true;pos=-1;
      for(j=0;j<st.length;j++){
        var p=txt.indexOf(st[j]);
        if(p<0){ok=false;break}
        if(pos<0||p<pos)pos=p;
      }
      if(ok)hits.push({it:it,pos:pos,len:st[0].length});
    }
    var frag=document.createDocumentFragment();
    hits.slice(0,25).forEach(function(h){
      var d=document.createElement('div');d.className='hit';
      var mlen=Math.max(h.len,3);
      var s=Math.max(0,h.pos-38),snip=h.it.text.slice(s,h.pos),
          match=h.it.text.slice(h.pos,h.pos+mlen),
          tail=h.it.text.slice(h.pos+mlen,h.pos+mlen+60);
      d.innerHTML=(h.it.num?'<span class="n">'+h.it.num+'</span> ':'')+
        (s>0?'…':'')+esc(snip)+'<mark>'+esc(match)+'</mark>'+esc(tail)+'…';
      d.addEventListener('click',function(){
        location.hash=h.it.id;h.it.el.scrollIntoView({behavior:'smooth',block:'center'});
        h.it.el.classList.add('flash');setTimeout(function(){h.it.el.classList.remove('flash')},1600);
        toc.classList.remove('open');
      });
      frag.appendChild(d);
    });
    if(hits.length>25){var m=document.createElement('div');m.className='more';
      m.textContent='Показаны 25 из '+hits.length+' совпадений — уточните запрос';frag.appendChild(m)}
    if(!hits.length){var z=document.createElement('div');z.className='more';
      z.textContent='Ничего не найдено';frag.appendChild(z)}
    res.appendChild(frag);
  }
  function esc(s){var d=document.createElement('div');d.textContent=s;return d.innerHTML}
})();
"""

THEME_BOOT = (
    "(function(){try{var t=localStorage.getItem('komplid-theme')||"
    "(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');"
    "document.documentElement.setAttribute('data-theme',t)}catch(e){}})();"
)

STD_RE = re.compile(r"(СП|ГОСТ Р|ГОСТ|СНиП|СанПиН)\s?(\d[\d.]*(?:[-–][\d.]+)*)")
BIBREF_RE = re.compile(r"\[(\d{1,2})\]")
APPENDIX_MENTION_RE = re.compile(r"(приложени[еиюя][хм]?\s+)([А-Я])(?![а-яА-Я])")
SECTION_MENTION_RE = re.compile(r"(раздел[еауом]{0,2}\s+)(\d{1,2})(?![.\d])")


class Renderer:
    def __init__(self, doc: dict, overlay: dict | None = None,
                 registry: dict | None = None):
        self.doc = doc
        self.ov = overlay or {}
        self.registry = registry or {}
        meta = doc["meta"]
        self.designation = meta.get("designation", "")
        self.slug = meta.get("slug", "")
        self.appendix_letters = {a["letter"]: a["id"] for a in doc["appendices"]}
        self.section_nums = {s["num"]: s["id"] for s in doc["sections"]}
        self.biblio_ns = {b["n"] for b in doc["biblio"]}

    # ── инлайн-обогащение ────────────────────────────────────────────────────
    def enrich(self, text: str) -> str:
        esc = H.escape(text)

        def bib(m):
            n = int(m.group(1))
            if n in self.biblio_ns:
                return f'<a class="bibref" href="#bib-{n}">[{n}]</a>'
            return m.group(0)
        esc = BIBREF_RE.sub(bib, esc)

        def std(m):
            label = f"{m.group(1)} {m.group(2).rstrip('.,;')}"
            trail = m.group(2)[len(m.group(2).rstrip('.,;')):]
            full = H.unescape(label)
            if full.startswith("СП ") and not full.startswith(self.designation):
                entry = self.registry.get(full.split(",")[0])
                if entry and entry.get("published"):
                    return (f'<a class="std" href="{entry["slug"]}.html">{label}</a>' + trail)
            return f'<span class="std">{label}</span>{trail}'
        esc = STD_RE.sub(std, esc)

        def app(m):
            aid = self.appendix_letters.get(m.group(2))
            if aid:
                return f'{m.group(1)}<a href="#{aid}">{m.group(2)}</a>'
            return m.group(0)
        esc = APPENDIX_MENTION_RE.sub(app, esc)

        def sec(m):
            sid = self.section_nums.get(m.group(2))
            if sid:
                return f'{m.group(1)}<a href="#{sid}">{m.group(2)}</a>'
            return m.group(0)
        esc = SECTION_MENTION_RE.sub(sec, esc)
        return esc

    # ── блоки контента ───────────────────────────────────────────────────────
    def render_blocks(self, blocks: list) -> str:
        out: list[str] = []
        for b in blocks:
            t = b["t"]
            if t == "clause":
                out.append(self._clause(b))
            elif t == "list":
                items = "".join(f"<li>{self.enrich(i)}</li>" for i in b["items"])
                out.append(f'<ul class="cl">{items}</ul>')
            elif t == "para":
                out.append(f'<p class="bp">{self.enrich(b["text"])}</p>')
            elif t == "subhead":
                out.append(f'<h4 class="subhead">{H.escape(b["text"])}</h4>')
            elif t == "table":
                out.append(self._table(b))
        return "\n".join(out)

    def _clause(self, b: dict) -> str:
        cid, num = b["id"], b["num"]
        return (
            f'<div class="clause" id="{cid}" data-s data-n="{num}">'
            f'<button class="acopy" data-id="{cid}" title="Скопировать ссылку на пункт {num}">⧉</button>'
            f'<span class="cnum"><a href="#{cid}" title="Пункт {num}">{num}</a></span>'
            f'<div class="ctext">{self.enrich(b["text"])}</div></div>'
        )

    def _table(self, b: dict) -> str:
        head = ""
        if b["header"]:
            cells = "".join(f"<th>{self.enrich(c)}</th>" for c in b["header"])
            head = f"<thead><tr>{cells}</tr></thead>"
        rows = []
        for r in b["body"]:
            cells = "".join(f"<td>{self.enrich(c)}</td>" for c in r)
            rows.append(f"<tr>{cells}</tr>")
        return (f'<figure class="tbl"><table>{head}<tbody>{"".join(rows)}</tbody>'
                f"</table></figure>")

    # ── крупные части страницы ───────────────────────────────────────────────
    def render_toc(self) -> str:
        li: list[str] = []
        if self.doc["intro"]:
            li.append('<li><a href="#vvedenie">Введение</a></li>')
        for s in self.doc["sections"]:
            li.append(f'<li><a href="#{s["id"]}"><span class="num">{s["num"]}</span>'
                      f'{H.escape(s["title"])}</a>')
            if s["subs"]:
                subs = "".join(
                    f'<li><a href="#{sub["id"]}"><span class="num">{sub["num"]}</span>'
                    f'{H.escape(sub["title"])}</a></li>' for sub in s["subs"])
                li.append(f'<ul class="sub">{subs}</ul>')
            li.append("</li>")
        for a in self.doc["appendices"]:
            li.append(f'<li><a href="#{a["id"]}"><span class="num">{a["letter"]}</span>'
                      f'{H.escape(_shorten(a["title"], 60))}</a></li>')
        if self.doc["biblio"]:
            li.append('<li><a href="#biblio">Библиография</a></li>')
        if self.ov.get("faq"):
            li.append('<li><a href="#faq">Частые вопросы</a></li>')
        return "".join(li)

    def render_sections(self) -> str:
        out: list[str] = []
        cta_map = {c["afterAnchor"]: c for c in self.ov.get("cta", [])}
        if self.doc["intro"]:
            out.append(f'<section class="sec" id="vvedenie" data-s data-n="Введение">'
                       f"<h2>Введение</h2>{self.render_blocks(self.doc['intro'])}</section>")
        for s in self.doc["sections"]:
            body = [f'<section class="sec" id="{s["id"]}">'
                    f'<h2><span class="num">{s["num"]}</span>{H.escape(s["title"])}</h2>']
            if "термины" in s["title"].lower() and self.doc["glossary"]:
                body.append(self._glossary())
            else:
                body.append(self.render_blocks(s["blocks"]))
                for sub in s["subs"]:
                    body.append(
                        f'<div class="subsec" id="{sub["id"]}">'
                        f'<h3><span class="num">{sub["num"]}</span>{H.escape(sub["title"])}</h3>'
                        f'{self.render_blocks(sub["blocks"])}</div>')
                    if sub["id"] in cta_map:
                        body.append(self._cta(cta_map[sub["id"]]))
            body.append("</section>")
            if s["id"] in cta_map:
                body.append(self._cta(cta_map[s["id"]]))
            out.append("".join(body))
        return "\n".join(out)

    def _glossary(self) -> str:
        items: list[str] = []
        for g in self.doc["glossary"]:
            if not g["term"] and not g["def"]:
                continue
            tid = f"term-{g['num'].replace('.', '-')}" if g["num"] else ""
            num = f'<span class="num">{g["num"]}</span>' if g["num"] else ""
            src = (f'<span class="src">Источник: {H.escape(g["source"])}</span>'
                   if g.get("source") else "")
            attr = f' id="{tid}"' if tid else ""
            items.append(f'<dt{attr} data-s data-n="{g["num"]}">{num}'
                         f'{H.escape(g["term"])}</dt>'
                         f"<dd>{self.enrich(g['def'])}{src}</dd>")
        return f'<dl class="glossary">{"".join(items)}</dl>'

    def render_appendices(self) -> str:
        out: list[str] = []
        for a in self.doc["appendices"]:
            out.append(f'<section class="sec" id="{a["id"]}">'
                       f'<h2><span class="num">{a["letter"]}</span>'
                       f'Приложение {a["letter"]}. {H.escape(a["title"])}</h2>')
            out.append(self.render_blocks(a["blocks"]))
            for sub in a["subs"]:
                sid = sub["id"]
                out.append(f'<div class="subsec" id="{sid}">'
                           f'<h3><span class="num">{sub["num"]}</span>'
                           f'{H.escape(sub["title"])}</h3>'
                           f'{self.render_blocks(sub["blocks"])}</div>')
            out.append("</section>")
        return "\n".join(out)

    def render_biblio(self) -> str:
        if not self.doc["biblio"]:
            return ""
        items = "".join(f'<li id="bib-{b["n"]}" value="{b["n"]}">{H.escape(b["text"])}</li>'
                        for b in self.doc["biblio"])
        return (f'<section class="sec" id="biblio"><h2>Библиография</h2>'
                f'<ol class="biblio">{items}</ol></section>')

    def render_faq(self) -> str:
        faq = self.ov.get("faq") or []
        if not faq:
            return ""
        items = "".join(
            f"<details{' open' if i == 0 else ''}><summary>{H.escape(f['q'])}</summary>"
            f'<div class="a">{self.enrich(f["a"])}</div></details>'
            for i, f in enumerate(faq))
        return (f'<section class="sec faq" id="faq"><h2>Частые вопросы</h2>{items}</section>')

    def render_related(self) -> str:
        rel = self.ov.get("related") or []
        if not rel:
            return ""
        cards = "".join(
            f'<a href="{H.escape(r["href"])}"><span class="k">{H.escape(r["kind"])}</span>'
            f'{H.escape(r["title"])}</a>' for r in rel)
        return (f'<section class="sec" id="related"><h2>Связанные материалы</h2>'
                f'<div class="related">{cards}</div></section>')

    def _cta(self, c: dict) -> str:
        return (f'<aside class="cta"><span>{H.escape(c["text"])}</span>'
                f'<a href="{H.escape(c["href"])}" rel="nofollow">{H.escape(c.get("label", "Подробнее →"))}</a></aside>')

    # ── head: SEO/JSON-LD ─────────────────────────────────────────────────────
    def json_ld(self) -> str:
        meta = self.doc["meta"]
        seo = self.ov.get("seo", {})
        canonical = seo.get("canonical", "")
        approval = meta.get("approval") or {}
        scripts = []
        article = {
            "@context": "https://schema.org", "@type": "TechArticle",
            "headline": f"{self.designation} «{meta.get('title', '')}»",
            "inLanguage": "ru",
            "about": "Свод правил (строительные нормы Российской Федерации)",
            "isBasedOn": "https://minstroyrf.gov.ru/",
            "datePublished": approval.get("date"),
            "dateModified": (self.ov.get("status") or {}).get("checkedAt"),
            "author": {"@type": "Organization", "name": "Минстрой России"},
            "publisher": {"@type": "Organization", "name": "Komplid",
                          "url": "https://komplid.ru"},
        }
        if canonical:
            article["mainEntityOfPage"] = canonical
        scripts.append(article)
        crumbs = {
            "@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Главная",
                 "item": "https://komplid.ru/"},
                {"@type": "ListItem", "position": 2, "name": "Нормативные документы",
                 "item": "https://komplid.ru/normativ"},
                {"@type": "ListItem", "position": 3,
                 "name": self.designation, "item": canonical or None},
            ],
        }
        scripts.append(crumbs)
        if self.ov.get("faq"):
            scripts.append({
                "@context": "https://schema.org", "@type": "FAQPage",
                "mainEntity": [
                    {"@type": "Question", "name": f["q"],
                     "acceptedAnswer": {"@type": "Answer", "text": f["a"]}}
                    for f in self.ov["faq"]],
            })
        out = []
        for s in scripts:
            payload = json.dumps(s, ensure_ascii=False)
            payload = payload.replace("</", "<\\/")  # защита от </script>
            out.append(f'<script type="application/ld+json">{payload}</script>')
        return "\n".join(out)

    # ── сборка страницы ───────────────────────────────────────────────────────
    def render(self) -> str:
        meta = self.doc["meta"]
        ov = self.ov
        seo = ov.get("seo", {})
        status = ov.get("status", {})
        approval = meta.get("approval") or {}
        title = seo.get("title") or (
            f"{self.designation} «{meta.get('title', '')}» — текст с навигацией и поиском")
        description = seo.get("description", "")
        canonical = seo.get("canonical", "")

        badges = []
        state = status.get("state")
        if state:
            label = {"active": "Действует", "amended": "Действует (с изменениями)",
                     "superseded": "Заменён"}.get(state, state)
            badges.append(f'<span class="badge st-{state}">● <b>{label}</b></span>')
        if approval.get("order"):
            badges.append(f'<span class="badge">Приказ Минстроя <b>{approval["order"]}</b>'
                          f'{" от " + _iso_to_ru(approval.get("date")) if approval.get("date") else ""}</span>')
        if approval.get("effective"):
            badges.append(f'<span class="badge">Введён <b>{_iso_to_ru(approval["effective"])}</b></span>')
        if status.get("checkedAt"):
            badges.append(f'<span class="badge">Сверено <b>{_iso_to_ru(status["checkedAt"])}</b></span>')
        if meta.get("snip"):
            badges.append(f'<span class="badge">Взамен <b>{H.escape(status.get("supersedes") or meta["snip"])}</b></span>')

        tldr = ""
        if ov.get("tldr"):
            chips = ""
            if ov.get("keyHighlights"):
                chips = '<div class="hl-chips">' + "".join(
                    f'<a href="#{h["anchor"]}">{H.escape(h["label"])}</a>'
                    for h in ov["keyHighlights"]) + "</div>"
            tldr = (f'<div class="tldr"><span class="lbl">Главное</span>'
                    f'{H.escape(ov["tldr"])}{chips}</div>')

        status_note = ""
        if status.get("note"):
            status_note = f'<p class="bp" style="color:var(--muted);font-size:13px">{H.escape(status["note"])}</p>'

        docinfo = ""
        if self.doc.get("preamble"):
            paras = "".join(f"<p>{H.escape(p)}</p>" for p in self.doc["preamble"][:14])
            docinfo = (f'<details class="docinfo"><summary>О документе: разработчики, '
                       f'утверждение, регистрация</summary><div class="body">{paras}</div></details>')

        head_meta = [
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            f"<title>{H.escape(title)}</title>",
        ]
        if description:
            head_meta.append(f'<meta name="description" content="{H.escape(description)}">')
        if canonical:
            head_meta.append(f'<link rel="canonical" href="{H.escape(canonical)}">')
        head_meta.append(f'<meta property="og:title" content="{H.escape(title)}">')
        if description:
            head_meta.append(f'<meta property="og:description" content="{H.escape(description)}">')
        head_meta.append('<meta property="og:type" content="article">')
        head_meta.append('<meta property="og:locale" content="ru_RU">')

        return f"""<!doctype html>
<html lang="ru" data-theme="light">
<head>
{chr(10).join(head_meta)}
<script>{THEME_BOOT}</script>
{self.json_ld()}
<style>{CSS}</style>
</head>
<body>
<div id="progress"></div>
<header class="topbar">
  <button class="iconbtn" id="tocToggle" aria-label="Оглавление">☰</button>
  <nav class="crumbs"><a href="https://komplid.ru/">Komplid</a> · <a href="https://komplid.ru/normativ">Нормативные документы</a> · {H.escape(self.designation)}</nav>
  <span class="spacer"></span>
  <button class="iconbtn" id="themeBtn" aria-label="Сменить тему">◐</button>
</header>
<div class="layout">
<nav class="toc" id="toc">
  <h3>Поиск по документу</h3>
  <input id="search" type="search" placeholder="Например: скрытые работы" autocomplete="off">
  <div id="sres"></div>
  <h3>Содержание</h3>
  <ul>{self.render_toc()}</ul>
</nav>
<main class="main">
<header class="doc-head" data-s data-n="{H.escape(self.designation)}">
  <div class="eyebrow">Свод правил · {H.escape(meta.get('snip', ''))}</div>
  <h1>{H.escape(self.designation)} «{H.escape(meta.get('title', ''))}»</h1>
  <div class="badges">{''.join(badges)}</div>
  {status_note}
  <div class="disclaimer">Справочная интерактивная копия для удобной работы с документом.
  Не является официальным опубликованием. Официальный источник —
  <a href="https://minstroyrf.gov.ru/" rel="noopener">Минстрой России</a>.
  Перед применением проверяйте актуальность редакции и перечень обязательных требований.</div>
  {tldr}
  {docinfo}
</header>
{self.render_sections()}
{self.render_appendices()}
{self.render_biblio()}
{self.render_faq()}
{self.render_related()}
<footer class="doc-foot">
  <p>Текст свода правил — © Минстрой России. Интерактивная вёрстка, навигация и справочные
  материалы — <a href="https://komplid.ru/">Komplid</a>, платформа для строительной документации.</p>
  <p>Нашли неточность распознавания? Напишите на hello@komplid.ru — исправим.</p>
</footer>
</main>
</div>
<script>{JS}</script>
</body>
</html>
"""


def _shorten(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def _iso_to_ru(iso: str | None) -> str:
    if not iso:
        return ""
    parts = iso.split("-")
    if len(parts) != 3:
        return iso
    return f"{parts[2]}.{parts[1]}.{parts[0]}"
