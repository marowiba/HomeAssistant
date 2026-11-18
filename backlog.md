# Backlog - Home Assistant Developments (HAD)

`Feature` dient als Epic und gruppiert zusammengehörige Tickets. Ticket-IDs
verwenden das Präfix `HAD-` gefolgt von einer fortlaufenden vierstelligen
Nummer. Neue Tickets erhalten den nächsten freien Wert. Erledigte Tickets
werden nach `backlog_done.md` verschoben und chronologisch absteigend (neuste oben) gemäß ihrem letzten GitHub Zeitstempel einsortiert.

## 🟡 IN PROGRESS

| ID | Feature | Prio | Name | Beschreibung | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |

## 🔵 OPEN

| ID | Feature | Prio | Name | Beschreibung | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| HAD-0020 | Signal-Administration | Low | Ereignislog: Sammelauswahl über eine Checkbox in der Kopfzeile | In der Ereignisliste unter `/events` erhält die erste Spalte in der Kopfzeile eine Checkbox. Ein Klick aktiviert alle Zeilen-Checkboxen der aktuellen Seite, ein weiterer Klick deaktiviert sie. Die Kopfzeilen-Checkbox ist reines Bedienelement und darf nicht mit dem Löschformular übertragen werden. Umsetzung ohne Inline-JavaScript, weil die CSP `script-src 'self'` Inline-Handler blockiert: eine statische Datei `signal_admin/static/admin.js` einbinden, die über die Attribute `data-select-all` und `data-row-select` arbeitet. Die Auswahl gilt nur für die sichtbaren Zeilen der aktuellen Seite. Tests für die gerenderten Attribute und für die statische Datei ergänzen. | OPEN |

## 🔴 ON HOLD

| ID | Feature | Prio | Name | Beschreibung | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |

## 🟡 Ideen

- Weitere Home-Assistant-Entitäten über eigene, fest definierte Signal-Kommandos
  integrieren.
