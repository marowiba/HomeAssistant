# HAD-0010: Eigene Kommandos in der Weboberfläche anlegen und verwalten

## Ziel

Administratoren können in der Weboberfläche eigene, fest definierte
Signal-Kommandos anlegen, bearbeiten, deaktivieren und löschen. Ein Kommando
besteht aus dem Signal-Text, einer Aktion und einer Home-Assistant-Entität.
Neben `on`, `off` und `status` gibt es die Aktion `set_value`, mit der ein
numerischer Wert gesetzt werden kann — etwa eine Soll-Temperatur. Dezimalwerte
sind erlaubt, mit Komma oder Punkt als Trennzeichen.

Es bleiben feste, validierte Aktionen — keine frei ausführbaren
Home-Assistant-Dienste, Skripte oder Templates.

## Ausgangslage

- [`command_parser.py`](../../signal-bridge/command_parser.py:1) kennt nur
  `HO M an/aus/status`.
- [`bridge.py`](../../signal-bridge/bridge.py:1) hat eine feste
  `FIXED_COMMAND_IDS`-Liste.
- [`ha_client.py`](../../signal-bridge/ha_client.py:1) nutzt Webhooks für
  `on`/`off` und eine feste Status-URL.
- [`config_store.py`](../../signal-admin/signal_admin/config_store.py:1) zeigt
  im UI nur die drei festen `HO M`-Kommandos.

## Datenmodell

Die Konfiguration erhält eine Liste `commands`:

```json
"commands": [
  {
    "id": "ho_m_on",
    "text": "HO M an",
    "action": "on",
    "entity_id": "switch.haustechnik_shc41ccf4_matthias_im_home_office",
    "enabled": true
  },
  {
    "id": "ho_t_set",
    "text": "HO T {wert}",
    "action": "set_value",
    "entity_id": "climate.wohnzimmer",
    "min": 5.0,
    "max": 30.0,
    "unit": "°C",
    "enabled": true
  }
]
```

- `id`: stabile, technische Kennung (vom UI erzeugt, z. B. `cmd_<zufall>`).
- `text`: Signal-Text, normalisiert (Leerraum zusammengefasst,
  Groß-/Kleinschreibung egal) und eindeutig.
- `action`: `on`, `off`, `status` oder `set_value`.
- `entity_id`: Home-Assistant-Entität, Muster `^[a-z_]+\.[a-z0-9_]+$`.
- `enabled`: bool.
- `min`, `max`, `unit`: nur bei `set_value`. `min` und `max` sind Pflicht,
  `unit` ist optional und dient nur der Antwort.

### Platzhalter für Werte

Bei `set_value` muss `text` genau einmal den Platzhalter `{wert}` enthalten,
und zwar am **Ende**. Beispiele: `HO T {wert}`, `Soll {wert}`.

Der Platzhalter am Ende hält die Erkennung eindeutig: Die Bridge vergleicht den
Text vor dem Platzhalter als Präfix und liest den Rest als Zahl. Ein
Literal-Kommando, das genau diesem Präfix entspricht, hat Vorrang (exakter
Treffer).

## Aktionen

| Aktion | Home-Assistant-Aufruf |
| :--- | :--- |
| `on` | `POST /api/services/switch/turn_on` mit `{"entity_id": ...}` |
| `off` | `POST /api/services/switch/turn_off` mit `{"entity_id": ...}` |
| `status` | `GET /api/states/<entity_id>` |
| `set_value` | siehe Tabelle unten |

`set_value` bildet die Entitäts-Domain auf genau einen Dienst ab. Die Domain
kommt aus der validierten `entity_id`, der Dienstname ist fest im Code:

| Domain | Dienst | Nutzlast |
| :--- | :--- | :--- |
| `climate` | `climate.set_temperature` | `{"entity_id": ..., "temperature": <zahl>}` |
| `number` | `number.set_value` | `{"entity_id": ..., "value": <zahl>}` |
| `input_number` | `input_number.set_value` | `{"entity_id": ..., "value": <zahl>}` |

Andere Domains werden bei `set_value` abgelehnt. Der Wert wird als JSON-Zahl
übertragen, nie als Zeichenkette in eine URL oder ein Template eingesetzt.

Alle Aufrufe nutzen den dedizierten Nicht-Admin-Token. Der Token erscheint
nicht in Logs oder Antworten.

## Werteingabe

- Akzeptiert werden Ganzzahlen und Dezimalzahlen, z. B. `21`, `21,5`, `21.5`.
- Komma und Punkt sind als Dezimaltrennzeichen gleichwertig; intern wird mit
  Punkt gerechnet.
- Erlaubt ist ein optionales führendes Minus, Ziffern und höchstens ein
  Trennzeichen. Tausendertrennzeichen, Exponenten und Leerzeichen innerhalb
  der Zahl sind nicht zulässig.
- Der Wert muss zwischen `min` und `max` liegen (einschließlich).
- Gerundet wird auf zwei Nachkommastellen.

## Bridge

- `parse_command` wird durch eine Zuordnung ersetzt, die die konfigurierten
  Kommandotexte (normalisiert) auf `(action, entity_id)` abbildet.
- Zuerst wird ein exakter Literal-Treffer geprüft, danach die
  `set_value`-Kommandos, absteigend nach Präfixlänge.
- Passt das Präfix, der Rest ist aber keine gültige Zahl, gilt das Kommando als
  nicht erkannt: keine Aktion, keine Antwort.
- Ist die Zahl gültig, liegt aber außerhalb von `min`/`max`, wird das Kommando
  erkannt und mit einer Fehlerantwort beantwortet.
- `perform_action` führt die Aktion über die REST-API aus.
- Deaktivierte Kommandos lösen keine Aktion aus.
- Unbekannte oder mehrdeutige Texte bleiben wirkungslos.

## Antworten

| Situation | Antwort |
| :--- | :--- |
| `set_value` auf `climate` erfolgreich | „Soll-Temperatur auf 21,5 °C gesetzt.“ |
| `set_value` auf `number`/`input_number` erfolgreich | „Wert auf 21,5 gesetzt.“ |
| Wert außerhalb `min`/`max` | „Fehler: Wert muss zwischen 5 und 30 liegen.“ |
| `status` auf `climate` | Zustand plus aktuelle und Soll-Temperatur, soweit vorhanden |

Die Antwort gibt den Wert in deutscher Schreibweise mit Komma aus.

## Weboberfläche

- Kommando-Ansicht mit Anlegen, Bearbeiten, Deaktivieren und Löschen.
- Felder: Signal-Text, Aktion (`on`/`off`/`status`/`set_value`), Entitäts-ID,
  aktiv.
- Bei `set_value` zusätzlich: `min`, `max`, `unit`. Das Textfeld wird mit
  `HO T {wert}` vorbelegt.
- Validierung: Text nicht leer und eindeutig; Aktion aus der festen Menge;
  Entitäts-ID entspricht dem Muster; bei `set_value` genau ein `{wert}` am
  Ende, Domain aus der erlaubten Menge, `min` und `max` numerisch und
  `min < max`.
- Jede Änderung wird im Audit-Log protokolliert.
- Bestehende `HO M`-Kommandos werden als Standard übernommen.

## Migration

- Beim ersten Start ohne `commands` werden die drei `HO M`-Kommandos aus den
  bisherigen `home_assistant.actions`/`status`-Werten erzeugt.
- Die alten Felder werden nicht mehr ausgewertet, bleiben aber lesbar.

## Sicherheit

- Feste Aktionsmenge, keine freien Dienste oder Templates.
- `set_value` nur für die Domains `climate`, `number` und `input_number`, mit
  fest zugeordnetem Dienst.
- Entitäts-ID streng validiert.
- Werte werden als Zahl geparst, bereichsgeprüft und als JSON-Zahl übertragen.
- Token nur serverseitig, nie in Antworten oder Logs.
- CSRF-Schutz und Audit-Log wie in HAD-0008.

## Verifikation

- Unit-Tests für Parser, Werteerkennung, Bridge, HA-Client, Konfiguration und
  UI.
- Wertefälle: `21`, `21,5`, `21.5`, `-3`, `21,`, `21,5,5`, `abc`, leer, unter
  `min`, über `max`, genau `min`, genau `max`.
- 424 Tests grün, 100 % Zeilenabdeckung (2174 Zeilen).
- SonarQube: 0 Issues, 0 Duplikate, Quality Gate OK. Bericht
  `tests/sast/reports/2026-11-18_11-18-05_sonar_summary.md`.
- UAT am 2026-11-18: `HO S an/aus/status` auf eine zweite Switch-Entität
  angelegt und ausgeführt; `HO T 21,5` setzt die Soll-Temperatur; der
  Hot-Reload wirkt ohne Dienstneustart.
