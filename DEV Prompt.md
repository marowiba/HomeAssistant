# Dev Prompt - Home Assistant Developments

## Aktuelles Ticket

Das aktive Ticket wird in `backlog.md` unter `## 🟡 IN PROGRESS` geführt.
Ticket-ID und Beschreibung sind vor Arbeitsbeginn zu prüfen; der Umfang des
Tickets ist verbindlich.

## Dokumentstruktur

- `backlog.md` führt offene und laufende Tickets, `backlog_done.md` die
  erledigten.
- `specs/<epic>/` enthält die Designs, ein Unterordner pro Epic. Der Ordnername
  entspricht der Spalte `Feature` in `backlog.md` in Kleinschreibung, Umlaute
  transliteriert (`ä` zu `ae`, `ö` zu `oe`, `ü` zu `ue`, `ß` zu `ss`).
- `specs/dashboards/` ist eine dokumentierte Ausnahme ohne Feature im Backlog.
- `specs/<epic>/design.md` ist das Epic-Design,
  `specs/<epic>/HAD-xxxx-<thema>.md` das Solution Design je Ticket.
- `deploy/<dienst>/` enthält systemd-Units und Konfigurationsvorlagen.
- Querverweise immer mit vollständigem Pfad ab Repository-Wurzel.
- Bei Widersprüchen gilt: Ticket vor Solution Design vor Epic-Design.

## Workflow

1. Ticket in `backlog.md` nach `## 🟡 IN PROGRESS` verschieben und Status
   aktualisieren.
2. Vor Änderungen die betroffene Home-Assistant-Konfiguration, zugehörige
   Spezifikationen und vorhandene Arbeitsabläufe prüfen.
3. Die kleinste vollständige Lösung umsetzen. Home-Assistant-Entitäten,
   Dienstaufrufe und Signal-Absender nicht dynamisch aus unvalidierten
   Nutzereingaben ableiten. Keine Zugangsdaten oder Schlüssel ins Repository
   schreiben.
4. Verfügbare, relevante Tests und Repository-Linter ausführen. Bestehende
   Konventionen und Abdeckung beachten; Ergebnisse wahrheitsgemäß festhalten
   und keine nicht vorhandenen Testwerkzeuge oder Grenzwerte voraussetzen.
5. Direkt betroffene Dokumentation und Spezifikationen aktualisieren. Ideen
   außerhalb des Ticketumfangs in `backlog.md` unter `## 🟡 Ideen` notieren.
6. Nach erfolgreicher Umsetzung das Ticket von `backlog.md` nach
   `backlog_done.md` unter `## 🟢 Erledigt` verschieben. ID und Feature bleiben
   erhalten.
7. Änderungen an der laufenden Home-Assistant-Installation, Server-Deployments
   oder Neustarts nur durchführen, wenn sie im Ticket ausdrücklich vorgesehen
   sind und der Benutzer sie freigegeben hat. Commits nur auf ausdrücklichen
   Wunsch erstellen.

## SAST und Codequalität

Die statische Analyse läuft über SonarQube (`http://sonar.srv001`, Projekt-Key
`HAD`) mit dem Skript `tests/sast/run-sonar-scan.ps1`. Details stehen in
`tests/sast/README.md`.

- Der Scan läuft **nach** dem UAT- und Freigabeschritt, nicht davor. Vor der
  Freigabe würde er Code melden, der noch geändert wird.
- Vor dem Scan müssen alle Tests grün sein; das Skript erzeugt die Coverage
  selbst.
- Ziel ist ein bestandenes Quality Gate mit 0 offenen Issues und 0 Duplikaten.
  Findings werden im Code behoben, nicht durch Regel-Deaktivierung verdeckt.
- Der Token steht ausschließlich in `.env` (gitignoriert) oder wird als
  `-Token` übergeben. Ein global gesetztes `SONAR_TOKEN` überschreibt `.env`
  nicht.
- Berichte liegen unter `tests/sast/reports/` und werden nicht versioniert.

## Akzeptanzkriterien

- Es wird ausschließlich der vereinbarte Ticketumfang geändert.
- Relevante Prüfungen sind erfolgreich; nicht ausführbare Prüfungen werden
  samt Grund genannt.
- Home-Assistant- und Serveränderungen sind nachvollziehbar und erfolgen nur
  mit Freigabe.
- Keine Secrets, privaten Nachrichteninhalte oder unnötigen personenbezogenen
  Daten werden offengelegt oder dauerhaft protokolliert.
- Backlog, Archiv und direkt betroffene Dokumentation sind konsistent.
