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
| HAD-0003 | Signal-Integration | High | Home-Office-Kommandos erkennen | Ausschließlich `HO M an`, `HO M aus` und `HO M Status` als Kommandos akzeptieren. Die Auswertung muss unabhängig von Groß- und Kleinschreibung sein; unbekannte oder mehrdeutige Nachrichten dürfen keine Aktion auslösen. | OPEN |
| HAD-0004 | Signal-Integration | High | Home-Assistant-Steuerung und Statusabfrage anbinden | `HO M an` und `HO M aus` sollen den Switch `switch.haustechnik_shc41ccf4_matthias_im_home_office` gezielt ein- bzw. ausschalten. `HO M Status` soll dessen aktuellen Zustand sicher und ausschließlich über das Heimnetz abfragen. Die vorhandenen Home-Assistant-Automationen sollen durch Zustandsänderungen weiterhin die Solltemperatur setzen. Den Status-Leseweg so gestalten, dass kein unnötig breit berechtigter API-Zugang entsteht. | OPEN |
| HAD-0005 | Signal-Integration | Medium | Signal-Antworten und Fehlerverhalten ergänzen | Nach erfolgreichen Schaltbefehlen und Statusabfragen eine verständliche Signal-Antwort senden. Bei unbekanntem/unverfügbarem Schalterzustand, nicht erreichbarem Home Assistant oder fehlgeschlagener Aktion ausdrücklich einen Fehler melden und keine erfolgreiche Ausführung vortäuschen. Wiederholte An-/Aus-Kommandos müssen idempotent bleiben. | OPEN |
| HAD-0006 | Signal-Integration | High | Signal-Integration absichern und abnehmen | End-to-End-Prüfungen für freigegebene und nicht freigegebene Absender, alle drei Kommandos, unterschiedliche Schreibweisen, ungültige Nachrichten, unbekannten Switch-Zustand und Verbindungsfehler ergänzen. Verifizieren, dass keine eingehenden Internetverbindungen oder Portfreigaben zu srv001 nötig sind und Nachrichten nicht freigegebener Absender keine Home-Assistant-Aktion auslösen. | OPEN |
| HAD-0007 | Codequalität und SAST | Medium | SonarQube anbinden, SAST-Reporting und sauberen Initialscan einrichten | SonarQube-Projekt und Entwicklungsumgebung sicher anbinden; keine Tokens oder Zugangsdaten committen. Das Scan- und Reporting-Verfahren nach dem Vorbild von `GnuCashReporting/tests/dast` projektspezifisch neu erstellen, aber im Verzeichnis `tests/sast` (SAST statt DAST). Summary- und Detailberichte lokal unter `tests/sast/reports/` ablegen und diesen Ordner von Git ausschließen. Einen initialen Scan ausführen, alle Findings beheben und einen verifizierten Scan mit 0 Issues sowie bestandenem Quality Gate dokumentieren. Danach diesen `DEV Prompt.md` um den freigegebenen SAST-Ablauf ergänzen; Scan erst nach dem dort festgelegten UAT-/Freigabeschritt ausführen. | OPEN |
| HAD-0008 | Signal-Administration | High | Geschützte Webanwendung zur Verwaltung der Signal-Integration erstellen | Eine reine Server-Webanwendung auf `srv001` bereitstellen, die ausschließlich über einen Browser im lokalen Netzwerk erreichbar ist; keine Desktop-/Client-Installation, Internetveröffentlichung oder eingehende Portfreigabe. Look & Feel sowie UI/UX an der GnuCashReporting-Anwendung (GRC) orientieren. Authentifizierten Administratoren erlauben, Sender-Allowlist und deren Berechtigungen sowie die unterstützten, fest definierten Kommandos zu verwalten; keine frei ausführbaren Home-Assistant-Dienste oder Templates zulassen. Einen durchsuch- und filterbaren Chat-/Ereignislog mit Detailansicht und bestätigtem Löschen ausgewählter Einträge anbieten. Löschungen und Konfigurationsänderungen separat und manipulationsgeschützt protokollieren; Aufbewahrung und automatische Bereinigung konfigurierbar machen. Zusätzlich Dienst-/Signal-/Home-Assistant-Verbindungsstatus, letzte Empfangs- und Verarbeitungsfehler, Konfigurationsvalidierung sowie geschützte Sicherung und Wiederherstellung der Einstellungen anbieten. Zugriff, Sitzungen, Eingaben und Ausgaben gegen unberechtigte Nutzung schützen. | OPEN |
| HAD-0009 | Signal-Integration | Medium | Registrierungspin für das Signal-Konto einrichten | Einen Registrierungspin (Registration Lock) für das dedizierte Signal-Konto aktivieren, damit die Nummer nicht ohne PIN erneut registriert und das Konto nicht übernommen werden kann. Vorab prüfen, ob die eingesetzte `signal-cli`-Version das Verfahren unterstützt; andernfalls den Befund dokumentieren und Alternativen bewerten. Den PIN ausschließlich in einem geschützten Speicher auf `srv001` ablegen, nicht im Repository, nicht in Logs und nicht in Nachrichten. Verfahren für eine Neuregistrierung und für den Verlust des PIN festlegen; bei Verlust ist die Nummer als kompromittiert zu behandeln. Setzt HAD-0001 voraus. | OPEN |

## 🔴 ON HOLD

| ID | Feature | Prio | Name | Beschreibung | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |

## 🟡 Ideen

- Weitere Home-Assistant-Entitäten über eigene, fest definierte Signal-Kommandos
  integrieren.
- Eine Signal-Hilfe-Nachricht mit den unterstützten Kommandos ergänzen.
