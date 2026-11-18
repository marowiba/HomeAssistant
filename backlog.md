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
| HAD-0009 | Signal-Integration | Medium | Registrierungspin für das Signal-Konto einrichten | Einen Registrierungspin (Registration Lock) für das dedizierte Signal-Konto aktivieren, damit die Nummer nicht ohne PIN erneut registriert und das Konto nicht übernommen werden kann. Vorab prüfen, ob die eingesetzte `signal-cli`-Version das Verfahren unterstützt; andernfalls den Befund dokumentieren und Alternativen bewerten. Den PIN ausschließlich in einem geschützten Speicher auf `srv001` ablegen, nicht im Repository, nicht in Logs und nicht in Nachrichten. Verfahren für eine Neuregistrierung und für den Verlust des PIN festlegen; bei Verlust ist die Nummer als kompromittiert zu behandeln. Setzt HAD-0001 voraus. | OPEN |
| HAD-0010 | Signal-Administration | High | Eigene Kommandos in der Weboberfläche anlegen und verwalten | Authentifizierten Administratoren erlauben, eigene, fest definierte Signal-Kommandos in der Weboberfläche anzulegen, zu bearbeiten, zu deaktivieren und zu löschen. Ein Kommando besteht aus dem Signal-Text (z. B. `HO S an`), einer Aktion (`on`, `off`, `status`) und einer Home-Assistant-Entität (`entity_id`). Keine frei ausführbaren Home-Assistant-Dienste, Skripte oder Templates zulassen; die Aktion ist auf `switch.turn_on`, `switch.turn_off` und Statuslesen beschränkt. Kommandotexte werden normalisiert und müssen eindeutig sein. Die Bridge wertet die konfigurierten Kommandos aus und führt die Aktion über die Home-Assistant-REST-API mit dem dedizierten Nicht-Admin-Token aus. Das UI validiert Text, Aktion und Entitäts-ID, protokolliert Änderungen im Audit-Log und zeigt die Kommandos in der Kommando-Ansicht. Bestehende `HO M`-Kommandos werden als Standard übernommen. Setzt HAD-0008 voraus. | OPEN |

## 🔴 ON HOLD

| ID | Feature | Prio | Name | Beschreibung | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |

## 🟡 Ideen

- Weitere Home-Assistant-Entitäten über eigene, fest definierte Signal-Kommandos
  integrieren.
