# Epic: Signal-Administration

## Ziel

Eine reine Server-Webanwendung auf `srv001` unter `http://signal-admin.srv001`,
über die authentifizierte Administratoren die Signal-Integration verwalten:
Allowlist, feste Kommandos, Ereignislog, Audit-Log, Status und Einstellungen.
Erreichbar nur per Browser im lokalen Netzwerk; keine Desktop-Installation,
keine Internetveröffentlichung, keine eingehende Portfreigabe.

## Architektur

- Python-3-Standardbibliothek (`http.server`, `sqlite3`, `hmac`, `hashlib`,
  `secrets`), keine externen Laufzeitabhängigkeiten.
- SQLite-Datenbank für Benutzer, Sitzungen, Audit-Log und Einstellungen.
- Liest und schreibt die Bridge-Konfiguration (`config.json`) und das
  Ereignislog (`messages.jsonl`).
- Bindet an `127.0.0.1:8090`; nginx (Port 80) leitet `signal-admin.srv001`
  als Reverse-Proxy dorthin weiter.
- Läuft als Benutzer `signal-cli`, damit Konfiguration und Ereignislog
  gelesen und geschrieben werden können.
- Look & Feel an GnuCashReporting (GRC) orientiert: Slate/Emerald, Sidebar,
  Karten, klare Tabellen.

## Sicherheit

- Anmeldung mit PBKDF2-HMAC-SHA256, Sitzungs-Cookies (HttpOnly,
  SameSite=Strict), CSRF-Schutz für schreibende Anfragen, Login-Rate-Limit.
- Eingaben validieren, Ausgaben HTML-escaped.
- Keine Secrets in Logs oder Antworten.
- Audit-Log append-only mit Hash-Kette (manipulationserkennbar).

## Abgrenzung

- Keine frei ausführbaren Home-Assistant-Dienste oder Templates.
- Werte-Kommandos (`set_value`) sind auf die Domains `climate`, `number` und
  `input_number` mit fest zugeordnetem Dienst beschränkt.
- Keine Mehrmandanten, kein Internet-Betrieb, kein Desktop-Client.
- Kein Ersatz für die Signal-Bridge; die Bridge bleibt der Empfangsdienst.

## Qualitätsziel

- 0 offene Sonar-Issues, 0 Duplikate, 100 % Zeilenabdeckung der Quelldateien.
