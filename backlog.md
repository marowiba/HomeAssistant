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
| HAD-0008 | Signal-Administration | High | Geschützte Webanwendung zur Verwaltung der Signal-Integration erstellen | Eine reine Server-Webanwendung auf `srv001` bereitstellen, die ausschließlich über einen Browser im lokalen Netzwerk erreichbar ist; keine Desktop-/Client-Installation, Internetveröffentlichung oder eingehende Portfreigabe. Look & Feel sowie UI/UX an der GnuCashReporting-Anwendung (GRC) orientieren. Authentifizierten Administratoren erlauben, Sender-Allowlist und deren Berechtigungen sowie die unterstützten, fest definierten Kommandos zu verwalten; keine frei ausführbaren Home-Assistant-Dienste oder Templates zulassen. Einen durchsuch- und filterbaren Chat-/Ereignislog mit Detailansicht und bestätigtem Löschen ausgewählter Einträge anbieten. Löschungen und Konfigurationsänderungen separat und manipulationsgeschützt protokollieren; Aufbewahrung und automatische Bereinigung konfigurierbar machen. Zusätzlich Dienst-/Signal-/Home-Assistant-Verbindungsstatus, letzte Empfangs- und Verarbeitungsfehler, Konfigurationsvalidierung sowie geschützte Sicherung und Wiederherstellung der Einstellungen anbieten. Zugriff, Sitzungen, Eingaben und Ausgaben gegen unberechtigte Nutzung schützen. | OPEN |
| HAD-0009 | Signal-Integration | Medium | Registrierungspin für das Signal-Konto einrichten | Einen Registrierungspin (Registration Lock) für das dedizierte Signal-Konto aktivieren, damit die Nummer nicht ohne PIN erneut registriert und das Konto nicht übernommen werden kann. Vorab prüfen, ob die eingesetzte `signal-cli`-Version das Verfahren unterstützt; andernfalls den Befund dokumentieren und Alternativen bewerten. Den PIN ausschließlich in einem geschützten Speicher auf `srv001` ablegen, nicht im Repository, nicht in Logs und nicht in Nachrichten. Verfahren für eine Neuregistrierung und für den Verlust des PIN festlegen; bei Verlust ist die Nummer als kompromittiert zu behandeln. Setzt HAD-0001 voraus. | OPEN |

## 🔴 ON HOLD

| ID | Feature | Prio | Name | Beschreibung | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |

## 🟡 Ideen

- Weitere Home-Assistant-Entitäten über eigene, fest definierte Signal-Kommandos
  integrieren.
- Eine Signal-Hilfe-Nachricht mit den unterstützten Kommandos ergänzen.
