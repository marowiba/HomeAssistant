# HAD-0024: Home-Assistant-Status korrekt prüfen

## Ziel

Dashboard und Statusseite melden für Home Assistant wieder einen verwertbaren
Zustand. Die Prüfung fragt die API und nicht die Startseite ab.

## Ausgangslage

- `status.check_home_assistant` erwartete ein Zustandsobjekt mit `state` und
  bekam seit HAD-0010 die `base_url` aus der Konfiguration.
- Ein Aufruf von `base_url` liefert die HTML-Startseite von Home Assistant.
  Das JSON-Parsing scheitert, die Oberfläche meldet
  „Antwort ist kein gültiges JSON“.
- Der Token wurde zwar gesendet, aber nicht geprüft, weil die Startseite ihn
  nicht auswertet.

## Umsetzung

### S1: Prüfung über die API

- `check_home_assistant(base_url, token, timeout)` baut die URL
  `base_url.rstrip("/") + "/api/"`.
- Der Request sendet `Authorization: Bearer <token>`.
- Erwartet wird JSON mit `{"message": "API running."}`.
- Fehlerbilder:
  - fehlende `base_url` oder fehlender `token` → `nicht konfiguriert`
  - HTTP-Fehler → `HTTP <code>`
  - Netzwerkfehler, Zeitüberschreitung → wie bisher
  - HTML oder anderer Nicht-JSON-Inhalt → `Antwort ist kein gültiges JSON`
  - JSON, aber kein Objekt → `Antwort ist kein Objekt`
  - Objekt ohne erwartete Meldung → `unerwartete Antwort`
- Erfolg meldet `erreichbar`.

### S2: Aufruf in der Anwendung

- `AdminApp._statuses` übergibt `base_url` und `token` aus
  `home_assistant`, sofern die Konstruktor-Parameter `ha_status_url` und
  `ha_status_token` nicht gesetzt sind.
- Fehlertexte enthalten weiterhin weder URL noch Token.

## Entscheidungen

- **E1:** `/api/` statt `/api/states`. Der Endpunkt ist dokumentiert, liefert
  eine feste Meldung und prüft den Token in einem Schritt.
- **E2:** Die Meldung wird exakt verglichen. Ein HTML-Fehlerblatt mit Status
  200 wird damit sicher erkannt.
- **E3:** Die Signatur heißt `base_url`, weil keine Zustands-URL mehr
  erwartet wird. Bestehende `status_url`-Konfigurationen migriert
  `config_store.migrate_config` bereits auf `base_url`.

## Verifikation

- Erfolg mit `{"message": "API running."}` meldet `erreichbar`.
- Die Anfrage geht an `<base_url>/api/` und trägt den Bearer-Token.
- HTML-Antwort meldet `Antwort ist kein gültiges JSON`.
- HTTP 401 meldet `HTTP 401`.
- Fehlende Konfiguration meldet `nicht konfiguriert`.
- `_statuses` reicht `base_url` und `token` aus der Konfiguration durch.
- 248 Tests grün, 100 % Zeilenabdeckung in `signal-admin/signal_admin`.
