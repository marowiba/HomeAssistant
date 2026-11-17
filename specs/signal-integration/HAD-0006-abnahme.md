# Solution Design: HAD-0006 – Signal-Integration absichern und abnehmen

## Metadaten

| Feld | Wert |
| :--- | :--- |
| Ticket | HAD-0006 (siehe `backlog.md`) |
| Feature / Epic | Signal-Integration |
| Priorität | High |
| Übergreifendes Design | `specs/signal-integration/design.md` |
| Vorgänger | HAD-0001 bis HAD-0005 |
| Dokumenttyp | Abnahmedokument |
| Status | in Arbeit |

## Ziel

Die gesamte Kette wird Ende-zu-Ende geprüft: vom Signal-Eingang über Allowlist
und Kommandoerkennung bis zur Home-Assistant-Aktion und zur Antwort. Zusätzlich
wird belegt, dass `srv001` keine eingehenden Verbindungen oder Portfreigaben
benötigt und dass Nachrichten nicht freigegebener Absender keine Aktion
auslösen.

## Teststrategie

Zwei Ebenen, weil die eine die andere nicht ersetzt:

| Ebene | Was sie prüft | Wo |
| :--- | :--- | :--- |
| Integrationstest | Kette mit echtem Code, aber simuliertem Signal und Home Assistant | `signal-bridge/tests/test_integration.py` |
| Manuelle Abnahme | echter Signal-Weg, echter Daemon, echtes Home Assistant | `srv001` |

Der Integrationstest läuft bei jeder Änderung mit und ist reproduzierbar. Die
manuelle Abnahme belegt, dass die Annahmen über die echten Systeme stimmen.

## Integrationstest

`FakeHomeAssistant` beantwortet vier Rollen in einem lokalen HTTP-Server:

| Pfad | Rolle |
| :--- | :--- |
| `GET /api/v1/events` | Ereignisstrom mit vier vorbereiteten Nachrichten |
| `POST /api/webhook/on`, `.../off` | Schaltbefehle, Antwort 200 |
| `GET /api/states/...` | Statusabfrage, Antwort `{"state": "on"}` |
| `POST /api/v1/rpc` | Antwortversand, Antwort `SUCCESS` |

Die vier Ereignisse:

| Nr. | Absender | Text | Erwartung |
| :--- | :--- | :--- | :--- |
| 1 | freigegeben | `HO M an` | `allowed`, `command: on`, Aktion ok, Antwort ok |
| 2 | freigegeben | `ho m status` | `allowed`, `command: status`, `detail: on`, Antwort ok |
| 3 | freigegeben | `HO M an aus` | kein Kommando, keine Aktion, keine Antwort |
| 4 | nicht freigegeben | `HO M an` | `blocked`, `not_in_allowlist`, keine Aktion, keine Antwort |

Geprüfte Eigenschaften:

- [x] Freigegebener Absender, alle drei Kommandos
- [x] Abweichende Schreibweise (`ho m status`)
- [x] Mehrdeutige Nachricht löst nichts aus
- [x] Nicht freigegebener Absender löst keinen Webhook aus
- [x] Antworttexte werden tatsächlich gesendet
- [x] Unbekannter Zustand (`HTTP 404`) führt zu einer Fehlerantwort
- [x] Nicht erreichbares Home Assistant führt zu einer Fehlerantwort

## Manuelle Abnahme auf srv001

### A1 – Nicht freigegebener Absender

- [x] Allowlist-Eintrag auf `enabled: false` setzen, Dienst neu starten
- [x] `HO M an` senden
- [x] Protokoll: `decision: blocked`, `reason: sender_disabled`, `actionable: false`, `action: null`, `reply: null`
- [x] Keine Antwort im Chat, Switch unverändert
- [x] Eintrag wieder aktivieren, Dienst neu starten

Ergebnis am 2026-11-17:

```json
{"decision":"blocked","reason":"sender_disabled","matched_label":null,"command":"on","actionable":false,"action":null,"reply":null}
```

Das Kommando wurde erkannt, aber nicht ausgeführt und nicht beantwortet. Der
Switch blieb `off`.

### A2 – Unbekannter Zustand und nicht erreichbares Home Assistant

- [x] Status-URL auf eine nicht existierende Entität setzen
- [x] Webhook-URLs auf einen geschlossenen Port setzen
- [x] Dienst neu starten
- [x] `HO M status` senden → Fehlerantwort, `action.ok: false`, `detail: HTTP 404`
- [x] `HO M an` senden → Fehlerantwort, `action.ok: false`, `detail: Verbindung fehlgeschlagen`
- [x] Konfiguration zurückstellen, Dienst neu starten

Ergebnis am 2026-11-17:

| Nachricht | `action` | `reply` |
| :--- | :--- | :--- |
| `HO M status` | `ok: false`, `detail: HTTP 404` | `ok: true` |
| `HO M an` | `ok: false`, `detail: Verbindung fehlgeschlagen: [Errno 111] Connection refused` | `ok: true` |

Beide Fehler wurden erkannt und als Fehler gemeldet. Der Switch blieb
unverändert. Nach dem Zurückstellen lieferte `HO M status` wieder
`ok: true` mit `detail: off`.

### A3 – Keine eingehenden Verbindungen

- [x] `ss -tlnp` zeigt ausschließlich Loopback-Bindungen für `signal-cli` und keine für die Bridge
- [x] `ufw status` unverändert
- [ ] Keine Portfreigabe im Router für `srv001`

Ergebnis am 2026-11-17: Der Bridge-Prozess hat **keinen Listener**;
`signal-cli` lauscht ausschließlich auf `[::ffff:127.0.0.1]:8080`. `ufw` ist
weiterhin inaktiv, es wurde keine Regel hinzugefügt.

Nebenbefund außerhalb des Ticketumfangs: Auf `0.0.0.0` lauschen zusätzlich
nginx (80), CUPS (631) und SSH (22). Diese Dienste stammen nicht aus der
Signal-Integration.

Die Router-Konfiguration wurde nicht geprüft; sie liegt außerhalb von `srv001`
und ist durch den Betreiber zu bestätigen.

## Verifikationsmatrix

| Anforderung aus HAD-0006 | Nachweis | Schritt |
| :--- | :--- | :--- |
| End-to-End-Prüfungen für freigegebene Absender | Integrationstest 1 und 2, manuelle Tests aus HAD-0004/0005 | Test, A1 |
| End-to-End-Prüfungen für nicht freigegebene Absender | Integrationstest 4, A1 | Test, A1 |
| Alle drei Kommandos | Integrationstest 1 und 2, HAD-0004/0005 | Test |
| Unterschiedliche Schreibweisen | Integrationstest 2, HAD-0003 | Test |
| Ungültige Nachrichten | Integrationstest 3, HAD-0003 | Test |
| Unbekannter Switch-Zustand | Integrationstest 5, A2 | Test, A2 |
| Verbindungsfehler | Integrationstest 6, A2 | Test, A2 |
| Keine eingehenden Verbindungen | A3 | A3 |
| Keine Aktion durch nicht freigegebene Absender | Integrationstest 4, A1 | Test, A1 |

## Ergebnis

Alle Prüfungen wurden am 2026-11-17 erbracht.

| Ebene | Ergebnis |
| :--- | :--- |
| Integrationstests | 5 Tests, alle grün, insgesamt 83 Tests im Projekt |
| A1 nicht freigegebener Absender | belegt, keine Aktion, keine Antwort |
| A2 unbekannter Zustand | belegt, `HTTP 404`, Fehlerantwort |
| A2 nicht erreichbares Home Assistant | belegt, `Connection refused`, Fehlerantwort |
| A3 keine eingehenden Verbindungen | belegt, Bridge ohne Listener |

Offen bleibt nur die Bestätigung der Router-Konfiguration durch den Betreiber.
