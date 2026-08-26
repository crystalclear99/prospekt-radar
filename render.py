"""Baut out/angebote.html - eigenstaendig, keine externen Abhaengigkeiten.

Layout nach dem Prototyp: KPI-Reihe, sortierbare Tabelle, Rabatt-Meter,
Geschaefts-Chips, Dark Mode, Druckansicht. Ergaenzt um Einkaufslisten-Modus,
NEU-Badge und Scheinrabatt-Warnung.
"""
from __future__ import annotations

import html
import json

from core.categories import sort_key
from datetime import datetime


def render_html(rows: list[dict], meta: dict) -> str:
    data = json.dumps(rows, ensure_ascii=False)
    stores = sorted({r["store"] for r in rows})
    cats = sorted({r["category"] for r in rows if r.get("category")},
                  key=sort_key)
    updated = meta.get("generated_at", datetime.now().strftime("%d.%m.%Y %H:%M"))
    min_pct = meta.get("min_pct", 30)
    plz = meta.get("zip", "")
    best = max((r["effective_pct"] for r in rows), default=0)
    n_new = sum(1 for r in rows if r.get("is_new"))

    return f"""<!DOCTYPE html>
<html lang="de"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Prospekt-Radar — die besten Angebote</title>
<style>
:root {{
  color-scheme: light dark;
  --surface:#fcfcfb; --plane:#f9f9f7; --card:#fff;
  --ink:#0b0b0b; --ink-2:#52514e; --muted:#898781;
  --grid:#e1e0d9; --line:#c3c2b7; --ring:rgba(11,11,11,.10);
  --accent:#2a78d6; --good:#0ca30c; --hot:#d03b3b; --warn:#b8791a;
  --b3:#3987e5; --b4:#256abf; --b5:#0d366b;
}}
@media (prefers-color-scheme: dark) {{ :root:where(:not([data-theme=light])) {{
  --surface:#1a1a19; --plane:#0d0d0d; --card:#1f1f1e;
  --ink:#fff; --ink-2:#c3c2b7; --muted:#898781;
  --grid:#2c2c2a; --line:#383835; --ring:rgba(255,255,255,.10);
  --accent:#3987e5; --good:#0ca30c; --hot:#e66767; --warn:#e0a84a;
  --b3:#3987e5; --b4:#86b6ef; --b5:#cde2fb;
}} }}
:root[data-theme=dark] {{
  --surface:#1a1a19; --plane:#0d0d0d; --card:#1f1f1e;
  --ink:#fff; --ink-2:#c3c2b7; --muted:#898781;
  --grid:#2c2c2a; --line:#383835; --ring:rgba(255,255,255,.10);
  --accent:#3987e5; --good:#0ca30c; --hot:#e66767; --warn:#e0a84a;
  --b3:#3987e5; --b4:#86b6ef; --b5:#cde2fb;
}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--plane);color:var(--ink);
  font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}}
.wrap{{max-width:1180px;margin:0 auto;padding:28px 20px 80px}}
header{{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap}}
h1{{font-size:26px;margin:0;letter-spacing:-.02em}}
.sub{{color:var(--ink-2);font-size:14px}}
.btn{{background:none;border:1px solid var(--ring);color:var(--ink-2);
  border-radius:8px;padding:5px 11px;cursor:pointer;font:inherit;font-size:13px}}
.btn:hover{{color:var(--ink)}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin:22px 0 20px}}
.kpi{{background:var(--card);border:1px solid var(--ring);border-radius:12px;padding:14px 16px}}
.kpi .v{{font-size:30px;font-weight:650;letter-spacing:-.03em;line-height:1.1}}
.kpi .l{{font-size:12.5px;color:var(--ink-2);margin-top:3px}}
.kpi .n{{font-size:11.5px;color:var(--muted);margin-top:2px}}
.filters{{display:flex;gap:10px;flex-wrap:wrap;align-items:center;background:var(--card);
  border:1px solid var(--ring);border-radius:12px;padding:12px 14px;margin-bottom:16px}}
input[type=search],select{{font:inherit;font-size:14px;padding:7px 10px;border-radius:8px;
  border:1px solid var(--line);background:var(--surface);color:var(--ink)}}
input[type=search]{{min-width:210px;flex:1 1 210px}}
.chip{{font:inherit;font-size:13px;padding:6px 12px;border-radius:999px;cursor:pointer;
  border:1px solid var(--line);background:var(--surface);color:var(--ink-2)}}
.chip[aria-pressed=true]{{background:var(--accent);border-color:var(--accent);color:#fff;font-weight:600}}
label.tog{{font-size:13px;color:var(--ink-2);display:flex;align-items:center;gap:6px;cursor:pointer}}
.tablecard{{background:var(--card);border:1px solid var(--ring);border-radius:12px;overflow:hidden}}
table{{width:100%;border-collapse:collapse}}
th,td{{text-align:left;padding:11px 14px;border-bottom:1px solid var(--grid);vertical-align:top}}
th{{font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);
  font-weight:600;cursor:pointer;user-select:none;white-space:nowrap;
  position:sticky;top:0;background:var(--card);z-index:1}}
th:hover{{color:var(--ink)}}
th.sorted::after{{content:" ↓"}} th.sorted.asc::after{{content:" ↑"}}
tbody tr:hover{{background:color-mix(in srgb,var(--accent) 6%,transparent)}}
.prod{{font-weight:600}}
a.prod{{color:inherit;text-decoration:none}} a.prod:hover{{text-decoration:underline}}
.promo{{font-size:12.5px;color:var(--ink-2);margin-top:2px}}
.amount{{white-space:nowrap;font-variant-numeric:tabular-nums}}
.store{{font-size:12px;font-weight:700;letter-spacing:.03em;white-space:nowrap;
  padding:3px 9px;border-radius:6px;border:1px solid var(--ring);
  background:color-mix(in srgb,var(--accent) 9%,transparent)}}
.disc{{white-space:nowrap}} .disc b{{font-size:17px;font-variant-numeric:tabular-nums}}
.meter{{height:5px;border-radius:3px;background:var(--grid);margin-top:5px;width:74px;overflow:hidden}}
.meter i{{display:block;height:100%;border-radius:3px}}
.price{{white-space:nowrap;font-variant-numeric:tabular-nums}}
.price s{{color:var(--muted);font-size:12.5px}}
.unit{{color:var(--ink-2);font-size:12.5px;white-space:nowrap;font-variant-numeric:tabular-nums}}
.tag{{display:inline-block;font-size:11px;padding:1px 6px;border-radius:5px;
  border:1px solid var(--line);color:var(--ink-2);margin-left:6px}}
.tag.new{{background:var(--good);border-color:var(--good);color:#fff}}
.tag.warn{{background:var(--hot);border-color:var(--hot);color:#fff}}
.tag.card{{color:var(--warn);border-color:var(--warn)}}
.tag.soon{{color:var(--accent);border-color:var(--accent)}}
.chk{{display:none}} body.shop .chk{{display:inline-block}}
.empty{{padding:40px;text-align:center;color:var(--ink-2)}}
footer{{margin-top:18px;font-size:12.5px;color:var(--muted)}}
#printarea{{display:none}}
@media print{{
  .filters,.kpis,.btn,footer,thead{{display:none!important}}
  body{{background:#fff;color:#000}} .tablecard{{border:none}}
  body.printlist .tablecard{{display:none}}
  body.printlist #printarea{{display:block}}
  #printarea h2{{margin:16px 0 6px;font-size:15px;border-bottom:1px solid #999}}
  #printarea .li{{padding:3px 0;border-bottom:1px dotted #ccc;font-size:13px}}
}}
@media (max-width:760px){{
  thead{{display:none}}
  tr{{display:block;padding:12px 14px;border-bottom:1px solid var(--grid)}}
  td{{display:block;border:none;padding:2px 0}}
}}
</style></head><body>
<div class="wrap">
<header>
  <h1>Prospekt-Radar</h1>
  <span class="sub">Nur Angebote ab −{min_pct}&nbsp;%{(' · PLZ ' + str(plz)) if plz else ''} · Stand {html.escape(str(updated))}</span>
  <span style="margin-left:auto;display:flex;gap:8px">
    <button class="btn" id="shopbtn">☑ Einkaufsliste</button>
    <button class="btn" id="printbtn">🖨 Drucken</button>
    <button class="btn" id="theme">◐ Hell / Dunkel</button>
  </span>
</header>

<div class="kpis">
  <div class="kpi"><div class="v" id="k1">0</div><div class="l">Angebote</div>
    <div class="n" id="k1n">von {len(rows)} gesamt</div></div>
  <div class="kpi"><div class="v">−{best:.0f}&nbsp;%</div><div class="l">bester Rabatt</div>
    <div class="n">höchster effektiver Nachlass</div></div>
  <div class="kpi"><div class="v">{len(stores)}</div><div class="l">Geschäfte</div>
    <div class="n">mit mindestens einem Treffer</div></div>
  <div class="kpi"><div class="v">{n_new}</div><div class="l">NEU</div>
    <div class="n">seit dem letzten Lauf</div></div>
</div>

<div class="filters">
  <input type="search" id="q" placeholder="Produkt suchen …" aria-label="Produkt suchen">
  <span id="storechips"></span>
  <select id="cat" aria-label="Kategorie"><option value="">Alle Kategorien</option></select>
  <select id="minpct" aria-label="Mindestrabatt">
    <option value="{min_pct}">ab −{min_pct} %</option>
    <option value="40">ab −40 %</option><option value="50">ab −50 %</option>
  </select>
  <label class="tog"><input type="checkbox" id="nocard"> ohne Kundenkarte</label>
  <label class="tog"><input type="checkbox" id="single"> ohne Mehrfachkauf</label>
  <label class="tog"><input type="checkbox" id="onlynew"> nur NEU</label>
</div>

<div class="tablecard">
<table>
<thead><tr>
  <th data-k="product">Produkt</th>
  <th data-k="amount">Menge</th>
  <th data-k="store">Geschäft</th>
  <th data-k="effective_pct" class="sorted">Rabatt</th>
  <th data-k="price">Preis</th>
  <th data-k="base_price_num">Grundpreis</th>
  <th data-k="valid_to">Gültig bis</th>
</tr></thead>
<tbody id="rows"></tbody>
</table>
<div class="empty" id="empty" hidden>Keine Angebote passen zu diesen Filtern.</div>
</div>
<div id="printarea"></div>
<footer>Rabatte sind effektive Werte: 2+1&nbsp;gratis = −33,3&nbsp;%, 1+1&nbsp;gratis = −50&nbsp;%.
„Größe variiert" heißt: das Angebot gilt für mehrere Gebindegrößen, der Grundpreis nur für die genannte.
Angaben ohne Gewähr — Preise im Geschäft prüfen.</footer>
</div>

<script>
const DATA = {data};
const STORES = {json.dumps(stores, ensure_ascii=False)};
const CATS = {json.dumps(cats, ensure_ascii=False)};
const state = {{ q:"", stores:new Set(), cat:"", min:{min_pct}, nocard:false,
                 single:false, onlynew:false, sort:"effective_pct", dir:-1 }};
const picked = new Set();

const $ = s => document.querySelector(s);
const eur = v => v==null ? "" : v.toFixed(2).replace(".",",")+" €";
const esc = s => String(s??"").replace(/[&<>"]/g,c=>({{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}}[c]));
const dmy = s => {{ if(!s) return ""; const p=String(s).split("-"); return p[2]+"."+p[1]+"."+p[0]; }};

const chipbox = $("#storechips");
STORES.forEach(s => {{
  const b=document.createElement("button");
  b.className="chip"; b.textContent=s; b.setAttribute("aria-pressed","false");
  b.onclick=()=>{{ state.stores.has(s)?state.stores.delete(s):state.stores.add(s);
    b.setAttribute("aria-pressed", state.stores.has(s)); render(); }};
  chipbox.appendChild(b);
}});
CATS.forEach(c=>{{ const o=document.createElement("option"); o.value=o.textContent=c; $("#cat").appendChild(o); }});

$("#q").oninput      = e => {{ state.q=e.target.value.toLowerCase(); render(); }};
$("#cat").onchange   = e => {{ state.cat=e.target.value; render(); }};
$("#minpct").onchange= e => {{ state.min=+e.target.value; render(); }};
$("#nocard").onchange= e => {{ state.nocard=e.target.checked; render(); }};
$("#single").onchange= e => {{ state.single=e.target.checked; render(); }};
$("#onlynew").onchange=e => {{ state.onlynew=e.target.checked; render(); }};
document.querySelectorAll("th").forEach(th => th.onclick = () => {{
  const k=th.dataset.k;
  state.dir = (state.sort===k) ? -state.dir : (k==="effective_pct" ? -1 : 1);
  state.sort=k;
  document.querySelectorAll("th").forEach(t=>t.className="");
  th.className="sorted"+(state.dir===1?" asc":"");
  render();
}});
$("#theme").onclick = () => {{
  const cur=document.documentElement.dataset.theme
    || (matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light");
  document.documentElement.dataset.theme = cur==="dark"?"light":"dark";
}};
$("#shopbtn").onclick = () => document.body.classList.toggle("shop");
$("#printbtn").onclick = () => {{
  const pool = picked.size ? visible().filter(o=>picked.has(o.key)) : visible();
  const byStore={{}};
  pool.forEach(o=>(byStore[o.store]=byStore[o.store]||[]).push(o));
  $("#printarea").innerHTML = Object.keys(byStore).sort().map(s =>
    "<h2>"+esc(s)+"</h2>" + byStore[s].map(o =>
      '<div class="li">☐ '+esc(o.product)+" — "+esc(o.amount)+
      (o.price!=null?" — "+eur(o.price):"")+
      (o.base_price?" ("+esc(o.base_price)+")":"")+
      (o.requires_qty>1?" — "+o.requires_qty+" Stk nötig":"")+"</div>").join("")
  ).join("");
  document.body.classList.add("printlist");
  window.print();
  setTimeout(()=>document.body.classList.remove("printlist"),600);
}};

function visible() {{
  return DATA.filter(o =>
    o.effective_pct >= state.min-0.05 &&
    (!state.stores.size || state.stores.has(o.store)) &&
    (!state.cat || o.category===state.cat) &&
    (!state.nocard || !o.needs_card) &&
    (!state.single || o.requires_qty===1) &&
    (!state.onlynew || o.is_new) &&
    (!state.q || (o.product+" "+(o.brand||"")+" "+(o.category||"")+" "+o.store).toLowerCase().includes(state.q))
  );
}}

function meterColor(p) {{
  const v=getComputedStyle(document.documentElement);
  return v.getPropertyValue(p>=50?"--b5":p>=40?"--b4":"--b3");
}}

function render() {{
  const rows = visible().sort((a,b) => {{
    const x=a[state.sort], y=b[state.sort];
    if (x==null) return 1; if (y==null) return -1;
    return (typeof x==="number" ? x-y : String(x).localeCompare(String(y),"de")) * state.dir;
  }});

  $("#k1").textContent = rows.length;
  $("#k1n").textContent = "von {len(rows)} gesamt";
  $("#empty").hidden = rows.length>0;

  $("#rows").innerHTML = rows.map(o => {{
    const tags = [];
    if (o.is_new) tags.push('<span class="tag new">NEU</span>');
    if (o.requires_qty>1) tags.push('<span class="tag">'+o.requires_qty+' Stk nötig</span>');
    if (o.needs_card) tags.push('<span class="tag card">Kundenkarte</span>');
    if (o.starts_in_future) tags.push('<span class="tag soon">ab '+dmy(o.valid_from)+'</span>');
    if (o.size_varies) tags.push('<span class="tag">Größe variiert</span>');
    if (o.hist_warning) tags.push('<span class="tag warn">Scheinrabatt? Ø −'+Math.round(o.hist_median_pct)+'%</span>');
    const nm = o.url
      ? '<a class="prod" href="'+esc(o.url)+'" target="_blank" rel="noopener">'+esc(o.product)+'</a>'
      : '<span class="prod">'+esc(o.product)+'</span>';
    return `<tr>
      <td><input type="checkbox" class="chk" data-key="${{esc(o.key)}}"${{picked.has(o.key)?" checked":""}}> ${{nm}}
          <div class="promo">„${{esc(o.action_text)}}"${{tags.join("")}}</div></td>
      <td class="amount">${{esc(o.amount)}}</td>
      <td><span class="store">${{esc(o.store)}}</span></td>
      <td class="disc"><b>−${{Math.round(o.effective_pct)}} %</b>
          <div class="meter"><i style="width:${{Math.min(100,o.effective_pct*1.6)}}%;
            background:${{meterColor(o.effective_pct)}}"></i></div></td>
      <td class="price">${{eur(o.price)}} ${{o.old_price!=null?"<s>"+eur(o.old_price)+"</s>":""}}</td>
      <td class="unit">${{esc(o.base_price??"")}}</td>
      <td class="unit">${{dmy(o.valid_to)}}</td>
    </tr>`;
  }}).join("");

  document.querySelectorAll(".chk").forEach(c => c.onchange = () => {{
    c.checked ? picked.add(c.dataset.key) : picked.delete(c.dataset.key);
  }});
}}
render();
</script></body></html>"""
