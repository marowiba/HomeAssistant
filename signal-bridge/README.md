# Signal-Bridge (HAD-0002)

Dienst, der den Ereignisstrom des `signal-cli`-Daemons liest, Absender gegen eine
Allowlist prüft und jede eingegangene Nachricht in ein lokales Protokoll
schreibt. Es wird nichts ausgewertet und nichts an Home Assistant weitergeleitet.

Die Begründung, die Schritte B0 bis B5 und die Verifikationsmatrix stehen in
`specs/signal-integration/HAD-0002-allowlist-und-chatlog.md`.

## Inhalt

| Datei | Zweck |
| :--- | :--- |
| `bridge.py` | Dienst, nur Standardbibliothek |
| `command_parser.py` | Erkennung der Home-Office-Kommandos und der Hilfe |
| `ha_client.py` | Aufruf der Home-Assistant-Webhooks und Statusabfrage |
| `signal_client.py` | Antworten über den signal-cli-Daemon |
| `config.example.json` | Vorlage für `/etc/signal-bridge/config.json` |
| `tests/test_bridge.py` | Unit-Tests |

## Voraussetzungen

- HAD-0001 abgeschlossen, `signal-cli`-Daemon aktiv
- `GET http://127.0.0.1:8080/api/v1/events` erreichbar
- Python 3.11 oder neuer

## Installation

```bash
sudo install -d -o root -g root -m 0755 /opt/signal-bridge
sudo install -o root -g root -m 0644 bridge.py command_parser.py ha_client.py signal_client.py /opt/signal-bridge/

sudo install -d -o root -g signal-cli -m 0750 /etc/signal-bridge
sudo install -o root -g signal-cli -m 0640 config.example.json /etc/signal-bridge/config.json
sudoedit /etc/signal-bridge/config.json

sudo install -o root -g root -m 0644 ../deploy/signal-bridge/signal-bridge.service \
     /etc/systemd/system/signal-bridge.service
sudo systemctl daemon-reload
sudo systemctl enable --now signal-bridge.service
```

## Konfiguration

| Feld | Bedeutung |
| :--- | :--- |
| `events_url` | Ereignisstrom des Daemons, Standard `http://127.0.0.1:8080/api/v1/events` |
| `log_path` | Protokolldatei, Standard `/var/lib/signal-bridge/messages.jsonl` |
| `retention_days` | Aufbewahrungsfrist in Tagen |
| `timezone` | Zeitzone für den lesbaren Zeitstempel, z. B. `Europe/Berlin` |
| `read_timeout_seconds` | Timeout beim Lesen des Stroms |
| `reconnect_delay_seconds` | Wartezeit vor erneutem Verbinden |
| `prune_interval_seconds` | Abstand der Aufbewahrungsbereinigung |
| `allowlist` | Liste der freigegebenen Absender |
| `signal` | Antworten über den Daemon, siehe unten |
| `home_assistant` | Webhook-Anbindung, siehe unten |

Ein Allowlist-Eintrag braucht `label` und mindestens eines von `number` oder
`uuid`. Ist eine `uuid` gesetzt, muss sie übereinstimmen; eine abweichende UUID
blockiert den Absender auch dann, wenn die Nummer passt. Damit erbt eine neu
vergebene Rufnummer keine Rechte.

## Protokoll

JSON Lines, ein Objekt pro Zeile:

```json
{"ts":"2026-11-17T14:02:11+01:00","received_ms":1794920531000,"sender_number":"+49XXXXXXXXXX","sender_uuid":"0929926d-1816-4157-9e5f-f57862547f66","sender_name":"Matthias","text":"HO M an","attachments":0,"decision":"allowed","reason":"allowlist","matched_label":"Matthias","command":"on","actionable":true}
```

`decision` ist `allowed` oder `blocked`, `reason` ist `allowlist`,
`not_in_allowlist` oder `sender_disabled`.

`command` ist `on`, `off`, `status`, `help` oder `null`. `actionable` ist nur dann
`true`, wenn der Absender freigegeben **und** ein Kommando erkannt wurde. Nur
dieses Feld entscheidet über eine Aktion.

`action` ist `null`, wenn nichts ausgeführt wurde. Sonst enthält es
`attempted`, `ok` und `detail`. Bei einer Statusabfrage steht in `detail` der
Zustand, etwa `on` oder `off`; bei Fehlern ein Text ohne URL.

`reply` ist `null`, wenn keine Antwort gesendet wurde. Sonst enthält es
`attempted`, `ok` und `detail`.

## Antworten

```json
"signal": {
  "enabled": true,
  "rpc_url": "http://127.0.0.1:8080/api/v1/rpc",
  "timeout_seconds": 10
}
```

Antworten gehen über die JSON-RPC-Schnittstelle des laufenden Daemons; ein
zweiter `signal-cli`-Prozess würde am Lock scheitern. Der `account`-Parameter
entfällt, weil der Daemon im Single-Account-Modus läuft.

| Situation | Antwort |
| :--- | :--- |
| `HO M an` erfolgreich | „Home Office ist eingeschaltet.“ |
| `HO M aus` erfolgreich | „Home Office ist ausgeschaltet.“ |
| `HO M status` | Zustand als Satz, sonst „Home Office hat den Zustand: …“ |
| `Hilfe` oder `?` | Liste der verfügbaren Kommandos |
| Fehler | „Fehler: …“ mit verständlichem Grund |

Nicht freigegebene Absender erhalten keine Antwort. Unbekannte Texte lösen
weder Aktion noch Antwort aus.

## Home-Assistant-Anbindung

```json
"home_assistant": {
  "enabled": true,
  "timeout_seconds": 10,
  "actions": {
    "on": "http://<pi>:8123/api/webhook/<id-on>",
    "off": "http://<pi>:8123/api/webhook/<id-off>"
  },
  "status": {
    "url": "http://<pi>:8123/api/states/switch.haustechnik_shc41ccf4_matthias_im_home_office",
    "token": "<long-lived-token>"
  }
}
```

Schaltbefehle laufen über Webhooks und brauchen keinen Token. Der Status wird
über die REST-API gelesen, weil Webhooks in Home Assistant keine Daten
zurückgeben können. Dafür ist ein dedizierter Nicht-Admin-Benutzer mit
Long-Lived-Token vorgesehen; der Token wird nur für einen GET auf genau eine
Entität verwendet und erscheint in keinem Log.

Fehlt der Abschnitt `status`, wird geschaltet, aber `HO M Status` meldet
`Statusabfrage nicht konfiguriert`. Die Automationen liegen als Vorlage in
`deploy/home-assistant/signal_ho_commands.yaml`.

## Kommandos

Akzeptiert werden ausschließlich `HO M an`, `HO M aus` und `HO M Status`,
unabhängig von Groß- und Kleinschreibung und mit beliebigem Leerraum.
`HO M an aus`, `HO M an!` oder `HO M` ergeben kein Kommando.

## Betrieb

```bash
systemctl status signal-bridge.service
sudo -u signal-cli tail -n 20 /var/lib/signal-bridge/messages.jsonl
sudo -u signal-cli grep '"decision":"blocked"' /var/lib/signal-bridge/messages.jsonl
python3 /opt/signal-bridge/bridge.py --config /etc/signal-bridge/config.json --check-config
```

`--dry-run` gibt Einträge auf stdout aus, statt sie zu schreiben.

## Tests

```bash
python -m unittest discover -s signal-bridge/tests -v
```

## Rechte

Die Logdatei entsteht mit `0640`, das Verzeichnis mit `0750`, beides in der
Gruppe `signal-cli`. Administratoren, die das Protokoll lesen sollen, werden
dieser Gruppe hinzugefügt. Das Protokoll enthält Nachrichteninhalte und ist
deshalb wie personenbezogene Daten zu behandeln.
