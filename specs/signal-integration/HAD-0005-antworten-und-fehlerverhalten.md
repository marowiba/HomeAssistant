# Solution Design: HAD-0005 – Signal-Antworten und Fehlerverhalten

## Metadaten

| Feld | Wert |
| :--- | :--- |
| Ticket | HAD-0005 (siehe `backlog.md`) |
| Feature / Epic | Signal-Integration |
| Priorität | Medium |
| Übergreifendes Design | `specs/signal-integration/design.md` |
| Vorgänger | HAD-0004 (`specs/signal-integration/HAD-0004-home-assistant-anbindung.md`) |
| Dokumenttyp | Solution Design, umsetzungsbegleitend |
| Status | umgesetzt, Abnahme offen |

## Ziel

Nach einem erfolgreichen Schaltbefehl oder einer Statusabfrage erhält der
Absender eine verständliche Antwort über Signal. Bei Fehlern wird ausdrücklich
ein Fehler gemeldet, statt eine erfolgreiche Ausführung vorzutäuschen.
Wiederholte An- und Aus-Kommandos bleiben idempotent.

## Abgrenzung

| Thema | Zuständiges Ticket |
| :--- | :--- |
| End-to-End-Abnahme | HAD-0006 |
| Verwaltungsoberfläche | HAD-0008 |

## Entscheidungen

| ID | Entscheidung | Begründung |
| :--- | :--- | :--- |
| E1 | Senden über die JSON-RPC-Schnittstelle des laufenden Daemons | Ein zweiter `signal-cli`-Prozess scheitert am Lock auf dem Konfigurationsverzeichnis |
| E2 | Kein `account`-Parameter im Aufruf | Der Daemon läuft im Single-Account-Modus und wertet den Parameter nicht aus |
| E3 | Antwort nur bei `actionable == true` | Nicht freigegebene Absender erhalten keine Rückmeldung; das entspricht HAD-0002 |
| E4 | Keine Antwort auf unbekannte Texte | HAD-0003 legt fest, dass unbekannte Nachrichten keine Aktion auslösen; eine Antwort wäre eine Reaktion |
| E5 | Technische Fehler werden in verständliche Sätze übersetzt | Der Absender soll handeln können, nicht HTTP-Codes lesen |
| E6 | Der technische Fehlertext bleibt im Protokoll | Diagnose ohne Preisgabe von URL oder Token |
| E7 | Antworttext ist fest im Code, nicht konfigurierbar | Kein Weg, über Konfiguration beliebige Texte zu versenden |

## Antworttabelle

| Situation | Antwort |
| :--- | :--- |
| `HO M an` erfolgreich | „Home Office ist eingeschaltet.“ |
| `HO M aus` erfolgreich | „Home Office ist ausgeschaltet.“ |
| `HO M status`, Zustand `on` | „Home Office ist eingeschaltet.“ |
| `HO M status`, Zustand `off` | „Home Office ist ausgeschaltet.“ |
| `HO M status`, anderer Zustand | „Home Office hat den Zustand: `<zustand>`.“ |
| `HO M status`, kein Zustand in der Antwort | „Fehler: Der Schalterzustand ist unbekannt.“ |
| Aktion nicht ausgeführt | „Fehler: `<übersetzter Grund>`“ |
| Aktion fehlgeschlagen | „Fehler: `<übersetzter Grund>`“ |

## Fehlerabbildung

| Technischer Fehler | Antworttext |
| :--- | :--- |
| `HTTP 401`, `HTTP 403` | „Home Assistant hat den Zugriff abgelehnt.“ |
| `HTTP 404` | „Die Aktion ist in Home Assistant nicht vorhanden.“ |
| `Verbindung fehlgeschlagen: …` | „Home Assistant ist nicht erreichbar.“ |
| `Zeitueberschreitung` | „Home Assistant antwortet nicht.“ |
| `Statusabfrage nicht konfiguriert` | „Die Statusabfrage ist nicht eingerichtet.“ |
| `Anbindung deaktiviert` | „Die Home-Assistant-Anbindung ist deaktiviert.“ |
| sonstiger Text | „Die Aktion ist fehlgeschlagen (`<detail>`).“ |

## Protokollerweiterung

| Feld | Bedeutung |
| :--- | :--- |
| `reply.attempted` | `true`, wenn eine Nachricht gesendet wurde |
| `reply.ok` | `true` bei Erfolg, `false` bei Fehler, `null` wenn nicht gesendet |
| `reply.detail` | Grund, wenn nicht gesendet oder Zustellung fehlgeschlagen |

Beispiel:

```json
{"ts":"2026-11-17T19:23:34+01:00","received_ms":1794939814608,"sender_number":"+49…","sender_uuid":"0929…","sender_name":"Matthias","text":"HO M an","attachments":0,"decision":"allowed","reason":"allowlist","matched_label":"Matthias","command":"on","actionable":true,"action":{"attempted":true,"ok":true,"detail":null},"reply":{"attempted":true,"ok":true,"detail":null}}
```

## Konfiguration

```json
"signal": {
  "enabled": true,
  "rpc_url": "http://127.0.0.1:8080/api/v1/rpc",
  "timeout_seconds": 10
}
```

Fehlt der Abschnitt, gelten diese Werte. `enabled: false` unterdrückt Antworten,
ohne die Aktionen zu verhindern.

## Umsetzungsschritte

### E0 – Voraussetzungen

- [x] HAD-0004 abgeschlossen, Aktionen laufen
- [x] Daemon im Single-Account-Modus erreichbar

### E1 – Sendepfad

- [x] `signal_client.py` mit `send_message`, `build_reply` und `send_reply`
- [x] Konfigurationsabschnitt `signal`
- [x] Antwort nur bei `actionable`, Ergebnis im Protokoll

### E2 – Tests

- [x] Antworttexte für alle drei Kommandos und alle Zustände
- [x] Fehlerabbildung für 401, 404, Verbindungsfehler, Zeitüberschreitung
- [x] JSON-RPC-Fehler und fehlgeschlagene Zustellung
- [x] Kein Versand ohne Empfänger, ohne Kommando oder bei deaktivierter Anbindung

### E3 – Nachweis auf srv001

- [x] `HO M an` → Antwort „Home Office ist eingeschaltet.“
- [x] `HO M aus` → Antwort „Home Office ist ausgeschaltet.“
- [x] `HO M status` → Antwort mit dem aktuellen Zustand
- [x] `HO M an` zweimal → beide Male dieselbe Antwort, Zustand bleibt an
- [ ] Home Assistant gestoppt → Fehlerantwort statt Erfolgsmeldung

Erfüllt am 2026-11-17 auf `srv001`. Fünf Nachrichten, alle mit
`"action":{"ok":true}` und `"reply":{"attempted":true,"ok":true}`:

| Nachricht | Kommando | Aktion | Antwort |
| :--- | :--- | :--- | :--- |
| `HO M an` | `on` | ok | ok |
| `HO M status` | `status` | ok, `detail: on` | ok |
| `HO m an` | `on` | ok | ok |
| `ho m an` | `on` | ok | ok |
| `ho m aus` | `off` | ok | ok |

Die beiden Wiederholungen von `HO M an` in unterschiedlicher Schreibweise
belegen die Idempotenz: gleiche Aktion, gleiche Antwort, Zustand bleibt an.

Der Fall „Home Assistant gestoppt" wurde auf `srv001` nicht geprüft, weil dafür
der Dienst auf dem Pi angehalten werden müsste. Der Fehlerpfad ist durch die
Unit-Tests und durch den `HTTP 401`-Fall aus HAD-0004 belegt: Dort erschien
`"ok":false` mit Fehlertext, ohne Erfolg vorzutäuschen.

## Verifikationsmatrix

| Anforderung aus HAD-0005 | Nachweis | Schritt |
| :--- | :--- | :--- |
| Verständliche Antwort nach Schaltbefehl | `reply.ok: true`, Text im Chat | E3 |
| Verständliche Antwort nach Statusabfrage | Antwort enthält den Zustand | E3 |
| Fehler bei nicht erreichbarem Home Assistant | Fehlertext statt Erfolgsmeldung | E2, E3 |
| Fehler bei fehlgeschlagener Aktion | `action.ok: false` führt zu Fehlerantwort | E2 |
| Kein Vortäuschen von Erfolg | Antwort hängt an `action.ok`, nicht am Kommando | E1 |
| Idempotente Wiederholung | Zweimal `HO M an` ergibt zweimal dieselbe Antwort | E3 |

## Sicherheit

| Risiko | Auswirkung | Gegenmaßnahme |
| :--- | :--- | :--- |
| Antwort an nicht freigegebene Absender | Bestätigung an Unbekannte | Antwort nur bei `actionable` (E3) |
| Fehlertext enthält URL oder Token | Offenlegung von Geheimnissen | Übersetzte Texte, technischer Text nur im Protokoll (E5, E6) |
| Endlosschleife durch eigene Nachrichten | Bot antwortet sich selbst | Antworten gehen an den Absender, nicht an das Bot-Konto; eigene Nachrichten haben keinen Absender im Allowlist-Sinn |
| Beliebig konfigurierbare Texte | Missbrauch als Spam-Kanal | Feste Texte im Code (E7) |

## Übergabe an Folgetickets

- **HAD-0006:** prüft die Antworten Ende-zu-Ende, inklusive des Falls eines
  gestoppten Home Assistant und eines unbekannten Schalterzustands.
- **HAD-0008:** zeigt gesendete Antworten und Zustellfehler im Ereignislog.
