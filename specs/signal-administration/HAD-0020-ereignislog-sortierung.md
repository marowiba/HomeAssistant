# HAD-0020: Ereignislog – Sammelauswahl und sortierbare Spaltenköpfe

## Ziel

Die Ereignisliste unter `/events` wird bedienbarer: eine Checkbox in der
Kopfzeile schaltet alle Zeilen der aktuellen Seite, und die Spaltenköpfe
sortieren auf- und absteigend. Standard ist der jüngste Eintrag oben.

## Ausgangslage

- `events_page` rendert die Zeilen in Dateireihenfolge, also den ältesten
  Eintrag zuerst.
- Die Zeilen-Checkboxen sind über `form="delete-form"` mit dem Löschformular
  verbunden.
- Die CSP in `app.py` setzt `script-src 'self'`; Inline-Handler sind blockiert.

## Umsetzung

### S1: Sortierung

- `events.sort_events(events, sort_key, direction)` sortiert stabil.
- Erlaubte Schlüssel: `ts`, `sender`, `text`, `decision`, `command`.
- Erlaubte Richtungen: `asc`, `desc`.
- Unbekannte Werte fallen auf `ts` und `desc` zurück.
- `ts` nutzt `received_ms`, nullgepolstert, sonst den ISO-Zeitstempel.
- `sender` nutzt `sender_name`, sonst `sender_number`.
- Sortiert wird nach dem Filtern und vor der Paginierung.

### S2: Spaltenköpfe

- Jeder sortierbare Kopf ist ein Link auf `/events` mit `sort` und `dir`.
- Der aktive Kopf zeigt ▲ für aufsteigend und ▼ für absteigend.
- Ein Klick auf den aktiven Kopf kehrt die Richtung um, ein Klick auf einen
  anderen Kopf setzt aufsteigend.
- Filterformular und Blätterlinks tragen `sort` und `dir` mit.

### S3: Sammelauswahl

- Die erste Kopfzelle enthält eine Checkbox ohne `name`, also nicht Teil des
  Löschformulars.
- Die Zeilen-Checkboxen tragen `data-row-select`, die Tabelle
  `data-select-scope`.
- `signal_admin/static/admin.js` reagiert auf Änderungen der Kopf-Checkbox,
  setzt alle Zeilen-Checkboxen im Bereich und schaltet das versteckte Feld
  `select_all` im Löschformular auf `1`.
- Der Server löscht bei `select_all=1` alle Ereignisse, die dem aktuellen
  Filter entsprechen, nicht nur die sichtbaren IDs. Das Löschformular trägt
  dafür die Filter `q`, `decision`, `command`, `from` und `to` als versteckte
  Felder.
- Bestätigungen laufen über `data-confirm` und `data-confirm-all` in
  `admin.js`, weil die CSP Inline-Handler blockiert.
- Das Skript wird im Layout mit `<script src="/static/admin.js" defer>`
  geladen.

## Entscheidungen

- **E1:** Sortierung über Query-Parameter, nicht über JavaScript. Damit
  funktioniert sie ohne Skript und bleibt in Lesezeichen und Links erhalten.
- **E2:** Weiße Liste für `sort` und `dir`; keine dynamischen Schlüssel.
- **E3:** Sammelauswahl über eine statische Datei, weil die CSP Inline-Handler
  blockiert.
- **E4:** Die Kopf-Checkbox wird nicht übertragen, damit sie die Löschauswahl
  nicht verfälscht.

## Verifikation

- Standardreihenfolge ist `ts` absteigend.
- Beide Richtungen für alle fünf Spalten.
- Ungültige Werte fallen auf den Standard zurück.
- Sortierung bleibt beim Filtern und Blättern erhalten.
- Kopf- und Zeilen-Checkboxen tragen die erwarteten Attribute.
- `admin.js` wird mit `application/javascript` ausgeliefert.
- 440 Tests grün, 100 % Zeilenabdeckung (2220 Zeilen).
- SonarQube: 0 Issues, 0 Duplikate, Quality Gate OK. Bericht
  `tests/sast/reports/2026-11-18_12-11-53_sonar_summary.md`.
- UAT am 2026-11-18: Sortierung in beide Richtungen, Sammelauswahl löscht
  alle gefilterten Einträge, Bestätigungen erscheinen.
- Statische Assets sind von der Coverage ausgenommen, weil kein JS-Testrunner
  vorhanden ist; sie bleiben in der Analyse.
