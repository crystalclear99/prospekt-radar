# Prospekt-Radar Österreich

Filtert aus den aktuellen Supermarkt-Aktionen automatisch die *wirklich guten*
Angebote (effektiver Rabatt ≥ 30 %) und baut daraus ein eigenständiges
HTML-Dashboard. Läuft lokal, für den privaten Einkauf.

```bash
python pipeline.py                                  # PLZ 1010, ab −30 %, alle Quellen
python pipeline.py --plz 4020 --min-pct 40 --stores BILLA,SPAR,HOFER
```

Ergebnis: **`out/angebote.html`** (per Doppelklick öffnen), zusätzlich
`out/angebote.csv` und `out/angebote.json`.

## Was „gut" heißt

Aufnahme nur, wenn der **zugesagte effektive Rabatt ≥ `--min-pct`** ist. Die
Umrechnung von Mengen-Aktionen ist das Herzstück (`core/discount.py`):

| Aktionstext | effektiv | drin bei ≥30 %? |
|---|---|---|
| 1+1 gratis · jeder 2. gratis | −50 % | ✅ |
| 2+1 gratis · 3 für 2 · jeder 3. gratis | −33 % | ✅ |
| −30 % | −30 % | ✅ |
| 3+1 gratis | −25 % | ❌ |
| jeder 2. zum halben Preis | −25 % | ❌ |
| „bis zu −50 %" | unbestimmt | ❌ (Obergrenze, kein zugesagter Rabatt) |

## Datenquellen (Stand August 2026)

| Adapter | Typ | Abdeckung | robots.txt |
|---|---|---|---|
| **marktguru** (`sources/marktguru.py`) | interne JSON-API | BILLA, BILLA PLUS, SPAR, EUROSPAR, INTERSPAR, HOFER, PENNY, Lidl … | `api.marktguru.at` erlaubt `/api/` ausdrücklich |
| **BILLA** (`sources/billa.py`) | offizielle JSON-API `product-discovery` | BILLA (bester Detailgrad, exakter Rabatt) | `shop.billa.at` erlaubt alles |
| **PENNY** (`sources/penny.py`) | dieselbe API (REWE-Gruppe) | PENNY, **inkl. echter Aktionszeiträume** | `penny.at` erlaubt alles |

BILLA und PENNY teilen sich den Parser in `sources/rewe_shop.py` — beide Ketten
betreiben dieselbe Shop-Software. Zwei Eigenheiten sind dort abgefangen:
Geblättert wird über `page` (nicht `offset`), und PENNY meldet `inPromotion:
false` auch bei echten Aktionen — verlässlich ist nur `discountPercentage`.

Zusammen liefern sie echte Daten aus über 15 Ketten. Aggregatoren wie prospektmaschine.at,
kimbino.at und preisrunter.at sperren ihre Datenpfade per robots.txt und werden
**nicht** gecrawlt; aktionsfinder.at ist offline.

**Eine ehrliche Lücke:** Die BILLA-API liefert **kein Aktions-Enddatum**
(Online-Aktionen sind rollierende Wochenpreise). BILLA-Angebote bekommen deshalb
ein Wochenfenster (bis kommenden Samstag, konfigurierbar in `sources/billa.py`,
`_week_end`). marktguru liefert exakte Datumsangaben.

## Fairness

Ehrlicher User-Agent mit Kontakt, **max. 1 Request/s pro Domain**, Retry mit
Backoff, `If-Modified-Since`/`ETag`, On-Disk-Cache in `data/cache/` (TTL 3–6 h).
robots.txt wird respektiert; kein Umgehen von Login/Bezahlung; keine
Weiterveröffentlichung fremder Prospektbilder (nur Verlinkung).

## Architektur

```
core/discount.py   Aktionstext -> effektiver Rabatt (+ Kundenkarte, Mehrfachkauf)
core/quantity.py   Mengen normalisieren ("6 x 1,5 l" -> Basis) + Grundpreis
core/models.py     dataclass Offer + Validierung (leere Pflichtfelder -> verworfen)
core/http.py       höflicher HTTP-Client (Cache, Rate-Limit, Retry, Conditional)
sources/*.py       Adapter, Vertrag:  def fetch(zip_code="1010") -> list[Offer]
render.py          baut out/angebote.html (Dark Mode, Filter, Einkaufsliste, NEU)
pipeline.py        Adapter -> Dedupe -> Filter -> Historie -> Render (fehlertolerant)
```

Neue Adapter in `ADAPTERS` in `pipeline.py` eintragen (Reihenfolge = Priorität
beim Dedupe). Ein abstürzender Adapter bricht den Lauf nie ab.

## Dashboard

**Mobile first.** Unter 780 px erscheinen die Angebote als Karten mit großen
Tippflächen, darüber als Raster mit sortierbaren Spalten. Auf dem Handy sind
die Detailfilter hinter dem Knopf „Filter" eingeklappt; Chip-Reihen scrollen
seitlich.

- **Favoriten** — Stern je Angebot. Sie liegen im Browser des Betrachters
  (`localStorage`) und **überleben die wöchentliche Aktualisierung**, weil der
  Schlüssel aus Geschäft + Produkt + Menge besteht und nicht aus einer Lauf-ID.
  Filter „nur Favoriten"; Angebote, die gerade ausgelaufen sind, bleiben
  gespeichert und werden unter der Liste vermerkt.
- **Filter in beschrifteten Abschnitten** — Rabatt, Kategorie, Unterkategorie,
  Geschäft, Weitere. Am Handy öffnen sie sich als Blatt von unten (Verdunkelung,
  Escape/Tippen daneben schließt, „Zurücksetzen" und „N Angebote zeigen" unten),
  am Desktop stehen sie fest im Panel. Vorher lagen fünf gleich aussehende
  Chip-Reihen unbeschriftet in der Kopfleiste.
- **Aktive Filter sind immer sichtbar** — als Chips mit ×, dazu „alle löschen".
  Der Filterknopf trägt die Anzahl. Ohne das ist nicht erkennbar, warum nur noch
  2 von 693 Angeboten übrig sind.
- **Rabattbänder als Mehrfachauswahl** — −30 %, −40 %, −50 %, −60 %+ einzeln oder
  kombiniert (nichts gewählt = alle), jeweils mit Trefferzahl.
- **Unterkategorie** erscheint erst, wenn eine Kategorie gewählt ist.
- **Miniaturbilder** für BILLA und PENNY (420 von 693). Verwendet wird die
  `-small`-Variante des CDN (rund 5 KB statt 176 KB), `loading="lazy"`; fehlende
  Bilder werden ausgeblendet. Die Bilder werden **verlinkt, nicht kopiert**.
  marktguru sperrt seinen Bild-CDN mit HTTP 403, dort bleibt der Platz leer.
- Suche, Geschäfts-Chips mit Anzahl, Sortierung nach jeder Spalte, Dark Mode
- **Einkaufsliste drucken** — die Favoriten, nach Geschäft gruppiert (ohne
  Favoriten: die aktuelle Ansicht)
- **NEU-Badge** gegenüber dem letzten Lauf (`data/last_run.json`)
- Badges: Mehrfachkauf nötig, Kundenkarte, „ab <Datum>", „Größe variiert",
  Scheinrabatt-Warnung
- Filter „nur NEU" / „ohne Mehrfachkauf" / „ohne Kundenkarte"

## Datenqualität

- **Grundpreis** wird selbst berechnet, wenn die Quelle keinen liefert (€/kg, €/l, €/Stk).
- **Mehrfachkauf** sichtbar (`requires_qty`, Badge) — bei „2+1" gilt der Rabatt nur für 3 Stück.
- **Kundenkarten-Aktionen** (jö, SPAR/PENNY/Lidl-App) markiert und filterbar.
- **Scheinrabatt-Check**: bei ≥ 4 Beobachtungen der letzten 90 Tage
  (`data/history.jsonl`) wird der Rabatt zusätzlich gegen den Median gerechnet;
  Abweichung > 10 Prozentpunkte → Warn-Badge.
- **Dedupe** über Quellen (exakter Key + konservatives Fuzzy: gleiches Geschäft +
  gleiche Basismenge + identische Namens-Wörter).
- **Gültigkeit**: abgelaufene Angebote raus, künftige bleiben mit „ab"-Markierung.
  Alle Datumsangaben laufen über `Europe/Vienna` — marktguru liefert UTC, und der
  GitHub-Runner arbeitet ebenfalls in UTC.
- **Kategorien**: Die Quellen liefern ~145 verschiedene Kategorien. `core/categories.py`
  fasst sie schlüsselwortbasiert zu 14 Einkaufs-Gruppen zusammen, damit der Filter
  im Dashboard benutzbar bleibt. Die feine Original-Kategorie bleibt als
  `category_detail` in CSV und JSON erhalten. Als zweite Filterebene dienen die
  Quell-Kategorien selbst (rund 10 je Gruppe), bereinigt um Schreibvarianten:
  „Weissweine"/„Weißwein" -> „Weißwein", „Dosenbier"/„Flaschenbier" -> „Bier".

## Monitoring

Exit-Code ≠ 0 (+ Logzeile auf stderr), wenn eine Quelle **0 Treffer** liefert
oder der Lauf **< 50 %** der Angebote der Vorwoche findet. Stillschweigend leere
Ergebnisse sind der schlimmste Fehlerfall — deshalb laut.

## Tests (offline, ohne Netzwerk)

```bash
python tests/test_discount.py         # Rabatt-Engine (44 Fälle)
python tests/test_quantity.py         # Mengen + Grundpreis (20 Fälle)
python tests/test_categories.py       # Kategorien + Unterkategorien
python tests/test_billa.py            # BILLA-Parser gegen Fixture
python tests/test_penny.py            # PENNY-Parser gegen Fixture
python tests/test_marktguru.py        # marktguru-Parser gegen Fixture
python tests/test_marktguru_fixes.py  # Zeitzone, Einheiten, Grundpreis
python tests/test_resilience.py       # kaputter Adapter bricht Lauf nicht ab
python tests/check_output.py          # Abnahme-Check über out/angebote.json
```

Fixtures (gespeicherte Rohantworten) liegen in `tests/fixtures/`.

## Online stellen (damit alle immer die aktuelle Liste sehen)

Eine verschickte HTML-Datei ist ein Schnappschuss und altert beim Empfänger.
Wer die Liste weitergeben will, verschickt daher besser **einen Link**.

`.github/workflows/update.yml` erledigt das: Donnerstagfrüh läuft der Radar in
der GitHub-Cloud, aktualisiert die Seite und veröffentlicht sie über GitHub
Pages — der eigene Rechner muss dafür nicht laufen. Die Preishistorie wird ins
Repo zurückgeschrieben, damit NEU-Badge und Scheinrabatt-Warnung auch dort
über Wochen funktionieren.

Schritt-für-Schritt: **[SETUP-GITHUB.md](SETUP-GITHUB.md)**

Die veröffentlichte Seite trägt `noindex` und eine sperrende `robots.txt`,
landet also nicht in Suchmaschinen. Es werden ausschließlich Text und Zahlen
gezeigt, keine Prospektbilder — die werden nur verlinkt.

## Automatisierung

AT-Flugblätter starten meist Do/Fr → einmal Donnerstagfrüh reicht.

**Windows (Aufgabenplaner):** `run.cmd` liegt bei. Task anlegen:

```bat
schtasks /Create /TN "Prospekt-Radar" /TR "C:\Users\thoma\Downloads\prospekt-radar\run.cmd" /SC WEEKLY /D THU /ST 06:00
```

**Linux (cron):**

```cron
0 6 * * 4 cd /pfad/prospekt-radar && /usr/bin/python3 pipeline.py --plz 1010 >> data/run.log 2>&1
```

**macOS (launchd):** `~/Library/LaunchAgents/at.prospektradar.plist`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>at.prospektradar</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/python3</string>
    <string>/pfad/prospekt-radar/pipeline.py</string>
    <string>--plz</string><string>1010</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict><key>Weekday</key><integer>4</integer><key>Hour</key><integer>6</integer><key>Minute</key><integer>0</integer></dict>
  <key>StandardOutPath</key><string>/pfad/prospekt-radar/data/run.log</string>
  <key>StandardErrorPath</key><string>/pfad/prospekt-radar/data/run.log</string>
</dict></plist>
```

`launchctl load ~/Library/LaunchAgents/at.prospektradar.plist`
