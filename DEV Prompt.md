# Dev Prompt - Home Assistant Developments

## Aktuelles Ticket

Das aktive Ticket wird in `backlog.md` unter `## 🟡 IN PROGRESS` geführt.
Ticket-ID und Beschreibung sind vor Arbeitsbeginn zu prüfen; der Umfang des
Tickets ist verbindlich.

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

## Akzeptanzkriterien

- Es wird ausschließlich der vereinbarte Ticketumfang geändert.
- Relevante Prüfungen sind erfolgreich; nicht ausführbare Prüfungen werden
  samt Grund genannt.
- Home-Assistant- und Serveränderungen sind nachvollziehbar und erfolgen nur
  mit Freigabe.
- Keine Secrets, privaten Nachrichteninhalte oder unnötigen personenbezogenen
  Daten werden offengelegt oder dauerhaft protokolliert.
- Backlog, Archiv und direkt betroffene Dokumentation sind konsistent.
