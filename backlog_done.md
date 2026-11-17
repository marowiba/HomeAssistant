# Backlog Archive (Erledigte Tasks) - Home Assistant Developments (HAD)

Erledigte Tickets aus `backlog.md` werden hier archiviert. Die Feature-Spalte
entspricht dem Epic, zu dem das Ticket gehört. Ticket-IDs behalten das Präfix
`HAD-` und werden nicht wiederverwendet.

## 🟢 Erledigt

| ID | Feature | Prio | Name | Beschreibung | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| HAD-0001 | Signal-Integration | High | Signal-Empfang auf srv001 bereitstellen | `signal-cli` als dauerhaft laufenden Dienst auf dem Ubuntu-Server `srv001` einrichten und mit einem dedizierten Signal-Konto verknüpfen. Eingehende Nachrichten sollen ereignisbasiert empfangen werden; der Dienst muss nach Neustarts automatisch starten. Es werden nur ausgehende Verbindungen zu Signal benötigt; srv001 erhält keine Internet-Portfreigabe. Kontodaten und Schlüssel sind persistent und zugriffsgeschützt abzulegen. | DONE |
| HAD-0002 | Signal-Integration | High | Absenderfreigabe und Chat-Log umsetzen | Eine explizite Absender-Allowlist für ausführbare Kommandos einführen. Nachrichten aller nicht freigegebenen Absender mit Absender und Empfangszeit lokal protokollieren, aber weder als Kommandos auswerten noch an Home Assistant weiterleiten. Das Log nur Administratoren zugänglich machen und Aufbewahrung sowie Löschung festlegen. | DONE |
