"""Baut out/angebote.html - eigenstaendig, keine externen Abhaengigkeiten.

Aufbau der Oberflaeche:
  * Kopfleiste: Suche + Knopf "Filter" mit Anzahl aktiver Filter
  * darunter eine Zeile mit den aktiven Filtern zum einzelnen Entfernen
  * die Filter selbst liegen in beschrifteten Abschnitten (Rabatt, Kategorie,
    Geschaeft, Weitere). Am Handy oeffnen sie sich als Blatt von unten, am
    Desktop stehen sie fest im Panel.
  * Angebote als Karten (< 780px) bzw. als Raster mit sortierbaren Spalten

Miniaturbilder gibt es fuer BILLA und PENNY (verlinkt, nicht kopiert);
marktguru sperrt seinen Bild-CDN, dort bleibt der Platz leer.

CSS und JS stehen bewusst in normalen Strings, nicht im f-String: sonst muesste
jede geschweifte Klammer verdoppelt werden.
"""
from __future__ import annotations

import html
import json
from collections import Counter, defaultdict
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
}
@media (prefers-color-scheme: dark) { :root:where(:not([data-theme=light])) {
  --surface:#1a1a19; --plane:#0d0d0d; --card:#1f1f1e;
  --ink:#fff; --ink-2:#c3c2b7; --muted:#8b8983;
  --grid:#2c2c2a; --line:#3d3d39; --ring:rgba(255,255,255,.12);
  --accent:#4a90e2; --good:#3ec46a; --hot:#e66767; --warn:#e0a84a;
  --star:#f0b940;
} }
:root[data-theme=dark] {
  --surface:#1a1a19; --plane:#0d0d0d; --card:#1f1f1e;
  --ink:#fff; --ink-2:#c3c2b7; --muted:#8b8983;
  --grid:#2c2c2a; --line:#3d3d39; --ring:rgba(255,255,255,.12);
  --accent:#4a90e2; --good:#3ec46a; --hot:#e66767; --warn:#e0a84a;
  --star:#f0b940;
}
* { box-sizing:border-box; -webkit-tap-highlight-color:transparent; }
body { margin:0; background:var(--plane); color:var(--ink);
  font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif; }
body.sheet-open { overflow:hidden; }
.wrap { max-width:1180px; margin:0 auto; padding:16px 12px 80px; }

header { display:flex; align-items:center; gap:10px; flex-wrap:wrap; }
h1 { font-size:20px; margin:0; letter-spacing:-.02em; }
.sub { color:var(--ink-2); font-size:12.5px; width:100%; }
.iconbtn { background:none; border:1px solid var(--ring); color:var(--ink-2);
  border-radius:9px; min-width:42px; min-height:42px; padding:0 11px;
  cursor:pointer; font:inherit; font-size:15px; }
.iconbtn:hover { color:var(--ink); }
.spacer { margin-left:auto; display:flex; gap:6px; }

.kpis { display:grid; grid-template-columns:repeat(2,1fr); gap:8px; margin:14px 0; }
.kpi { background:var(--card); border:1px solid var(--ring); border-radius:11px;
  padding:10px 12px; }
.kpi .v { font-size:22px; font-weight:650; letter-spacing:-.03em; line-height:1.15; }
.kpi .l { font-size:11.5px; color:var(--ink-2); margin-top:1px; }

/* ---- Kopfleiste: Suche + Filterknopf ---- */
.bar { position:sticky; top:0; z-index:30; background:var(--plane);
  padding:8px 0; margin-bottom:6px; }
.barrow { display:flex; gap:8px; }
input[type=search] { font:inherit; font-size:16px; padding:10px 12px; flex:1;
  min-width:0; border-radius:10px; border:1px solid var(--line);
  background:var(--card); color:var(--ink); min-height:46px; }
.filterbtn { display:flex; align-items:center; gap:7px; white-space:nowrap;
  border:1px solid var(--line); background:var(--card); color:var(--ink);
  border-radius:10px; padding:0 15px; min-height:46px; font:inherit;
  font-size:15px; cursor:pointer; }
.filterbtn .cnt { background:var(--accent); color:#fff; border-radius:999px;
  min-width:21px; height:21px; font-size:12px; font-weight:700;
  display:none; align-items:center; justify-content:center; padding:0 6px; }
.filterbtn.has .cnt { display:flex; }

/* ---- Zeile mit den aktiven Filtern ---- */
.active { display:flex; gap:6px; align-items:center; overflow-x:auto;
  padding-bottom:2px; margin-top:8px; }
.active:empty { display:none; }
.afchip { display:inline-flex; align-items:center; gap:6px; flex:0 0 auto;
  background:var(--accent); color:#fff; border:none; border-radius:999px;
  padding:6px 8px 6px 12px; font:inherit; font-size:12.5px; font-weight:600;
  cursor:pointer; min-height:34px; }
.afchip .x { font-size:15px; line-height:1; opacity:.85; }
.clearall { flex:0 0 auto; background:none; border:1px solid var(--line);
  color:var(--ink-2); border-radius:999px; padding:6px 12px; font:inherit;
  font-size:12.5px; cursor:pointer; min-height:34px; }

/* ---- Filterblatt / Panel ---- */
.scrim { position:fixed; inset:0; background:rgba(0,0,0,.55); z-index:40;
  opacity:0; pointer-events:none; transition:opacity .2s; }
body.sheet-open .scrim { opacity:1; pointer-events:auto; }
.panel { position:fixed; left:0; right:0; bottom:0; z-index:50;
  background:var(--card); border-radius:18px 18px 0 0; max-height:84vh;
  overflow-y:auto; transform:translateY(101%); transition:transform .22s ease;
  padding:6px 14px calc(16px + env(safe-area-inset-bottom));
  box-shadow:0 -8px 30px rgba(0,0,0,.25); }
body.sheet-open .panel { transform:translateY(0); }
.grip { width:38px; height:4px; border-radius:2px; background:var(--line);
  margin:8px auto 12px; }
.sect { margin-bottom:16px; }
.sect h3 { font-size:11.5px; text-transform:uppercase; letter-spacing:.06em;
  color:var(--muted); margin:0 0 7px; font-weight:700; }
.scroller { display:flex; gap:6px; flex-wrap:wrap; }
.chip { font:inherit; font-size:13.5px; padding:9px 14px; border-radius:999px;
  cursor:pointer; border:1px solid var(--line); background:var(--surface);
  color:var(--ink-2); white-space:nowrap; min-height:42px; }
.chip[aria-pressed=true] { background:var(--accent); border-color:var(--accent);
  color:#fff; font-weight:600; }
.chip .n { opacity:.62; font-size:11.5px; margin-left:5px; }
.chip.fav[aria-pressed=true] { background:var(--star); border-color:var(--star);
  color:#161616; }
.sheetbar { position:sticky; bottom:0; background:var(--card); display:flex;
  gap:8px; padding-top:10px; border-top:1px solid var(--grid); }
.sheetbar button { flex:1; min-height:48px; border-radius:11px; font:inherit;
  font-size:15px; cursor:pointer; }
.btn-reset { background:none; border:1px solid var(--line); color:var(--ink-2); }
.btn-apply { background:var(--accent); border:1px solid var(--accent);
  color:#fff; font-weight:600; }
#subsect[hidden] { display:none; }

/* ---- Liste ---- */
.hdr { display:none; }
.list { display:flex; flex-direction:column; gap:8px; }
.offer { background:var(--card); border:1px solid var(--ring); border-radius:12px;
  padding:11px 12px; }
.otop { display:flex; align-items:center; gap:9px; }
.obody { display:flex; gap:11px; margin-top:7px; }
.thumb { width:54px; height:54px; flex:0 0 auto; border-radius:9px;
  object-fit:contain; background:var(--surface); border:1px solid var(--grid); }
.thumb.broken { visibility:hidden; }
.otext { min-width:0; flex:1; }
.star { background:none; border:none; cursor:pointer; font-size:22px;
  line-height:1; padding:0; color:var(--muted); flex:0 0 auto;
  min-width:38px; min-height:38px; }
.star[aria-pressed=true] { color:var(--star); }
.disc { font-weight:800; font-size:19px; font-variant-numeric:tabular-nums;
  color:var(--good); flex:0 0 auto; }
.disc.hot { color:var(--hot); }
.store { font-size:11.5px; font-weight:700; letter-spacing:.03em;
  white-space:nowrap; padding:3px 8px; border-radius:6px;
  border:1px solid var(--ring); margin-left:auto;
  background:color-mix(in srgb, var(--accent) 10%, transparent); }
.name { font-weight:600; overflow-wrap:anywhere; }
a.name { color:inherit; text-decoration:none; display:block; }
.meta { color:var(--ink-2); font-size:13px; margin-top:3px;
  font-variant-numeric:tabular-nums; }
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

/* ---- Desktop ---- */
@media (min-width:780px) {
  .wrap { padding:26px 20px 80px; }
  h1 { font-size:25px; }
  .sub { width:auto; font-size:13.5px; }
  .kpis { grid-template-columns:repeat(4,1fr); gap:12px; }
  .kpi .v { font-size:28px; }
  .scrim, .sheetbar, .grip, #filterbtn { display:none; }
  .panel { position:static; transform:none; max-height:none; overflow:visible;
    border:1px solid var(--ring); border-radius:12px; box-shadow:none;
    padding:14px; margin-bottom:12px; }
  .sect { margin-bottom:12px; }
  /* Zehn Rasterzellen: .otop und .obody haben display:contents, ihre Kinder
     zaehlen also einzeln. Stimmt die Spaltenzahl nicht, bricht die Zeile um. */
  .cols { display:grid;
    grid-template-columns:38px 76px 100px 46px minmax(0,1fr) 84px 112px 92px 106px 88px;
    gap:9px; align-items:center; }
  .hdr { display:grid; padding:2px 12px 6px; font-size:11.5px;
    text-transform:uppercase; letter-spacing:.04em; color:var(--muted);
    font-weight:600; }
  .hdr span { cursor:pointer; user-select:none; white-space:nowrap; }
  .hdr span:hover { color:var(--ink); }
  .hdr .on::after { content:" \\2193"; }
  .hdr .on.asc::after { content:" \\2191"; }
  .offer { padding:8px 12px; }
  .otop, .obody { display:contents; }
  .star { justify-self:center; }
  .disc { font-size:17px; }
  .store { margin-left:0; justify-self:start; }
  .thumb { width:42px; height:42px; }
  .cell { font-size:13px; color:var(--ink-2); font-variant-numeric:tabular-nums;
    white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .cell.price { color:var(--ink); font-weight:600; }
  .cell .old { color:var(--muted); font-weight:400; font-size:12px; display:block; }
  .m-only { display:none; }
}
@media (max-width:779px) { .d-only { display:none; } }

@media print {
  .bar, .active, .panel, .scrim, .kpis, .iconbtn, .spacer, footer, .hdr,
  .note, header { display:none !important; }
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

/* Favoriten liegen im Browser des Betrachters und ueberleben die woechentliche
   Aktualisierung, weil der Schluessel aus Geschaeft + Produkt + Menge besteht.
   Private Fenster koennen localStorage sperren -> alles in try/catch. */
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

function bandOf(pct) { return Math.min(Math.floor(pct / 10) * 10, 60); }
const BANDS = [...new Set(DATA.map(o => bandOf(o.effective_pct)))].sort((a,b) => a-b);
const bandLabel = b => "\\u2212" + b + " %" + (b === 60 ? "+" : "");

/* ---- Chips ---- */
function chipRow(box, items, label, pressed, onClick, cls) {
  box.innerHTML = "";
  items.forEach(it => {
    const b = document.createElement("button");
    b.className = "chip" + (cls ? " " + cls : "");
    b.type = "button";
    b.innerHTML = label(it);
    b._item = it;
    b.onclick = () => { onClick(it); sync(); draw(); };
    box.appendChild(b);
  });
}

function buildBands() {
  chipRow($("#bands"), BANDS,
    b => bandLabel(b) + "<span class='n'>" +
         DATA.filter(o => bandOf(o.effective_pct) === b).length + "</span>",
    null,
    b => { if (state.bands.has(b)) state.bands.delete(b); else state.bands.add(b); });
}
function buildStores() {
  chipRow($("#stores"), ["", ...STORES],
    s => s === "" ? "Alle" : esc(s) + "<span class='n'>" +
         DATA.filter(o => o.store === s).length + "</span>",
    null,
    s => { if (s === "") state.stores.clear();
           else if (state.stores.has(s)) state.stores.delete(s);
           else state.stores.add(s); });
}
function catCount(g) { return CATS[g].reduce((n, s) => n + s[1], 0); }
function buildCats() {
  chipRow($("#cats"), ["", ...Object.keys(CATS)],
    g => g === "" ? "Alle" : esc(g) + "<span class='n'>" + catCount(g) + "</span>",
    null,
    g => { state.cat = g; state.sub = ""; buildSubs(); });
}
function buildSubs() {
  const subs = state.cat ? (CATS[state.cat] || []) : [];
  $("#subsect").hidden = subs.length === 0;
  if (!subs.length) { $("#subs").innerHTML = ""; return; }
  const anz = {};
  subs.forEach(p => { anz[p[0]] = p[1]; });
  chipRow($("#subs"), ["", ...subs.map(p => p[0])],
    s => s === "" ? "Alle" : esc(s) + "<span class='n'>" + anz[s] + "</span>",
    null,
    s => { state.sub = s; });
}
function buildFlags() {
  const flags = [["favOnly", "\\u2605 nur Favoriten"], ["newOnly", "nur NEU"],
                 ["noMulti", "ohne Mehrfachkauf"], ["noCard", "ohne Kundenkarte"]];
  chipRow($("#flags"), flags,
    f => f[1] + (f[0] === "favOnly" ? "<span class='n'>" + favs.size + "</span>" : ""),
    null,
    f => { state[f[0]] = !state[f[0]]; },
    "");
  [...$("#flags").children].forEach(b => {
    if (b._item[0] === "favOnly") b.classList.add("fav");
  });
}

/* ---- Aktive Filter: sichtbar und einzeln loeschbar ---- */
function activeList() {
  const a = [];
  [...state.bands].sort((x,y) => x-y).forEach(b =>
    a.push([bandLabel(b), () => state.bands.delete(b)]));
  if (state.cat) a.push([state.cat, () => { state.cat = ""; state.sub = ""; buildSubs(); }]);
  if (state.sub) a.push([state.sub, () => { state.sub = ""; }]);
  [...state.stores].forEach(s => a.push([s, () => state.stores.delete(s)]));
  if (state.favOnly) a.push(["\\u2605 Favoriten", () => { state.favOnly = false; }]);
  if (state.newOnly) a.push(["nur NEU", () => { state.newOnly = false; }]);
  if (state.noMulti) a.push(["ohne Mehrfachkauf", () => { state.noMulti = false; }]);
  if (state.noCard) a.push(["ohne Kundenkarte", () => { state.noCard = false; }]);
  if (state.q) a.push(["Suche: " + state.q, () => { state.q = ""; $("#q").value = ""; }]);
  return a;
}
function resetAll() {
  state.bands.clear(); state.stores.clear();
  state.cat = ""; state.sub = ""; state.q = ""; $("#q").value = "";
  state.favOnly = state.newOnly = state.noMulti = state.noCard = false;
  buildSubs(); sync(); draw();
}

function sync() {
  document.querySelectorAll("#bands .chip").forEach(b =>
    b.setAttribute("aria-pressed", state.bands.has(b._item)));
  document.querySelectorAll("#stores .chip").forEach(b =>
    b.setAttribute("aria-pressed", b._item === "" ? state.stores.size === 0
                                                  : state.stores.has(b._item)));
  document.querySelectorAll("#cats .chip").forEach(b =>
    b.setAttribute("aria-pressed", state.cat === b._item));
  document.querySelectorAll("#subs .chip").forEach(b =>
    b.setAttribute("aria-pressed", state.sub === b._item));
  document.querySelectorAll("#flags .chip").forEach(b =>
    b.setAttribute("aria-pressed", !!state[b._item[0]]));

  const act = activeList();
  $("#filterbtn").classList.toggle("has", act.length > 0);
  $("#filtercnt").textContent = act.length;

  const box = $("#active");
  box.innerHTML = "";
  act.forEach(pair => {
    const b = document.createElement("button");
    b.className = "afchip";
    b.type = "button";
    b.innerHTML = esc(pair[0]) + "<span class='x'>\\u00D7</span>";
    b.onclick = () => { pair[1](); sync(); draw(); };
    box.appendChild(b);
  });
  if (act.length) {
    const c = document.createElement("button");
    c.className = "clearall";
    c.type = "button";
    c.textContent = "alle l\\u00F6schen";
    c.onclick = resetAll;
    box.appendChild(c);
  }
}

/* ---- Filterblatt oeffnen / schliessen ---- */
function openSheet() { document.body.classList.add("sheet-open"); }
function closeSheet() { document.body.classList.remove("sheet-open"); }
$("#filterbtn").onclick = openSheet;
$("#scrim").onclick = closeSheet;
$("#apply").onclick = closeSheet;
$("#reset").onclick = resetAll;
$("#q").oninput = e => { state.q = e.target.value.toLowerCase(); sync(); draw(); };
$("#theme").onclick = () => {
  const cur = document.documentElement.dataset.theme ||
    (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  document.documentElement.dataset.theme = cur === "dark" ? "light" : "dark";
};
document.addEventListener("keydown", e => { if (e.key === "Escape") closeSheet(); });
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
  const img = o.image_url
    ? "<img class='thumb' src='" + esc(o.image_url) + "' alt='' loading='lazy' decoding='async'>"
    : "<div class='thumb'></div>";

  return "<div class='offer cols'>" +
    "<div class='otop'>" +
      "<button class='star' data-key='" + esc(o.key) + "' aria-pressed='" + on +
        "' aria-label='Als Favorit merken'>" + (on ? "\\u2605" : "\\u2606") + "</button>" +
      "<div class='disc" + (o.effective_pct >= 50 ? " hot" : "") + "'>\\u2212" +
        Math.round(o.effective_pct) + "\\u2009%</div>" +
      "<span class='store'>" + esc(o.store) + "</span>" +
    "</div>" +
    "<div class='obody'>" + img +
      "<div class='otext'>" + nm +
        "<div class='meta m-only'>" + esc(o.amount) +
          (o.price != null ? " \\u00B7 <b>" + eur(o.price) + "</b>" : "") +
          (o.old_price != null ? " <s>" + eur(o.old_price) + "</s>" : "") +
        "</div>" +
        "<div class='meta m-only'>" +
          (o.base_price ? "<span class='bp'>" + esc(o.base_price) + "</span> \\u00B7 " : "") +
          "bis " + dmy(o.valid_to) + "</div>" +
        (tags.length ? "<div class='badges'>" + tags.join("") + "</div>" : "") +
      "</div>" +
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
  $("#applycnt").textContent = rows.length;
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
    saveFavs(); buildFlags(); sync(); draw();
  });
  // Fehlende Bilder ausblenden statt ein kaputtes Symbol zu zeigen.
  document.querySelectorAll("img.thumb").forEach(im => {
    im.onerror = () => im.classList.add("broken");
  });
}

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

buildBands(); buildCats(); buildSubs(); buildStores(); buildFlags();
sync(); draw();
"""


def render_html(rows: list[dict], meta: dict) -> str:
    # Geschaefte nach Angebotszahl - die grossen Ketten zuerst, nicht "ADEG" nur
    # weil es alphabetisch vorne steht.
    stores = [s for s, _ in Counter(r["store"] for r in rows).most_common()]
    updated = meta.get("generated_at", datetime.now().strftime("%d.%m.%Y %H:%M"))
    min_pct = meta.get("min_pct", 30)
    plz = meta.get("zip", "")
    best = max((r["effective_pct"] for r in rows), default=0)
    n_new = sum(1 for r in rows if r.get("is_new"))

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

    sources = meta.get("sources") or {}
    dead = [name for name, n in sources.items() if not n]
    alert = ""
    if dead:
        names = " und ".join(html.escape(d) for d in dead)
        alert = ('<div class="alert"><b>Diese Liste ist unvollständig</b>'
                 "Von " + names + " kamen bei diesem Lauf keine Daten. "
                 "Angebote dieser Geschäfte fehlen hier oder erscheinen nur, "
                 "soweit eine andere Quelle sie kennt.</div>")
    srcline = ""
    if sources:
        parts = ", ".join(html.escape(k) + " " + str(v) + ("" if v else " (0)")
                          for k, v in sources.items())
        srcline = ('<div class="srcline">Von den Quellen geholt (vor Dedupe und '
                   'Rabattfilter): ' + parts + "</div>")

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

    body = f"""<div class="scrim" id="scrim"></div>
<div class="wrap">
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

<div class="bar">
  <div class="barrow">
    <input type="search" id="q" placeholder="Produkt suchen …" aria-label="Produkt suchen">
    <button class="filterbtn" id="filterbtn">Filter <span class="cnt" id="filtercnt">0</span></button>
  </div>
  <div class="active" id="active"></div>
</div>

<div class="panel" id="panel">
  <div class="grip"></div>
  <div class="sect"><h3>Rabatt</h3><div class="scroller" id="bands"></div></div>
  <div class="sect"><h3>Kategorie</h3><div class="scroller" id="cats"></div></div>
  <div class="sect" id="subsect" hidden><h3>Unterkategorie</h3>
    <div class="scroller" id="subs"></div></div>
  <div class="sect"><h3>Geschäft</h3><div class="scroller" id="stores"></div></div>
  <div class="sect"><h3>Weitere</h3><div class="scroller" id="flags"></div></div>
  <div class="sheetbar">
    <button class="btn-reset" id="reset">Zurücksetzen</button>
    <button class="btn-apply" id="apply"><span id="applycnt">0</span> Angebote zeigen</button>
  </div>
</div>

<div class="hdr cols">
  <span>★</span>
  <span data-k="effective_pct" class="on">Rabatt</span>
  <span data-k="store">Geschäft</span>
  <span></span>
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
Produktbilder werden von den Händler-Servern geladen, nicht gespeichert.
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
