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

- Die Tabelle zeigt alle Kommandos mit Text, Aktion, Entität, Bereich und
  Status.
- **Neues Kommando anlegen:** Signal-Text, Aktion, Entität, optional `min`,
  `max` und Einheit, „Hinzufügen“.
- **Bearbeiten:** Felder in der Zeile ändern, „Speichern“.
- **Löschen:** „Löschen“ und bestätigen.
- **Aktivieren/Deaktivieren:** Häkchen „aktiv“ in der Zeile.
- Aktionen: `on`, `off`, `status`, `set_value`, `help`.
- Werte-Kommandos brauchen den Platzhalter `{wert}` am Ende, z. B.
  `HO T {wert}`. Erlaubt sind `climate`, `number` und `input_number`.
- `on` und `off` sind nur für `switch`-Entitäten erlaubt.
- `Hilfe` oder `?` sendet eine Übersicht der aktiven Kommandos.
- Änderungen werden von der Bridge automatisch übernommen; ein Neustart ist
  nicht nötig.

## Ereignislog

- **Suche** nach Text, Absender, Kommando.
- **Filter:** Entscheidung (erlaubt/blockiert), Kommando, Zeitraum.
- **Sortierung:** Klick auf einen Spaltenkopf sortiert aufsteigend, ein
  weiterer Klick absteigend. Standard ist Zeit absteigend, also der jüngste
  Eintrag oben. Der aktive Spaltenkopf zeigt die Richtung mit ▲ oder ▼.
- **Sammelauswahl:** Die Checkbox im Spaltenkopf der ersten Spalte wählt alle
  gefilterten Ereignisse aus, auch auf anderen Seiten. „Ausgewählte löschen“
  löscht dann alle gefilterten Einträge, nicht nur die sichtbare Seite.
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
| Kommando-Änderung wirkt nicht | Konfiguration prüfen: `sudo python3 /opt/signal-bridge/bridge.py --config /etc/signal-bridge/config.json --check-config` |
| Status „Fehler“ | Verbindung zu `signal-cli` bzw. Home Assistant prüfen |
