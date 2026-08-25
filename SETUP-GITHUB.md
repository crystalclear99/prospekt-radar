# Prospekt-Radar online stellen — Schritt für Schritt

Ziel: **eine feste Adresse**, die du an alle verschickst. Donnerstagfrüh
aktualisiert sich die Seite von selbst in der GitHub-Cloud. Dein PC muss dafür
nicht laufen.

Einmalig ~15 Minuten. Danach nie wieder anfassen.

---

## Was GitHub überhaupt ist (30 Sekunden)

GitHub ist ein Online-Speicher für Programmcode. Wir brauchen davon zwei Dinge:

* **Actions** — führt dein Programm nach Zeitplan auf GitHubs Servern aus.
* **Pages** — macht aus einer HTML-Datei eine öffentliche Webseite.

Beides ist kostenlos. Du lädst also den Ordner hoch, und GitHub übernimmt
Ausführen und Ausliefern.

---

## Schritt 1 — Konto anlegen

Falls du noch keins hast: **https://github.com/signup**

Du brauchst E-Mail, Passwort und einen Benutzernamen. **Merk dir den
Benutzernamen genau** — er steckt später in deiner Webadresse. Nimm etwas
Kurzes ohne Sonderzeichen.

E-Mail-Bestätigung nicht vergessen, sonst geht Schritt 5 nicht.

> Im Folgenden schreibe ich überall `DEINNAME`. Ersetze das durch deinen
> echten GitHub-Benutzernamen.

---

## Schritt 2 — Repository anlegen

Ein „Repository" (kurz Repo) ist einfach ein Projektordner auf GitHub.

Gehe auf **https://github.com/new** und trage ein:

| Feld | Was rein muss |
|---|---|
| **Repository name** | `prospekt-radar` |
| **Description** | leer lassen (oder irgendwas) |
| **Public / Private** | **Public** anklicken |
| Add a README file | ❌ **NICHT** ankreuzen |
| Add .gitignore | ❌ auf `None` lassen |
| Choose a license | ❌ auf `None` lassen |

Dann unten **„Create repository"**.

> ⚠️ **Die drei Häkchen müssen wirklich leer bleiben.** Wenn GitHub schon
> Dateien anlegt, kollidiert das mit deinem Ordner und der Upload in Schritt 4
> wird abgelehnt.

> **Warum Public?** Pages funktioniert bei privaten Repos nur im Bezahltarif.
> Die *Seite* bleibt trotzdem unauffindbar (`noindex` + sperrende
> `robots.txt`) — wer die Adresse nicht kennt, findet sie nicht. Öffentlich
> lesbar ist der **Programmcode**. Wenn dich das stört, sag mir Bescheid,
> dann bauen wir es auf Cloudflare Pages um.

Nach dem Klick landest du auf einer Seite mit Anleitungen — **die kannst du
ignorieren**, wir machen es gleich selbst.

---

## Schritt 3 — Zwei Einstellungen setzen

Diese beiden Schalter entscheiden, ob es funktioniert. **Bitte nicht
überspringen.**

### 3a) Actions darf schreiben

Im Repo oben auf **Settings** (Zahnrad) → links unten **Actions** →
**General** → runterscrollen zu **„Workflow permissions"**:

* ✅ **„Read and write permissions"** auswählen
* Dann **Save** drücken

> Ohne das kann der Roboter die Preishistorie nicht zurückschreiben und der
> ganze Lauf bricht mit einem Rechte-Fehler ab. GitHub stellt neue Repos
> standardmäßig auf „nur lesen".

### 3b) Pages auf Actions umstellen

Immer noch in **Settings** → links **Pages** → unter **„Build and deployment"**:

* **Source**: von „Deploy from a branch" auf **„GitHub Actions"** umstellen

Mehr ist dort nicht einzustellen. Es gibt keinen Speichern-Knopf, das
übernimmt sofort.

---

## Schritt 4 — Deinen Ordner hochladen

Jetzt kommt der einzige Schritt mit Tastatur.

1. Öffne den Ordner `C:\Users\thoma\Downloads\prospekt-radar` im Explorer
2. **Rechtsklick auf eine freie Stelle** im Ordner → **„Im Terminal öffnen"**
   (falls das fehlt: „Weitere Optionen anzeigen" → „Git Bash Here")
3. Diese zwei Zeilen eintippen, `DEINNAME` ersetzt:

```bash
git remote add origin https://github.com/DEINNAME/prospekt-radar.git
git push -u origin main
```

**Beim ersten `push` fragt GitHub nach dem Login:**
Es öffnet sich ein Fenster „Connect to GitHub" → **„Sign in with your browser"**
→ im Browser mit deinem Konto anmelden → **„Authorize"**. Danach läuft es
durch. Passwort im Terminal eintippen funktioniert bei GitHub **nicht** mehr,
das ist normal.

Wenn alles gut ging, endet es mit ungefähr:

```
branch 'main' set up to track 'origin/main'.
```

Lade jetzt die Repo-Seite im Browser neu — deine Dateien müssen da sein.

---

## Schritt 5 — Ersten Lauf starten

1. Im Repo oben auf **Actions**
2. Falls eine blaue Box erscheint („Workflows aren't being run…"), auf
   **„I understand my workflows, go ahead and enable them"** klicken
3. Links auf **„Angebote aktualisieren"**
4. Rechts der graue Knopf **„Run workflow"** → im Aufklappmenü nochmal den
   grünen **„Run workflow"**

Nach ein paar Sekunden erscheint ein Eintrag mit gelbem Punkt (läuft) →
grünem Haken (fertig). **Dauert 2–4 Minuten.** Zum Zuschauen draufklicken.

---

## Schritt 6 — Deine Adresse

Nach dem grünen Haken ist deine Seite hier:

```
https://DEINNAME.github.io/prospekt-radar/
```

Du findest sie auch unter **Settings → Pages**, dort steht sie ganz oben.

**Diese Adresse verschickst du.** Sie bleibt für immer gleich, der Inhalt wird
donnerstags automatisch frisch. Jeder, der sie öffnet, sieht die aktuelle Liste.

---

## Danach: PLZ oder Rabatt ändern (ohne Code)

**Settings → Secrets and variables → Actions** → Reiter **Variables** →
**New repository variable**:

| Name | Beispiel | Bedeutung |
|---|---|---|
| `PLZ` | `4652` | deine Postleitzahl |
| `MIN_PCT` | `40` | Mindestrabatt in Prozent |

Ohne diese Variablen gelten 4652 und 30 %. Nach dem Ändern einmal
**Actions → Run workflow** drücken, damit es sofort greift.

---

## Wann läuft es automatisch?

Donnerstag **06:00 Wiener Zeit** (im Winter 05:00 — GitHub rechnet in UTC).
AT-Flugblätter starten meist Do/Fr, deshalb dieser Tag.

Zwischendurch manuell: **Actions → Run workflow**. So oft du willst.

---

## Wenn etwas nicht klappt

| Symptom | Ursache / Lösung |
|---|---|
| `push` sagt „Authentication failed" | Browser-Anmeldung abgebrochen. Nochmal `git push -u origin main`. |
| `push` sagt „rejected / fetch first" | In Schritt 2 doch ein Häkchen gesetzt. Lösung: `git push -u origin main --force` |
| `remote origin already exists` | Schon mal ausgeführt. Dann: `git remote set-url origin https://github.com/DEINNAME/prospekt-radar.git` |
| Lauf rot, „Permission denied" beim Push | Schritt 3a vergessen (Read and write permissions). |
| Actions-Lauf grün, aber Seite ist 404 | Schritt 3b vergessen, oder die ersten Minuten nach dem allerersten Deploy — kurz warten und neu laden. |
| Gelbe Warnung im Lauf | Eine Quelle lieferte nichts oder deutlich weniger als sonst. Seite wird trotzdem aktualisiert, Details im Protokoll. |
| Lauf komplett fehlgeschlagen | **Die alte Seite bleibt online.** Deine Empfänger sehen nie eine leere Liste. |

Jeder Lauf ist im Tab **Actions** mit vollem Protokoll nachlesbar. Draufklicken,
dann auf „build", dann den roten Schritt aufklappen.

---

## Ein Restrisiko, ehrlich gesagt

Die Datenquellen werden dann von GitHub-Servern abgefragt, nicht von deinem
Anschluss. Sollten marktguru oder BILLA solche Cloud-Zugriffe irgendwann
sperren, schlägt der Lauf fehl (die letzte gute Seite bleibt stehen). Der
Umstieg wäre klein: Zeitplan im Workflow rausnehmen und stattdessen den
Windows-Aufgabenplaner von zuhause hochladen lassen. Sag Bescheid, falls es
so weit kommt.
