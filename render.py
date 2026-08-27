"""Baut out/angebote.html - eigenstaendig, keine externen Abhaengigkeiten.

Mobile first: unter 780px werden die Angebote als Karten dargestellt, darueber
als Raster mit sortierbaren Spalten.

Funktionen: Favoriten (bleiben ueber Wochen im Browser erhalten), Kategorie +
Unterkategorie, Rabattbaender als Mehrfachauswahl, Geschaefts-Chips, Suche,
Dark Mode, Druckansicht der Favoriten.

CSS und JS stehen bewusst in normalen Strings, nicht im f-String: sonst muesste
jede geschweifte Klammer verdoppelt werden.
"""
from __future__ import annotations

import html
import json
from collections import defaultdict
from datetime import datetime

from core.categories import sort_key

CSS = """
:root {
  color-scheme: light dark;
  --surface:#fcfcfb; --plane:#f4f4f1; --card:#fff;
  --ink:#0b0b0b; --ink-2:#52514e; --muted:#8b8983;
  --grid:#e6e5de; --line:#c9c8bd; --ring:rgba(11,11,11,.10);
  --accent:#2a78d6; --good:#0a8f3c; --hot:#d03b3b; --warn:#a86a12;
  --star:#e8a33d;
  --b3:#3987e5; --b4:#256abf; --b5:#0d366b;
}
@media (prefers-color-scheme: dark) { :root:where(:not([data-theme=light])) {
  --surface:#1a1a19; --plane:#0d0d0d; --card:#1f1f1e;
  --ink:#fff; --ink-2:#c3c2b7; --muted:#8b8983;
  --grid:#2c2c2a; --line:#3d3d39; --ring:rgba(255,255,255,.12);
  --accent:#4a90e2; --good:#3ec46a; --hot:#e66767; --warn:#e0a84a;
  --star:#f0b940;
  --b3:#3987e5; --b4:#86b6ef; --b5:#cde2fb;
} }
:root[data-theme=dark] {
  --surface:#1a1a19; --plane:#0d0d0d; --card:#1f1f1e;
  --ink:#fff; --ink-2:#c3c2b7; --muted:#8b8983;
  --grid:#2c2c2a; --line:#3d3d39; --ring:rgba(255,255,255,.12);
  --accent:#4a90e2; --good:#3ec46a; --hot:#e66767; --warn:#e0a84a;
  --star:#f0b940;
  --b3:#3987e5; --b4:#86b6ef; --b5:#cde2fb;
}
* { box-sizing:border-box; -webkit-tap-highlight-color:transparent; }
body { margin:0; background:var(--plane); color:var(--ink);
  font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif;
  padding-bottom:env(safe-area-inset-bottom); }
.wrap { max-width:1180px; margin:0 auto; padding:16px 12px 80px; }

header { display:flex; align-items:center; gap:10px; flex-wrap:wrap; }
h1 { font-size:20px; margin:0; letter-spacing:-.02em; }
.sub { color:var(--ink-2); font-size:12.5px; width:100%; }
.iconbtn { background:none; border:1px solid var(--ring); color:var(--ink-2);
  border-radius:9px; min-width:42px; min-height:42px; padding:0 11px; cursor:pointer;
  font:inherit; font-size:15px; }
.iconbtn:hover { color:var(--ink); }
.spacer { margin-left:auto; display:flex; gap:6px; }

.kpis { display:grid; grid-template-columns:repeat(2,1fr); gap:8px; margin:14px 0; }
.kpi { background:var(--card); border:1px solid var(--ring); border-radius:11px; padding:10px 12px; }
.kpi .v { font-size:22px; font-weight:650; letter-spacing:-.03em; line-height:1.15; }
.kpi .l { font-size:11.5px; color:var(--ink-2); margin-top:1px; }

/* ---- Filter ---- */
.filters { background:var(--card); border:1px solid var(--ring); border-radius:12px;
  padding:10px; margin-bottom:12px; position:sticky; top:0; z-index:20; }
.frow { display:flex; gap:8px; align-items:center; margin-bottom:8px; }
.frow:last-child { margin-bottom:0; }
input[type=search], select { font:inherit; font-size:16px; padding:9px 11px;
  border-radius:9px; border:1px solid var(--line); background:var(--surface);
  color:var(--ink); min-height:44px; }
input[type=search] { flex:1; min-width:0; }
select { flex:1; min-width:0; }
.scroller { display:flex; gap:6px; overflow-x:auto; padding-bottom:2px; width:100%;
  scrollbar-width:thin; -webkit-overflow-scrolling:touch; }
.scroller::-webkit-scrollbar { height:4px; }
.scroller::-webkit-scrollbar-thumb { background:var(--line); border-radius:2px; }
.chip { font:inherit; font-size:13px; padding:8px 13px; border-radius:999px;
  cursor:pointer; border:1px solid var(--line); background:var(--surface);
  color:var(--ink-2); white-space:nowrap; flex:0 0 auto; min-height:40px; }
.chip[aria-pressed=true] { background:var(--accent); border-color:var(--accent);
  color:#fff; font-weight:600; }
.chip .n { opacity:.65; font-size:11.5px; margin-left:4px; }
.chip.fav[aria-pressed=true] { background:var(--star); border-color:var(--star); color:#161616; }
.more { display:none; }
.filters.open .more { display:block; }
#togglefilters .caret { display:inline-block; transition:transform .15s; }
.filters.open #togglefilters .caret { transform:rotate(180deg); }

/* ---- Liste ---- */
.hdr { display:none; }
.list { display:flex; flex-direction:column; gap:8px; }
.offer { background:var(--card); border:1px solid var(--ring); border-radius:12px;
  padding:11px 12px; }
.otop { display:flex; align-items:center; gap:9px; }
.star { background:none; border:none; cursor:pointer; font-size:22px; line-height:1;
  padding:0; color:var(--muted); flex:0 0 auto; min-width:38px; min-height:38px; }
.star[aria-pressed=true] { color:var(--star); }
.disc { font-weight:800; font-size:19px; font-variant-numeric:tabular-nums;
  color:var(--good); flex:0 0 auto; }
.disc.hot { color:var(--hot); }
.store { font-size:11.5px; font-weight:700; letter-spacing:.03em; white-space:nowrap;
  padding:3px 8px; border-radius:6px; border:1px solid var(--ring); margin-left:auto;
  background:color-mix(in srgb, var(--accent) 10%, transparent); }
.name { font-weight:600; margin-top:6px; overflow-wrap:anywhere; }
a.name { color:inherit; text-decoration:none; display:block; }
a.name:active { text-decoration:underline; }
.meta { color:var(--ink-2); font-size:13px; margin-top:3px; font-variant-numeric:tabular-nums; }
.meta s { color:var(--muted); }
.meta .bp { color:var(--muted); }
.badges { display:flex; gap:5px; flex-wrap:wrap; margin-top:6px; }
.tag { font-size:11px; padding:2px 7px; border-radius:6px;
  border:1px solid var(--line); color:var(--ink-2); }
.tag.new { background:var(--good); border-color:var(--good); color:#fff; }
.tag.warn { background:var(--hot); border-color:var(--hot); color:#fff; }
.tag.card { color:var(--warn); border-color:var(--warn); }
.tag.soon { color:var(--accent); border-color:var(--accent); }
.empty { padding:36px 16px; text-align:center; color:var(--ink-2); }
.note { font-size:12.5px; color:var(--muted); margin:10px 2px 0; }
.alert { background:color-mix(in srgb, var(--hot) 14%, transparent);
  border:1px solid var(--hot); border-radius:11px; padding:10px 13px;
  margin-bottom:12px; font-size:13.5px; }
.alert b { display:block; margin-bottom:2px; }
.srcline { font-size:11.5px; color:var(--muted); margin-top:8px; }
footer { margin-top:16px; font-size:12px; color:var(--muted); }
#printarea { display:none; }

/* ---- Desktop: Raster mit sortierbaren Spalten ---- */
@media (min-width:780px) {
  .wrap { padding:26px 20px 80px; }
  h1 { font-size:25px; }
  .sub { width:auto; font-size:13.5px; }
  .kpis { grid-template-columns:repeat(4,1fr); gap:12px; }
  .kpi .v { font-size:28px; }
  .more { display:block; }
  #togglefilters { display:none; }
  /* Neun Rasterzellen je Zeile: .otop hat display:contents, also zaehlen
     Stern, Rabatt und Geschaeft einzeln - danach Produkt und die
     Detailspalten. Stimmt die Spaltenzahl nicht, bricht die Zeile um. */
  .cols { display:grid;
    grid-template-columns:40px 82px 106px minmax(0,1fr) 88px 118px 94px 112px 92px;
    gap:10px; align-items:center; }
  .hdr { display:grid; padding:2px 12px 6px; font-size:11.5px; text-transform:uppercase;
    letter-spacing:.04em; color:var(--muted); font-weight:600; }
  .hdr span { cursor:pointer; user-select:none; white-space:nowrap; }
  .hdr span:hover { color:var(--ink); }
  .hdr .on::after { content:" \\2193"; }
  .hdr .on.asc::after { content:" \\2191"; }
  .offer { padding:9px 12px; }
  .otop { display:contents; }
  .star { justify-self:center; }
  .disc { font-size:17px; }
  .store { margin-left:0; justify-self:start; }
  .name { margin-top:0; }
  .badges { margin-top:4px; }
  .cell { font-size:13px; color:var(--ink-2); font-variant-numeric:tabular-nums;
    white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .cell.price { color:var(--ink); font-weight:600; }
  .cell .old { color:var(--muted); font-weight:400; font-size:12px; display:block; }
  .m-only { display:none; }
}
@media (max-width:779px) {
  .d-only { display:none; }
}

@media print {
  .filters, .kpis, .iconbtn, .spacer, footer, .hdr, .note, header { display:none !important; }
  body { background:#fff; color:#000; }
  .list { display:none; }
  #printarea { display:block !important; }
  #printarea h2 { margin:14px 0 6px; font-size:15px; border-bottom:1px solid #999; }
  #printarea .li { padding:4px 0; border-bottom:1px dotted #ccc; font-size:13px; }
}
"""

JS = """
const $ = s => document.querySelector(s);
const FAVKEY = "prospekt-radar:favoriten";

/* Favoriten liegen im Browser des Betrachters. Sie ueberleben die woechentliche
   Aktualisierung, weil der Schluessel aus Geschaeft + Produkt + Menge besteht
   und nicht aus einer Lauf-ID. Private Fenster koennen localStorage sperren -
   deshalb alles in try/catch. */
function loadFavs() {
  try { return new Set(JSON.parse(localStorage.getItem(FAVKEY) || "[]")); }
  catch (e) { return new Set(); }
}
function saveFavs() {
  try { localStorage.setItem(FAVKEY, JSON.stringify([...favs])); } catch (e) {}
}
const favs = loadFavs();

const state = { q:"", stores:new Set(), cat:"", sub:"", bands:new Set(),
                favOnly:false, newOnly:false, noMulti:false, noCard:false,
                sort:"effective_pct", dir:-1 };

const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g, c =>
  ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;" }[c]));
const eur = v => v == null ? "" : v.toFixed(2).replace(".", ",") + " \\u20AC";
const dmy = s => { if (!s) return ""; const p = String(s).split("-");
  return p[2] + "." + p[1] + "." + p[0]; };

/* ---- Rabattbaender: 30-39, 40-49, 50-59, ab 60. Mehrfachauswahl. ---- */
function bandOf(pct) { return Math.min(Math.floor(pct / 10) * 10, 60); }
const BANDS = [...new Set(DATA.map(o => bandOf(o.effective_pct)))].sort((a, b) => a - b);
function bandLabel(b) { return "\\u2212" + b + " %" + (b === 60 ? "+" : ""); }

function buildChips(box, items, label, onToggle, cls) {
  box.innerHTML = "";
  items.forEach(it => {
    const b = document.createElement("button");
    b.className = "chip" + (cls ? " " + cls : "");
    b.type = "button";
    b.innerHTML = label(it);
    b._item = it;
    b.onclick = () => { onToggle(it); syncChips(); draw(); };
    box.appendChild(b);
  });
}
function syncChips() {
  document.querySelectorAll("#bands .chip").forEach(b =>
    b.setAttribute("aria-pressed", state.bands.has(b._item)));
  document.querySelectorAll("#storechips .chip").forEach(b =>
    b.setAttribute("aria-pressed", state.stores.has(b._item)));
  $("#favOnly").innerHTML = "\\u2605 nur Favoriten<span class='n'>" + favs.size + "</span>";
}

buildChips($("#bands"), BANDS,
  b => bandLabel(b) + "<span class='n'>" +
       DATA.filter(o => bandOf(o.effective_pct) === b).length + "</span>",
  b => { if (state.bands.has(b)) state.bands.delete(b); else state.bands.add(b); });

buildChips($("#storechips"), STORES,
  s => esc(s) + "<span class='n'>" + DATA.filter(o => o.store === s).length + "</span>",
  s => { if (state.stores.has(s)) state.stores.delete(s); else state.stores.add(s); });

/* ---- Kategorie + Unterkategorie ---- */
function fillCats() {
  const sel = $("#cat");
  sel.innerHTML = "<option value=''>Alle Kategorien</option>";
  Object.keys(CATS).forEach(g => {
    const total = CATS[g].reduce((n, s) => n + s[1], 0);
    const o = document.createElement("option");
    o.value = g;
    o.textContent = g + " (" + total + ")";
    sel.appendChild(o);
  });
}
function fillSubs() {
  const sel = $("#sub");
  const subs = state.cat ? (CATS[state.cat] || []) : [];
  sel.innerHTML = "<option value=''>" +
    (subs.length ? "Alle Unterkategorien" : "Erst Kategorie w\\u00E4hlen") + "</option>";
  subs.forEach(pair => {
    const o = document.createElement("option");
    o.value = pair[0];
    o.textContent = pair[0] + " (" + pair[1] + ")";
    sel.appendChild(o);
  });
  sel.disabled = subs.length === 0;
  sel.style.opacity = subs.length ? "1" : ".55";
}
fillCats(); fillSubs();

$("#cat").onchange = e => { state.cat = e.target.value; state.sub = ""; fillSubs(); draw(); };
$("#sub").onchange = e => { state.sub = e.target.value; draw(); };
$("#q").oninput = e => { state.q = e.target.value.toLowerCase(); draw(); };
["favOnly", "newOnly", "noMulti", "noCard"].forEach(k => {
  const el = document.getElementById(k);
  el.onclick = () => {
    state[k] = !state[k];
    el.setAttribute("aria-pressed", state[k]);
    draw();
  };
});
$("#togglefilters").onclick = () => $(".filters").classList.toggle("open");
$("#theme").onclick = () => {
  const cur = document.documentElement.dataset.theme ||
    (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  document.documentElement.dataset.theme = cur === "dark" ? "light" : "dark";
};
document.querySelectorAll(".hdr span[data-k]").forEach(th => th.onclick = () => {
  const k = th.dataset.k;
  state.dir = (state.sort === k) ? -state.dir : (k === "effective_pct" ? -1 : 1);
  state.sort = k;
  document.querySelectorAll(".hdr span").forEach(x => x.className = "");
  th.className = "on" + (state.dir === 1 ? " asc" : "");
  draw();
});

/* ---- Filtern ---- */
function visible() {
  return DATA.filter(o =>
    (!state.bands.size || state.bands.has(bandOf(o.effective_pct))) &&
    (!state.stores.size || state.stores.has(o.store)) &&
    (!state.cat || o.category === state.cat) &&
    (!state.sub || o.subcategory === state.sub) &&
    (!state.favOnly || favs.has(o.key)) &&
    (!state.newOnly || o.is_new) &&
    (!state.noMulti || o.requires_qty === 1) &&
    (!state.noCard || !o.needs_card) &&
    (!state.q || (o.product + " " + (o.brand || "") + " " + (o.subcategory || "") +
                  " " + o.store).toLowerCase().includes(state.q))
  );
}

function offerHTML(o) {
  const tags = [];
  if (o.is_new) tags.push("<span class='tag new'>NEU</span>");
  if (o.requires_qty > 1) tags.push("<span class='tag'>" + o.requires_qty + " Stk n\\u00F6tig</span>");
  if (o.needs_card) tags.push("<span class='tag card'>Kundenkarte</span>");
  if (o.starts_in_future) tags.push("<span class='tag soon'>ab " + dmy(o.valid_from) + "</span>");
  if (o.size_varies) tags.push("<span class='tag'>Gr\\u00F6\\u00DFe variiert</span>");
  if (o.hist_warning) tags.push("<span class='tag warn'>Scheinrabatt? \\u00D8 \\u2212" +
    Math.round(o.hist_median_pct) + "%</span>");

  const nm = o.url
    ? "<a class='name' href='" + esc(o.url) + "' target='_blank' rel='noopener'>" +
      esc(o.product) + "</a>"
    : "<div class='name'>" + esc(o.product) + "</div>";
  const on = favs.has(o.key);

  return "<div class='offer cols'>" +
    "<div class='otop'>" +
      "<button class='star' data-key='" + esc(o.key) + "' aria-pressed='" + on +
        "' aria-label='Als Favorit merken'>" + (on ? "\\u2605" : "\\u2606") + "</button>" +
      "<div class='disc" + (o.effective_pct >= 50 ? " hot" : "") + "'>\\u2212" +
        Math.round(o.effective_pct) + "\\u2009%</div>" +
      "<span class='store'>" + esc(o.store) + "</span>" +
    "</div>" +
    "<div>" + nm +
      "<div class='meta m-only'>" + esc(o.amount) +
        (o.price != null ? " \\u00B7 <b>" + eur(o.price) + "</b>" : "") +
        (o.old_price != null ? " <s>" + eur(o.old_price) + "</s>" : "") +
      "</div>" +
      "<div class='meta m-only'>" +
        (o.base_price ? "<span class='bp'>" + esc(o.base_price) + "</span> \\u00B7 " : "") +
        "bis " + dmy(o.valid_to) + "</div>" +
      (tags.length ? "<div class='badges'>" + tags.join("") + "</div>" : "") +
    "</div>" +
    "<div class='cell d-only'>" + esc(o.amount) + "</div>" +
    "<div class='cell d-only'>" + esc(o.subcategory) + "</div>" +
    "<div class='cell d-only price'>" + (o.price != null ? eur(o.price) : "") +
      (o.old_price != null ? "<span class='old'>statt " + eur(o.old_price) + "</span>" : "") +
    "</div>" +
    "<div class='cell d-only'>" + esc(o.base_price) + "</div>" +
    "<div class='cell d-only'>bis " + dmy(o.valid_to) + "</div>" +
  "</div>";
}

function draw() {
  const rows = visible().sort((a, b) => {
    const x = a[state.sort], y = b[state.sort];
    if (x == null) return 1;
    if (y == null) return -1;
    return (typeof x === "number" ? x - y : String(x).localeCompare(String(y), "de")) * state.dir;
  });
  $("#k1").textContent = rows.length;
  $("#kfav").textContent = favs.size;
  $("#list").innerHTML = rows.length
    ? rows.map(offerHTML).join("")
    : "<div class='empty'>Keine Angebote passen zu diesen Filtern.</div>";
  $(".hdr").style.visibility = rows.length ? "visible" : "hidden";

  const missing = [...favs].filter(k => !DATA.some(o => o.key === k)).length;
  $("#note").textContent = missing
    ? missing + (missing === 1 ? " Favorit ist" : " Favoriten sind") +
      " gerade nicht im Angebot \\u2013 gespeichert bleiben sie trotzdem."
    : "";

  document.querySelectorAll(".star").forEach(btn => btn.onclick = () => {
    const k = btn.dataset.key;
    if (favs.has(k)) favs.delete(k); else favs.add(k);
    saveFavs(); syncChips(); draw();
  });
}

/* Drucken: Favoriten, sonst die aktuelle Ansicht - nach Geschaeft gruppiert. */
$("#printbtn").onclick = () => {
  const pool = favs.size ? DATA.filter(o => favs.has(o.key)) : visible();
  const byStore = {};
  pool.forEach(o => { (byStore[o.store] = byStore[o.store] || []).push(o); });
  $("#printarea").innerHTML =
    "<h2>Einkaufsliste" + (favs.size ? " (Favoriten)" : "") + "</h2>" +
    Object.keys(byStore).sort().map(s =>
      "<h2>" + esc(s) + "</h2>" + byStore[s].map(o =>
        "<div class='li'>\\u2610 " + esc(o.product) + " \\u2014 " + esc(o.amount) +
        (o.price != null ? " \\u2014 " + eur(o.price) : "") +
        (o.requires_qty > 1 ? " (" + o.requires_qty + " Stk n\\u00F6tig)" : "") +
        "</div>").join("")
    ).join("");
  window.print();
};

syncChips();
draw();
"""


def render_html(rows: list[dict], meta: dict) -> str:
    stores = sorted({r["store"] for r in rows})
    updated = meta.get("generated_at", datetime.now().strftime("%d.%m.%Y %H:%M"))
    min_pct = meta.get("min_pct", 30)
    plz = meta.get("zip", "")
    best = max((r["effective_pct"] for r in rows), default=0)
    n_new = sum(1 for r in rows if r.get("is_new"))

    # Kategoriebaum fuer die zweistufigen Filter: Gruppe -> [(Unterkategorie, Anzahl)]
    tree: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in rows:
        if r.get("category"):
            tree[r["category"]][r.get("subcategory") or "Übrige"] += 1
    cat_tree = {
        g: sorted(subs.items(), key=lambda kv: (-kv[1], kv[0]))
        for g, subs in sorted(tree.items(), key=lambda kv: sort_key(kv[0]))
    }

    subtitle = (f"ab −{min_pct}\u2009%"
                + (f" · PLZ {plz}" if plz else "")
                + f" · Stand {html.escape(str(updated))}")

    # Quellenlage sichtbar machen. Faellt eine Quelle aus, steht das oben auf
    # der Seite - sonst sieht man nur eine kuerzere Liste und haelt sie fuer
    # normal. Ein gruener Lauf bei halber Datenmenge ist der gefaehrlichste Fall.
    sources = meta.get("sources") or {}
    dead = [name for name, n in sources.items() if not n]
    alert = ""
    if dead:
        names = " und ".join(html.escape(d) for d in dead)
        alert = ('<div class="alert"><b>Diese Liste ist unvollstaendig</b>'
                 "Von " + names + " kamen bei diesem Lauf keine Daten. "
                 "Angebote dieser Geschaefte fehlen hier oder erscheinen nur, "
                 "soweit eine andere Quelle sie kennt.</div>")
    srcline = ""
    if sources:
        parts = ", ".join(html.escape(k) + " " + str(v) + ("" if v else " (0)")
                          for k, v in sources.items())
        srcline = '<div class="srcline">Quellen dieses Laufs: ' + parts + "</div>"


    head = (
        '<!DOCTYPE html>\n<html lang="de"><head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1,'
        'viewport-fit=cover">\n'
        '<meta name="robots" content="noindex, nofollow">\n'
        '<meta name="theme-color" content="#2a78d6">\n'
        "<title>Prospekt-Radar — die besten Angebote</title>\n"
        "<style>" + CSS + "</style></head><body>\n"
    )

    body = f"""<div class="wrap">
<header>
  <h1>🛒 Prospekt-Radar</h1>
  <span class="spacer">
    <button class="iconbtn" id="printbtn" title="Einkaufsliste drucken">🖨</button>
    <button class="iconbtn" id="theme" title="Hell / Dunkel">◐</button>
  </span>
  <span class="sub">{subtitle}</span>
</header>

{alert}<div class="kpis">
  <div class="kpi"><div class="v" id="k1">0</div><div class="l">Angebote sichtbar</div></div>
  <div class="kpi"><div class="v" id="kfav">0</div><div class="l">Favoriten</div></div>
  <div class="kpi"><div class="v">−{best:.0f}&nbsp;%</div><div class="l">bester Rabatt</div></div>
  <div class="kpi"><div class="v">{n_new}</div><div class="l">neu diese Woche</div></div>
</div>

<div class="filters">
  <div class="frow">
    <input type="search" id="q" placeholder="Produkt suchen …" aria-label="Produkt suchen">
    <button class="iconbtn" id="togglefilters">Filter <span class="caret">▾</span></button>
  </div>
  <div class="frow"><div class="scroller" id="bands"></div></div>
  <div class="more">
    <div class="frow">
      <select id="cat" aria-label="Kategorie"></select>
      <select id="sub" aria-label="Unterkategorie"></select>
    </div>
    <div class="frow"><div class="scroller" id="storechips"></div></div>
    <div class="frow">
      <div class="scroller">
        <button class="chip fav" id="favOnly" type="button" aria-pressed="false">★ nur Favoriten</button>
        <button class="chip" id="newOnly" type="button" aria-pressed="false">nur NEU</button>
        <button class="chip" id="noMulti" type="button" aria-pressed="false">ohne Mehrfachkauf</button>
        <button class="chip" id="noCard" type="button" aria-pressed="false">ohne Kundenkarte</button>
      </div>
    </div>
  </div>
</div>

<div class="hdr cols">
  <span>★</span>
  <span data-k="effective_pct" class="on">Rabatt</span>
  <span data-k="store">Geschäft</span>
  <span data-k="product">Produkt</span>
  <span data-k="amount">Menge</span>
  <span data-k="subcategory">Art</span>
  <span data-k="price">Preis</span>
  <span data-k="base_price_num">Grundpreis</span>
  <span data-k="valid_to">Gültig</span>
</div>
<div class="list" id="list"></div>
<div class="note" id="note"></div>
<div id="printarea"></div>
<footer>Rabatte sind effektive Werte: 2+1&nbsp;gratis = −33&nbsp;%, 1+1&nbsp;gratis = −50&nbsp;%.
Favoriten bleiben in diesem Browser gespeichert, auch wenn die Liste aktualisiert wird.
Angaben ohne Gewähr — Preise im Geschäft prüfen.{srcline}</footer>
</div>
"""

    script = (
        "<script>\n"
        "const DATA = " + json.dumps(rows, ensure_ascii=False) + ";\n"
        "const STORES = " + json.dumps(stores, ensure_ascii=False) + ";\n"
        "const CATS = " + json.dumps(cat_tree, ensure_ascii=False) + ";\n"
        + JS + "\n</script>\n</body></html>\n"
    )
    return head + body + script
