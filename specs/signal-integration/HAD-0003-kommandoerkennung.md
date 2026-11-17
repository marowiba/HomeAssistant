# Solution Design: HAD-0003 – Home-Office-Kommandos erkennen

## Metadaten

| Feld | Wert |
| :--- | :--- |
| Ticket | HAD-0003 (siehe `backlog.md`) |
| Feature / Epic | Signal-Integration |
| Priorität | High |
| Übergreifendes Design | `specs/signal-integration/design.md` |
| Vorgänger | HAD-0002 (`specs/signal-integration/HAD-0002-allowlist-und-chatlog.md`) |
| Dokumenttyp | Solution Design, umsetzungsbegleitend |
| Status | umgesetzt |

## Ziel

Die Bridge erkennt ausschließlich die drei definierten Kommandos `HO M an`,
`HO M aus` und `HO M Status`. Die Erkennung ist unabhängig von Groß- und
Kleinschreibung. Unbekannte, abweichende oder mehrdeutige Nachrichten ergeben
kein Kommando und lösen keine Aktion aus.

In diesem Ticket wird **nichts ausgeführt**. Die Erkennung wird im Protokoll
festgehalten, damit HAD-0004 darauf aufsetzen kann.

## Abgrenzung

| Thema | Zuständiges Ticket |
| :--- | :--- |
| Aufruf von Home Assistant | HAD-0004 |
| Antworten an den Absender | HAD-0005 |
| End-to-End-Abnahme | HAD-0006 |

## Entscheidungen

| ID | Entscheidung | Begründung |
| :--- | :--- | :--- |
| C1 | Eigener Parser in `command_parser.py` | Trennt Erkennung von Transport und Protokoll; HAD-0004 und HAD-0005 können ihn unverändert nutzen |
| C2 | Normalisierung über Leerraum-Vereinheitlichung und `casefold()` | Erfüllt die Anforderung „unabhängig von Groß- und Kleinschreibung" und toleriert mehrfache Leerzeichen |
| C3 | Exakte Gleichheit nach der Normalisierung, keine Teilstring-Suche | Verhindert, dass `HO M an aus` oder `HO M an!` als Kommando durchgehen |
| C4 | Keine Satzzeichen- oder Füllwort-Toleranz | Die Spezifikation nennt genau drei Kommandos; jede Toleranz erzeugt Mehrdeutigkeit |
| C5 | Kommando wird auch bei blockierten Absendern protokolliert, aber nicht als ausführbar markiert | Macht Fehlkonfigurationen sichtbar, ohne Rechte zu vergeben |
| C6 | Ausführbarkeit als eigenes Feld `actionable` | Trennt „erkannt" von „darf ausgeführt werden"; HAD-0004 prüft nur `actionable` |

## Erkennungsregel

1. `text` fehlt oder ist leer → kein Kommando.
2. Alle Folgen von Leerraum werden zu einem einzelnen Leerzeichen.
3. Der Text wird mit `casefold()` vereinheitlicht.
4. Das Ergebnis wird exakt mit den drei Kommandos verglichen.

| Eingabe | Normalisiert | Ergebnis |
| :--- | :--- | :--- |
| `HO M an` | `ho m an` | `on` |
| `ho m AN` | `ho m an` | `on` |
| `  Ho   M   An  ` | `ho m an` | `on` |
| `HO M aus` | `ho m aus` | `off` |
| `HO M Status` | `ho m status` | `status` |
| `HO M an aus` | `ho m an aus` | kein Kommando |
| `HO M an!` | `ho m an!` | kein Kommando |
| `HO M` | `ho m` | kein Kommando |
| `Hallo` | `hallo` | kein Kommando |

## Erweiterung des Protokolleintrags

Zwei Felder kommen hinzu:

| Feld | Bedeutung |
| :--- | :--- |
| `command` | `on`, `off`, `status` oder `null` |
| `actionable` | `true` nur wenn der Absender freigegeben **und** ein Kommando erkannt wurde |

Beispiel:

```json
{"ts":"2026-11-17T14:02:11+01:00","received_ms":1794920531000,"sender_number":"+49…","sender_uuid":"0929…","sender_name":"Matthias","text":"HO M an","attachments":0,"decision":"allowed","reason":"allowlist","matched_label":"Matthias","command":"on","actionable":true}
```

## Umsetzungsschritte

### C0 – Voraussetzungen

- [x] HAD-0002 abgeschlossen, Bridge im Betrieb
- [x] Freigegebener Absender in der Allowlist

### C1 – Parser und Integration

- [x] `command_parser.py` mit `normalize` und `parse_command`
- [x] `build_record` um `command` und `actionable` erweitert
- [x] Journalzeile nennt das erkannte Kommando

### C2 – Tests

- [x] Exakte Kommandos, Groß- und Kleinschreibung, zusätzlicher Leerraum
- [x] Unbekannte und mehrdeutige Texte
- [x] Kopplung an die Allowlist: blockiert bleibt nicht ausführbar
- [x] Nachricht ohne Text, etwa reine Anhangsnachricht

### C3 – Nachweis auf srv001

- [x] `HO M an` vom freigegebenen Absender → `command: on`, `actionable: true`
- [x] `ho m status` in anderer Schreibweise → `command: status`, `actionable: true`
- [x] `HO M an aus` → `command: null`, `actionable: false`
- [ ] `HO M an` von einem nicht freigegebenen Absender → `command: on`, `actionable: false`

Erfüllt am 2026-11-17 auf `srv001`. `HO M an`, `HO M aus` und `HO M status`
ergaben `on`, `off` und `status` mit `actionable: true`. `HO M an aus` ergab
`command: null` und `actionable: false`. `ho m AN` ergab `on` mit
`actionable: true` und belegt die Unabhängigkeit von der Schreibweise.

Der vierte Fall ist durch den Unit-Test `test_blocked_command_is_not_actionable`
abgedeckt, auf `srv001` aber nicht separat geprüft, weil dafür ein zweiter
Signal-Absender nötig wäre.

## Verifikationsmatrix

| Anforderung aus HAD-0003 | Nachweis | Schritt |
| :--- | :--- | :--- |
| Nur die drei Kommandos werden akzeptiert | `parse_command` liefert nur für diese drei Werte ein Ergebnis | C2 |
| Auswertung unabhängig von Groß- und Kleinschreibung | Testfälle mit gemischter Schreibweise | C2 |
| Unbekannte Nachrichten lösen keine Aktion aus | `command: null`, `actionable: false` | C2, C3 |
| Mehrdeutige Nachrichten lösen keine Aktion aus | `HO M an aus` ergibt kein Kommando | C2, C3 |
| Keine Ausführung in diesem Ticket | Kein Aufruf außerhalb des Ereignisstroms im Code | C1 |

## Sicherheit

| Risiko | Auswirkung | Gegenmaßnahme |
| :--- | :--- | :--- |
| Teilstring-Treffer | `HO M an aus` schaltet ein | Exakte Gleichheit (C3) |
| Kommando von nicht freigegebenem Absender | Unbefugte Steuerung | `actionable` nur bei `decision == allowed` (C5, C6) |
| Versteckte Zeichen oder Unicode-Varianten | Umgehung der Erkennung | `casefold()` und Leerraum-Normalisierung; keine weiteren Toleranzen |
| Vorzeitige Wirkung | Aktion ohne Freigabe | Kein Home-Assistant-Aufruf in diesem Ticket |

## Übergabe an Folgetickets

- **HAD-0004:** prüft ausschließlich `actionable == true` und bildet `command`
  auf die feste Aktion ab. Keine dynamischen Entitäts- oder Dienstnamen.
- **HAD-0005:** antwortet auf Basis von `command` und dem Ergebnis der Aktion.
- **HAD-0006:** prüft die Grenzfälle aus C2 und C3 zusätzlich Ende-zu-Ende.
