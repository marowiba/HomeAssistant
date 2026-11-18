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
| HAD-0021 | Signal-Administration | Low | Event-Detail: Absender-Nummer nicht als UUID anzeigen | In der Ereignis-Detailansicht steht im Feld `Absender-Nummer` eine UUID, wenn der Absender die Nummernweitergabe abgeschaltet hat; Signal liefert dann die UUID in `sourceNumber`. Das Feld soll `-` anzeigen, wenn der Wert wie eine UUID aussieht, und die UUID nur im Feld `Absender-UUID` führen. Die Erkennung erfolgt über ein UUID-Muster, die gespeicherten Daten bleiben unverändert. Tests für die Anzeige mit Nummer, mit UUID und ohne beides ergänzen. | OPEN |
| HAD-0022 | Signal-Administration | Low | UI-Texte mit korrekten deutschen Umlauten | Die Weboberfläche verwendet durchgängig transliterierte Umlaute (`ae`, `ue`, `oe`, `ss`), etwa „zulaessig“, „loeschen“, „Eintraege“, „waehlen“. Alle sichtbaren Texte in `signal-admin/signal_admin/templates.py` und die Meldungen in `app.py` sollen die korrekte deutsche Rechtschreibung mit `ä`, `ö`, `ü` und `ß` verwenden. Technische Bezeichner, Dateinamen, URLs und Attributwerte bleiben unverändert. Tests, die auf transliterierte Texte prüfen, werden angepasst. Die Dokumentation kann in einem Folgeschritt nachgezogen werden. | OPEN |
| HAD-0023 | Signal-Administration | Medium | Responsive Oberfläche für mobile Geräte | Die Weboberfläche ist für den Desktop ausgelegt; auf Smartphones und Tablets sind Sidebar, Tabellen und Formulare schlecht bedienbar. Die Oberfläche soll sich an die Bildschirmbreite anpassen: Sidebar als einklappbares Menü, Tabellen horizontal scrollbar oder als Karten, Formulare einspaltig, ausreichend große Schaltflächen. Umsetzung mit CSS in `signal_admin/static/admin.css`, ohne externe Frameworks. Tests für die gerenderten Viewport- und Menü-Attribute ergänzen. | OPEN |
| HAD-0024 | Signal-Administration | High | Defekt: Dashboard und Status melden für Home Assistant „Antwort ist kein gueltiges JSON“ | Seit HAD-0010 übergibt `_statuses` in `app.py` die `base_url` an `status.check_home_assistant`. Diese Funktion erwartet ein Zustandsobjekt mit `state`, bekommt aber die HTML-Startseite von Home Assistant und meldet „Antwort ist kein gueltiges JSON“. Behoben wird der Fehler, indem die Prüfung `base_url + "/api/"` mit dem Token aufruft und die JSON-Antwort `{"message": "API running."}` auswertet. Alternativ `base_url + "/api/states"` und eine Liste prüfen. Fehlertexte bleiben ohne URL und Token. Tests für Erfolg, HTTP 401, HTML-Antwort und fehlende Konfiguration ergänzen. | OPEN |
| HAD-0025 | Signal-Administration | Low | Einstellungen: Schaltflächen einheitlich anordnen und dimensionieren | Unter `/settings` stehen „Speichern“ und „Wiederherstellen“ in eigenen Formularen, während „Bereinigung jetzt ausführen“ und „Konfiguration herunterladen“ anders aussehen und an anderer Stelle stehen. Die vier Schaltflächen sollen in identischer Größe und Ausrichtung erscheinen, je Aktion in ihrer logischen Gruppe. Reine Layout-Änderung in `templates.py` und `admin.css`, keine Änderung am Verhalten. Tests für die gerenderten Klassen ergänzen. | OPEN |
| HAD-0026 | Signal-Administration | Low | Audit-Log: Spalten sortierbar und Inhalt verständlich | Die Spaltenköpfe des Audit-Logs sind nicht sortierbar. Zusätzlich sind „Kette unversehrt“ und die Einträge selbst für Anwender schwer zu deuten. Die Spalten ID, Zeit, Akteur, Aktion, Ziel, Detail und Hash sollen wie im Event-Log über `sort` und `dir` sortierbar werden, Standard Zeit absteigend. Der Integritätsstatus erhält einen erklärenden Satz, etwa „Die Einträge sind unverändert; die Prüfkette ist vollständig.“ Aktionen werden mit verständlichen Bezeichnungen angezeigt, etwa `allowlist.add` als „Allowlist-Eintrag angelegt“. Eine kurze Legende erklärt Hash und Prüfkette. Tests für Sortierung, Standardreihenfolge und die neuen Texte ergänzen. | OPEN |
| HAD-0027 | Signal-Administration | Low | Umbenennung: Allow List, Audit Log, Event Log | Die Navigation und die Seitenüberschriften verwenden „Allowlist“, „Audit-Log“ und „Ereignislog“. Sie sollen einheitlich „Allow List“, „Audit Log“ und „Event Log“ heißen. Betroffen sind die Navigation, die Seitentitel, die Überschriften und die Verweise in `templates.py` sowie die Texte im Benutzerhandbuch. URLs, Routen, CSS-Klassen und technische Bezeichner bleiben unverändert. Tests, die auf die alten Bezeichnungen prüfen, werden angepasst. | OPEN |
| HAD-0028 | Signal-Administration | Low | Kommandos nach Kommando und Entität sortierbar | Die Kommando-Ansicht unter `/commands` listet die Kommandos in Konfigurationsreihenfolge. Die Spalten „Kommando“ und „Entität“ sollen auf- und absteigend sortierbar sein, über `sort` und `dir` mit weißer Liste, analog zum Event-Log. Standard ist die Konfigurationsreihenfolge. Der aktive Spaltenkopf zeigt die Richtung an. Tests für beide Spalten in beiden Richtungen und für ungültige Werte ergänzen. | OPEN |

## 🔴 ON HOLD

| ID | Feature | Prio | Name | Beschreibung | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |

## 🟡 Ideen

- Weitere Home-Assistant-Entitäten über eigene, fest definierte Signal-Kommandos
  integrieren.
