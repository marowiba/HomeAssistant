# HAD-0009: Registrierungspin für das Signal-Konto einrichten

## Ziel

Das dedizierte Signal-Konto des Bots wird mit einem Registrierungspin
(Registration Lock) geschützt. Wer die Telefonnummer später erneut bei Signal
registrieren will, benötigt zusätzlich zur SMS die PIN. Damit verhindert eine
neu vergebene Prepaid-Nummer die Übernahme der Bot-Identität.

## Ausgangslage

- `signal-cli` 0.14.10, Konto in `/var/lib/signal-cli`, Daemon auf
  `127.0.0.1:8080` mit JSON-RPC unter `/api/v1/rpc`.
- Die Nummer ist eine Prepaid-SIM. Bei Verlust oder Ablauf kann der Anbieter
  sie neu vergeben.
- Ohne PIN genügt der Besitz der Nummer, um das Konto neu zu registrieren.

## Umsetzung

### S1: Unterstützung prüfen

Geprüft am 2026-11-18 auf `srv001`:

- `signal-cli 0.14.10` kennt `setPin` als Unterbefehl. Der PIN ist ein
  **Positionsargument**: `signal-cli setPin <pin>`.
- Der laufende Daemon implementiert `listAccounts` nicht
  (`-32601 Method not implemented`). Die JSON-RPC-Schnittstelle stellt damit
  nur einen Teil der CLI-Befehle bereit; `setPin` ist dort nicht verfügbar.

Damit ist der Weg über die CLI verbindlich.

### S2: PIN setzen

Der Daemon hält den Account-Lock, deshalb wird er für den Setz-Vorgang kurz
gestoppt und danach wieder gestartet. Die Bridge verbindet ihren
Ereignisstrom automatisch neu.

Der PIN wird interaktiv mit `read -s` eingegeben und als Variable übergeben.
In der Shell-Historie steht nur `"$PIN"`, nie der Wert. Für die Laufzeit des
`signal-cli`-Prozesses ist der PIN als Argument sichtbar; das ist auf `srv001`
auf die lokalen Benutzer `root`, `matti` und `signal-cli` beschränkt und wird
als Restrisiko akzeptiert.

### S3: PIN ablegen

Der PIN wird ausschließlich in `/etc/signal-cli/registration-pin` abgelegt:
`root:root`, Modus `0600`, Verzeichnis `0700`. Nicht im Repository, nicht in
`.env`, nicht in Logs.

### S4: Wiederherstellung dokumentieren

- Wer die PIN kennt: der Benutzer und der Passwortmanager.
- Bei vergessener PIN und vorhandener Nummer: Rücksetzen über den
  Bestätigungscode, sieben Tage Sperre.
- Bei verlorener Nummer: Das Konto gilt als verloren. Die Nummer ist als
  kompromittiert zu behandeln und die Allowlist zu prüfen.

## Entscheidungen

- **E1:** CLI statt JSON-RPC, weil der Daemon `setPin` nicht über JSON-RPC
  anbietet. Der Dienst wird für den Vorgang kurz gestoppt.
- **E2:** PIN-Eingabe interaktiv, nie als Literal in einem Befehl.
- **E3:** Ablage nur auf `srv001` mit `0600 root:root`.
- **E4:** Kein `removePin` im Regelbetrieb; Entfernen nur bewusst und
  dokumentiert.

## Verifikation

- `signal-cli setPin` wurde mit Exit-Code 0 beendet; der PIN ist gesetzt.
- Der PIN liegt in `/etc/signal-cli/registration-pin` (`0600 root:root`,
  Verzeichnis `0700`). Die Datei wird nur bei erfolgreichem `setPin`
  geschrieben, damit ein Tippfehler keine falsche PIN hinterlässt.
- `signal-cli.service` und `signal-bridge.service` laufen nach dem Neustart.
- Eine Testnachricht `Hilfe` wird verarbeitet und beantwortet; das Konto
  arbeitet normal weiter.
- Der PIN taucht in keinem Log, keiner Nachricht und keinem Commit auf.
- Ein erneutes `setPin` mit derselben PIN ist idempotent. Es wurde nicht
  wiederholt, um den PIN nicht zusätzlich zu exponieren.

## Risiken

- Bei PIN-Verlust ist eine Neuregistrierung erst nach sieben Tagen möglich.
- Der PIN schützt nicht davor, die Nummer zu verlieren, und nicht `srv001`.
- Laut `signal-cli`-Hilfe wird der Registrierungspin nach sieben Tagen
  Inaktivität zurückgesetzt. Bei einem dauerhaft genutzten Bot-Konto greift die
  Sperre; nach längerer Pause muss sie erneut gesetzt werden.
- Während des Setzens ist der PIN kurz als Prozessargument sichtbar.
