# Backlog - Home Assistant Developments (HAD)

`Feature` dient als Epic und gruppiert zusammengehörige Tickets. Ticket-IDs
verwenden das Präfix `HAD-` gefolgt von einer fortlaufenden vierstelligen
Nummer. Neue Tickets erhalten den nächsten freien Wert. Erledigte Tickets
werden nach `backlog_done.md` verschoben.

## 🟡 IN PROGRESS

| ID | Feature | Prio | Name | Beschreibung | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |

## 🔵 OPEN

| ID | Feature | Prio | Name | Beschreibung | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| HAD-0001 | Signal-Integration | High | Signal-Empfang auf srv001 bereitstellen | `signal-cli` als dauerhaft laufenden Dienst auf dem Ubuntu-Server `srv001` einrichten und mit einem dedizierten Signal-Konto verknüpfen. Eingehende Nachrichten sollen ereignisbasiert empfangen werden; der Dienst muss nach Neustarts automatisch starten. Es werden nur ausgehende Verbindungen zu Signal benötigt; srv001 erhält keine Internet-Portfreigabe. Kontodaten und Schlüssel sind persistent und zugriffsgeschützt abzulegen. | OPEN |
| HAD-0002 | Signal-Integration | High | Absenderfreigabe und Chat-Log umsetzen | Eine explizite Absender-Allowlist für ausführbare Kommandos einführen. Nachrichten aller nicht freigegebenen Absender mit Absender und Empfangszeit lokal protokollieren, aber weder als Kommandos auswerten noch an Home Assistant weiterleiten. Das Log nur Administratoren zugänglich machen und Aufbewahrung sowie Löschung festlegen. | OPEN |
| HAD-0003 | Signal-Integration | High | Home-Office-Kommandos erkennen | Ausschließlich `HO M an`, `HO M aus` und `HO M Status` als Kommandos akzeptieren. Die Auswertung muss unabhängig von Groß- und Kleinschreibung sein; unbekannte oder mehrdeutige Nachrichten dürfen keine Aktion auslösen. | OPEN |
| HAD-0004 | Signal-Integration | High | Home-Assistant-Steuerung und Statusabfrage anbinden | `HO M an` und `HO M aus` sollen den Switch `switch.haustechnik_shc41ccf4_matthias_im_home_office` gezielt ein- bzw. ausschalten. `HO M Status` soll dessen aktuellen Zustand sicher und ausschließlich über das Heimnetz abfragen. Die vorhandenen Home-Assistant-Automationen sollen durch Zustandsänderungen weiterhin die Solltemperatur setzen. Den Status-Leseweg so gestalten, dass kein unnötig breit berechtigter API-Zugang entsteht. | OPEN |
| HAD-0005 | Signal-Integration | Medium | Signal-Antworten und Fehlerverhalten ergänzen | Nach erfolgreichen Schaltbefehlen und Statusabfragen eine verständliche Signal-Antwort senden. Bei unbekanntem/unverfügbarem Schalterzustand, nicht erreichbarem Home Assistant oder fehlgeschlagener Aktion ausdrücklich einen Fehler melden und keine erfolgreiche Ausführung vortäuschen. Wiederholte An-/Aus-Kommandos müssen idempotent bleiben. | OPEN |
| HAD-0006 | Signal-Integration | High | Signal-Integration absichern und abnehmen | End-to-End-Prüfungen für freigegebene und nicht freigegebene Absender, alle drei Kommandos, unterschiedliche Schreibweisen, ungültige Nachrichten, unbekannten Switch-Zustand und Verbindungsfehler ergänzen. Verifizieren, dass keine eingehenden Internetverbindungen oder Portfreigaben zu srv001 nötig sind und Nachrichten nicht freigegebener Absender keine Home-Assistant-Aktion auslösen. | OPEN |

## 🔴 ON HOLD

| ID | Feature | Prio | Name | Beschreibung | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |

## 🟡 Ideen

- Weitere Home-Assistant-Entitäten über eigene, fest definierte Signal-Kommandos
  integrieren.
- Eine Signal-Hilfe-Nachricht mit den unterstützten Kommandos ergänzen.
