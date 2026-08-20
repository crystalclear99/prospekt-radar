# Prospekt-Radar online stellen (GitHub Pages)

Ziel: eine feste Adresse, die du an alle verschickst. Donnerstagfrüh aktualisiert
sich die Seite **von selbst in der GitHub-Cloud** — dein PC muss dafür nicht laufen.

Einmalig einzurichten, danach nie wieder anfassen.

---

## 1. GitHub-Konto

Falls noch keins: https://github.com/signup (kostenlos).
Merk dir deinen Benutzernamen — er steckt später in der Adresse.

## 2. Repository anlegen

https://github.com/new

| Feld | Wert |
|---|---|
| Repository name | `prospekt-radar` |
| Sichtbarkeit | **Public** |
| Add a README / .gitignore / license | **alle drei leer lassen** |

„Create repository" klicken.

> **Warum Public?** GitHub Pages ist bei privaten Repos nur mit dem
> kostenpflichtigen Pro-Tarif verfügbar. Die Seite selbst wird trotzdem
> nicht gefunden: sie enthält `noindex` und eine `robots.txt`, die
> Suchmaschinen aussperrt. Wer die Adresse nicht kennt, findet sie nicht.
> Der *Code* ist dann öffentlich lesbar — deine Angebotsliste ist ohnehin
> nichts Geheimes. Willst du das nicht, nimm stattdessen Cloudflare Pages
> (dann muss aber dein PC donnerstags laufen).

## 3. Hochladen

Terminal im Projektordner öffnen (Rechtsklick in
`C:\Users\thoma\Downloads\prospekt-radar` → „Im Terminal öffnen") und
`DEINNAME` durch deinen GitHub-Benutzernamen ersetzen:

```bash
git remote add origin https://github.com/DEINNAME/prospekt-radar.git
git push -u origin main
```

Beim ersten Mal fragt Git nach Login — ein Browserfenster öffnet sich,
dort mit GitHub anmelden und bestätigen.

## 4. Pages einschalten

Im Repo auf **Settings → Pages**:

- **Source**: `GitHub Actions` auswählen (nicht „Deploy from a branch")

Das war's. Mehr ist dort nicht einzustellen.

## 5. Ersten Lauf starten

Im Repo auf **Actions** → links „Angebote aktualisieren" → rechts
**„Run workflow"** → grünen Knopf drücken.

Dauert 2–4 Minuten. Danach ist deine Seite hier:

```
https://DEINNAME.github.io/prospekt-radar/
```

**Diesen Link verschickst du.** Er bleibt immer gleich, der Inhalt wird
donnerstags automatisch frisch.

---

## PLZ oder Rabattschwelle ändern

Ohne den Code anzufassen: **Settings → Secrets and variables → Actions →
Variables → New repository variable**

| Name | Beispiel | Bedeutung |
|---|---|---|
| `PLZ` | `4652` | deine Postleitzahl |
| `MIN_PCT` | `30` | Mindestrabatt in Prozent |

Ohne diese Variablen gelten die Vorgaben 4652 und 30 %.

## Wann läuft es?

Donnerstag 04:00 UTC = **06:00 Wiener Zeit** (im Winter 05:00). AT-Flugblätter
starten meist Do/Fr. Manuell anstoßen geht jederzeit über Actions → Run workflow.

## Wenn mal etwas schiefgeht

- Im Tab **Actions** steht jeder Lauf mit Protokoll.
- Meldet eine Quelle 0 Treffer oder bricht die Angebotszahl gegenüber der
  Vorwoche um mehr als die Hälfte ein, erscheint dort eine **gelbe Warnung** —
  die Seite wird trotzdem aktualisiert.
- Schlägt der Lauf ganz fehl, bleibt die **letzte funktionierende Version
  online**. Deine Empfänger sehen nie eine leere Seite.
- Die Offline-Tests laufen vor jedem Update mit. Sind sie rot, wird gar nicht
  erst deployt.

## Ein Restrisiko, ehrlich gesagt

Die Datenquellen werden von GitHub-Servern in der Cloud abgefragt, nicht von
deinem Anschluss aus. Sollte marktguru oder BILLA solche Zugriffe irgendwann
blocken, schlägt der Lauf fehl (die alte Seite bleibt online). Dann ist der
Umstieg klein: Zeitplan in `.github/workflows/update.yml` entfernen und
stattdessen den Windows-Aufgabenplaner nutzen (siehe README), der die
fertige Seite von zuhause hochlädt.
