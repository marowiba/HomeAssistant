# HAD-0007: SonarQube anbinden und SAST-Reporting einrichten

## Ziel

Die Python-Komponenten der Signal-Integration werden statisch mit SonarQube
geprüft. Der Scan ist reproduzierbar, läuft lokal und erzeugt einen Summary- und
einen Detailbericht. Der initiale Scan wird mit 0 offenen Issues, 0 Duplikaten
und bestandenem Quality Gate abgeschlossen.

## Ausgangslage

- SonarQube 26.8.0 unter `http://sonar.srv001`, Projekt-Key `HAD`.
- SonarScanner CLI 6.2.1.4610 unter `C:\sonar-scanner\bin`.
- Python 3.14 mit `pytest` und `coverage`.
- Vorbild: `GnuCashReporting/tests/dast/run-sonar-scan.ps1`.

## Umsetzung

### S1: Scan-Skript

`tests/sast/run-sonar-scan.ps1` führt die Tests mit Coverage aus, startet den
Scanner und ruft Quality Gate, Issues und Metriken über die REST-API ab. Es
schreibt `reports/<zeitstempel>_sonar_summary.md` und
`reports/<zeitstempel>_sonar_details.md` und entfernt ältere Berichte.

### S2: Token-Handhabung

Der Token wird in dieser Reihenfolge aufgelöst: `-Token`, `.env`,
`SONAR_TOKEN`. `.env` ist über `.gitignore` ausgeschlossen. Ein global gesetztes
`SONAR_TOKEN` (aus einem anderen Projekt) überschreibt `.env` nicht; das Skript
warnt und setzt die Variable für den Lauf auf den aufgelösten Wert.

### S3: Analyseumfang

`sonar.sources=signal-bridge`, `sonar.tests=signal-bridge/tests`,
`sonar.exclusions=signal-bridge/tests/**`. Ohne den Ausschluss indexiert der
Scanner Testdateien doppelt.

### S4: Findings beheben

Der erste Scan meldete 19 Issues. Behoben wurden:

| Regel | Anzahl | Maßnahme |
| :--- | :--- | :--- |
| `python:S1192` | 2 | URL-Schema-Literale durch `_is_http_url()` mit `urlparse` ersetzt |
| `python:S5332` | 4 | keine `http://`-Literale mehr, Prüfung über `urlparse` |
| `python:S3776` | 3 | `_parse_home_assistant`, `send_message` und `run` in Hilfsfunktionen zerlegt |
| `python:S5713` | 2 | `except OSError` statt redundanter Unterklassen |
| `python:S8572` | 1 | `LOG.exception` statt `LOG.error` im Except-Block |
| `python:S5778` | 7 | `self.write(...)` aus dem `assertRaises`-Block gezogen |

### S5: Verifikation

- 83 Tests grün.
- Quality Gate: OK.
- Offene Issues: 0 (Security 0, Reliability 0, Maintainability 0).
- Duplikate: 0.0 %, 0 Zeilen, 0 Blöcke, 0 Dateien.
- Coverage: 85.8 % (614 zu deckende Zeilen, 87 nicht gedeckt).

## Entscheidungen

- **E1:** SAST statt DAST, Verzeichnis `tests/sast`.
- **E2:** Berichte lokal und gitignoriert; keine Versionierung von
  Scan-Ergebnissen.
- **E3:** Token nur in `.env` oder als Parameter, nie im Repository.
- **E4:** Findings im Code beheben, keine Regel-Deaktivierung.
- **E5:** Scan nach UAT/Freigabe, dokumentiert in `DEV Prompt.md`.

## Ergebnis

Der Scan ist eingerichtet und verifiziert. Der Ablauf ist in
`tests/sast/README.md` und `DEV Prompt.md` dokumentiert.
