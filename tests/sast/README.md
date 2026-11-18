# SAST – SonarQube-Scan und Berichte

Statische Analyse des Projekts gegen den SonarQube-Server im Heimnetz.
Vorbild ist das Verfahren aus `GnuCashReporting/tests/dast`, hier als SAST
umgesetzt.

## Voraussetzungen

| Voraussetzung | Prüfung |
| :--- | :--- |
| SonarQube erreichbar | `curl -s -o /dev/null -w "%{http_code}" http://sonar.srv001/` |
| Projekt `HAD` vorhanden | im SonarQube-Web unter Projekte |
| SonarScanner | `C:\sonar-scanner\bin\sonar-scanner.bat` |
| Python mit `pytest` und `coverage` | `python -m coverage --version` |

## Token

Der Token ist ein Zugangsmerkmal und gehört **nicht** ins Repository. Drei Wege,
in dieser Reihenfolge:

1. `-Token` als Parameter beim Aufruf
2. Datei `.env` im Projektwurzelverzeichnis mit `SONAR_TOKEN=...`
3. Umgebungsvariable `SONAR_TOKEN` in der aktuellen Sitzung

Die Datei `.env` ist über `.gitignore` ausgeschlossen. Sie enthält nur diesen
einen Wert und wird nicht versioniert.

Die Reihenfolge ist bewusst: Ein global gesetztes `SONAR_TOKEN` (etwa aus einem
anderen Projekt) darf den projektspezifischen Wert aus `.env` nicht
überschreiben. Weicht die Umgebungsvariable ab, gibt das Skript eine Warnung aus
und verwendet für den Lauf den Wert aus `.env`.

## Aufruf

```powershell
.\tests\sast\run-sonar-scan.ps1
```

Mit abweichendem Server oder Projekt:

```powershell
.\tests\sast\run-sonar-scan.ps1 -SonarHostUrl "http://sonar.srv001" -ProjectKey "HAD"
```

## Ablauf

1. Tests mit Coverage ausführen, `coverage.xml` erzeugen
2. `sonar-scanner` gegen `http://sonar.srv001` starten
3. Auf die Serververarbeitung warten
4. Quality Gate, Issues und Metriken über die REST-API abrufen
5. Summary und Details schreiben, ältere Berichte entfernen

## Berichte

| Datei | Inhalt |
| :--- | :--- |
| `reports/<zeitstempel>_sonar_summary.md` | Quality Gate, Issue-Zahlen, Schweregrade, Top-Regeln, Coverage gesamt und je Datei, Duplikate |
| `reports/<zeitstempel>_sonar_details.md` | jede offene Issue mit Datei, Zeile und Meldung; nicht abgedeckte Zeilen je Quelldatei |

Der Ordner `tests/sast/reports/` ist von Git ausgeschlossen. Es bleibt immer nur
der letzte Lauf liegen.

## Umfang der Analyse

| Einstellung | Wert |
| :--- | :--- |
| `sonar.sources` | `signal-bridge`, `signal-admin` |
| `sonar.tests` | `signal-bridge/tests`, `signal-admin/tests` |
| `sonar.coverage.exclusions` | `signal-admin/signal_admin/static/**` (kein JS-Testrunner) |
| `sonar.python.coverage.reportPaths` | `coverage.xml` |
| `sonar.python.version` | `3.14` |

Dokumentation, Deployment-Vorlagen und Spezifikationen werden nicht analysiert.

## Testabdeckung

Ziel ist **100 %** Zeilenabdeckung der Quelldateien. Die Tests werden mit
`coverage.py` gemessen; Testdateien selbst zählen nicht mit
(`--omit="signal-bridge/tests/*"`).

- Der Summary-Bericht enthält eine Tabelle „Testabdeckung je Datei".
- Der Detailbericht listet unter „Nicht abgedeckte Zeilen (Coverage)" je
  Quelldatei die noch nicht abgedeckten Zeilennummern.
- Nicht abgedeckte Zeilen werden durch zusätzliche Tests geschlossen, nicht
  durch Ausschlüsse. Ausnahme ist nur der `__main__`-Block, der nicht
  importierbar ist.

## Prozessregel

Der Scan läuft **nach** dem UAT- und Freigabeschritt, nicht davor. Der Ablauf ist
in `DEV Prompt.md` festgehalten. Ein Scan vor der Freigabe würde Findings zu
Code melden, der noch geändert wird.
