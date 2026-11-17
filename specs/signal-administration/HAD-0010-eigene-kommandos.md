# HAD-0010: Eigene Kommandos in der Weboberfläche anlegen und verwalten

## Ziel

Administratoren können in der Weboberfläche eigene, fest definierte
Signal-Kommandos anlegen, bearbeiten, deaktivieren und löschen. Ein Kommando
besteht aus dem Signal-Text, einer Aktion und einer Home-Assistant-Entität.
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
  }
]
```

- `id`: stabile, technische Kennung (vom UI erzeugt, z. B. `cmd_<zufall>`).
- `text`: Signal-Text, normalisiert (Leerraum zusammengefasst,
  Groß-/Kleinschreibung egal) und eindeutig.
- `action`: ausschließlich `on`, `off` oder `status`.
- `entity_id`: Home-Assistant-Entität, Muster
  `^[a-z_]+\.[a-z0-9_]+$`.
- `enabled`: bool.

Die bisherige `home_assistant.actions`- und `home_assistant.status`-Struktur
wird durch eine gemeinsame REST-Anbindung ersetzt:

```json
"home_assistant": {
  "enabled": true,
  "timeout_seconds": 10,
  "base_url": "http://192.168.1.10:8123",
  "token": "REPLACE_TOKEN"
}
```

## Aktionen

| Aktion | Home-Assistant-Aufruf |
| :--- | :--- |
| `on` | `POST /api/services/switch/turn_on` mit `{"entity_id": ...}` |
| `off` | `POST /api/services/switch/turn_off` mit `{"entity_id": ...}` |
| `status` | `GET /api/states/<entity_id>` |

Alle Aufrufe nutzen den dedizierten Nicht-Admin-Token. Der Token erscheint
nicht in Logs oder Antworten.

## Bridge

- `parse_command` wird durch eine Zuordnung ersetzt, die die konfigurierten
  Kommandotexte (normalisiert) auf `(action, entity_id)` abbildet.
- `perform_action` führt die Aktion über die REST-API aus.
- Deaktivierte Kommandos lösen keine Aktion aus.
- Unbekannte oder mehrdeutige Texte bleiben wirkungslos.

## Weboberfläche

- Kommando-Ansicht mit Anlegen, Bearbeiten, Deaktivieren und Löschen.
- Felder: Signal-Text, Aktion (Auswahl `on`/`off`/`status`), Entitäts-ID,
  aktiv.
- Validierung: Text nicht leer und eindeutig; Aktion aus der festen Menge;
  Entitäts-ID entspricht dem Muster.
- Jede Änderung wird im Audit-Log protokolliert.
- Bestehende `HO M`-Kommandos werden als Standard übernommen.

## Migration

- Beim ersten Start ohne `commands` werden die drei `HO M`-Kommandos aus den
  bisherigen `home_assistant.actions`/`status`-Werten erzeugt.
- Die alten Felder werden nicht mehr ausgewertet, bleiben aber lesbar.

## Sicherheit

- Feste Aktionsmenge, keine freien Dienste oder Templates.
- Entitäts-ID streng validiert.
- Token nur serverseitig, nie in Antworten oder Logs.
- CSRF-Schutz und Audit-Log wie in HAD-0008.

## Verifikation

- Unit-Tests für Parser, Bridge, HA-Client, Konfiguration und UI.
- 100 % Zeilenabdeckung der Quelldateien.
- SonarQube: 0 Issues, 0 Duplikate, Quality Gate OK.
