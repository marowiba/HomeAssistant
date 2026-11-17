# HAD-0008: Geschützte Webanwendung zur Signal-Administration

## Ziel

Eine reine Server-Webanwendung auf `srv001`, die authentifizierten
Administratoren die Verwaltung der Signal-Integration erlaubt. Keine
Desktop-Installation, keine Internetveröffentlichung, keine eingehende
Portfreigabe.

## Ausgangslage

- Signal-Bridge (`signal-bridge/bridge.py`) schreibt das Ereignislog als
  JSON-Lines und liest die Konfiguration als JSON.
- `signal-cli` läuft als systemd-Dienst und bietet JSON-RPC unter
  `http://127.0.0.1:8080`.
- Home Assistant ist über Webhooks (Schalten) und REST (Status) angebunden.
- Referenz für Look & Feel: GnuCashReporting (GRC), FastAPI/Jinja2/HTMX.

## Entscheidungen

- **E1:** Python-Standardbibliothek statt FastAPI. Das Projekt ist bewusst
  abhängigkeitsfrei; Deployment bleibt ein einzelner systemd-Dienst ohne venv.
- **E2:** SQLite für Benutzer, Sitzungen, Audit und Einstellungen.
- **E3:** Die Bridge-Konfiguration bleibt die einzige Quelle für Allowlist,
  Kommandos und Retention. Die Web-App schreibt sie atomar und validiert vorher.
- **E4:** Das Ereignislog bleibt JSON-Lines. Löschen schreibt die Datei atomar
  neu und protokolliert jede Löschung im Audit-Log.
- **E5:** Audit-Log append-only mit Hash-Kette; jede Zeile enthält
  `prev_hash` und `entry_hash`.
- **E6:** Feste Kommandos (`HO M an`, `HO M aus`, `HO M Status`) sind eine
  geschlossene Liste. Die App kann sie nur ein-/ausschalten, nicht ersetzen.
- **E7:** Bindung an `127.0.0.1:8090`; nginx auf Port 80 leitet
  `signal-admin.srv001` als Reverse-Proxy weiter.
- **E8:** Der Dienst läuft als Benutzer `signal-cli`, damit er die
  Bridge-Konfiguration und das Ereignislog lesen und schreiben kann.

## Module

| Modul | Aufgabe |
| :--- | :--- |
| `signal_admin/store.py` | SQLite-Schema und Zugriffe (Benutzer, Sitzungen, Audit, Einstellungen) |
| `signal_admin/auth.py` | PBKDF2-Passwörter, Sitzungs-Token, CSRF, Login-Rate-Limit |
| `signal_admin/config_store.py` | Bridge-Konfiguration lesen, validieren, atomar schreiben, Backup/Restore |
| `signal_admin/events.py` | Ereignislog lesen, filtern, Detail, Löschen |
| `signal_admin/audit.py` | Hash-Kette fortschreiben und prüfen |
| `signal_admin/status.py` | Dienst-, Signal- und Home-Assistant-Status, letzte Fehler |
| `signal_admin/templates.py` | HTML-Rendering (GRC-Look) |
| `signal_admin/app.py` | HTTP-Server, Routing, Sicherheitsheader |

## Routen

| Methode | Pfad | Zweck |
| :--- | :--- | :--- |
| GET | `/` | Weiterleitung auf `/dashboard` |
| GET/POST | `/login` | Anmeldung |
| POST | `/logout` | Abmeldung |
| GET | `/dashboard` | Übersicht, Status, letzte Ereignisse |
| GET | `/allowlist` | Allowlist anzeigen |
| POST | `/allowlist/add`, `/allowlist/update`, `/allowlist/delete` | Allowlist ändern |
| GET | `/commands` | Feste Kommandos anzeigen |
| POST | `/commands/toggle` | Kommando ein-/ausschalten |
| GET | `/events` | Ereignislog mit Suche/Filter/Pagination |
| GET | `/events/detail` | Detailansicht eines Ereignisses |
| POST | `/events/delete` | Ausgewählte Ereignisse löschen |
| GET | `/audit` | Audit-Log mit Kettenprüfung |
| GET | `/status` | Verbindungsstatus und letzte Fehler |
| GET | `/settings` | Retention und Backup/Restore |
| POST | `/settings/retention`, `/settings/cleanup` | Retention ändern, Bereinigung ausführen |
| GET | `/backup` | Konfiguration als JSON herunterladen |
| POST | `/restore` | Konfiguration wiederherstellen |
| GET | `/static/<datei>` | CSS/JS |

## Sicherheit

- Alle Routen außer `/login` und `/static` erfordern eine gültige Sitzung.
- Alle POST-Routen erfordern ein gültiges CSRF-Token.
- Sitzungs-Cookies: `HttpOnly`, `SameSite=Strict`, `Path=/`.
- Login-Rate-Limit pro Client-Adresse.
- Sicherheitsheader: `Content-Security-Policy`, `X-Frame-Options`,
  `X-Content-Type-Options`, `Referrer-Policy`.
- Eingaben werden validiert, Ausgaben HTML-escaped.

## Verifikation

- 329 Tests grün (145 Bridge, 184 Administration).
- 100 % Zeilenabdeckung der Quelldateien (1668 Zeilen).
- SonarQube: 0 Issues, 0 Duplikate, Quality Gate OK.
- Der Scan umfasst `signal-bridge` und `signal-admin`.
