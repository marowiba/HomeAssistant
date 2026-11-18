# Benutzerhandbuch: Signal-Administration

## Zweck

Die Signal-Administration ist die Weboberfläche zur Verwaltung der
Signal-Integration auf `srv001`. Sie ist ausschließlich im lokalen Netzwerk
erreichbar.

## Aufruf

- Direkt: `http://srv001:8090/`
- Optional mit hosts-Eintrag: `http://signal-admin.srv001/`

## Anmeldung

- **Benutzername:** `admin`
- **Passwort:** das beim Anlegen des Kontos gesetzte Passwort.

Nach der Anmeldung steht die Seitenleiste mit Dashboard, Allowlist, Kommandos,
Ereignislog, Audit-Log, Status und Einstellungen zur Verfügung. Abmelden über
den Knopf oben rechts.

## Dashboard

- Kennzahlen: Allowlist-Einträge, Ereignisse, blockierte Nachrichten,
  Aufbewahrung in Tagen.
- Verbindungen: `signal-bridge`, `signal-cli`, Home Assistant.
- Letzte Ereignisse.

## Allowlist

- **Neuen Eintrag anlegen:** Bezeichnung, Nummer (`+49...`) und/oder UUID,
  „aktiv“ setzen, „Hinzufügen“.
- **Eintrag bearbeiten:** Felder ändern, „Speichern“.
- **Eintrag löschen:** „Löschen“ und bestätigen.

Nur aktive Einträge dürfen Kommandos auslösen. Ein Eintrag braucht mindestens
Nummer oder UUID.

## Kommandos

- Feste Kommandos: `HO M an`, `HO M aus`, `HO M Status`, `Hilfe` und `?`.
- `Hilfe` oder `?` sendet eine Übersicht der unterstützten Kommandos.
- Ein-/Ausschalten über „Deaktivieren“ bzw. „Aktivieren“.
- Es lassen sich keine weiteren Kommandos oder Home-Assistant-Dienste anlegen.
- Nach dem Ändern die Bridge neu starten:
  `sudo systemctl restart signal-bridge.service`.

## Ereignislog

- **Suche** nach Text, Absender, Kommando.
- **Filter:** Entscheidung (erlaubt/blockiert), Kommando, Zeitraum.
- **Details** zeigt alle Felder eines Ereignisses.
- **Löschen:** Häkchen setzen, „Ausgewählte löschen“, bestätigen. Jede Löschung
  wird im Audit-Log protokolliert.

## Audit-Log

- Zeigt Anmeldungen, Allowlist-Änderungen, Kommando-Änderungen, Löschungen,
  Retention und Restore.
- Die Hash-Kette zeigt, ob das Log unversehrt ist. „Kette gebrochen“ bedeutet
  eine nachträgliche Manipulation.

## Status

- Verbindungsstatus von `signal-bridge`, `signal-cli` und Home Assistant.
- Letzte Verarbeitungsfehler (Aktion oder Antwort fehlgeschlagen).

## Einstellungen

- **Aufbewahrung:** Anzahl Tage, „Speichern“.
- **Bereinigung jetzt ausführen:** entfernt ältere Ereignisse sofort.
- **Sicherung:** „Konfiguration herunterladen“ (JSON).
- **Wiederherstellung:** Backup-JSON einfügen, „Wiederherstellen“.

## Sicherheit

- Die Sitzung endet nach 8 Stunden oder beim Abmelden.
- Schreibende Aktionen sind CSRF-geschützt.
- Nach mehreren Fehlanmeldungen wird die Anmeldung kurz gesperrt.
- Keine Passwörter oder Tokens in Berichten.

## Problembehebung

| Problem | Maßnahme |
| :--- | :--- |
| „Seite nicht erreichbar“ | `systemctl status signal-admin.service` prüfen |
| Anmeldung schlägt fehl | Benutzer `admin` und Passwort prüfen; ggf. Passwort neu setzen (siehe `deploy/signal-admin/README.md`) |
| Kommando-Änderung wirkt nicht | `sudo systemctl restart signal-bridge.service` |
| Status „Fehler“ | Verbindung zu `signal-cli` bzw. Home Assistant prüfen |
