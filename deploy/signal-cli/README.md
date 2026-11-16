# Deployment: signal-cli Empfangsdienst (HAD-0001)

Vorlagen für den dauerhaft laufenden `signal-cli`-Empfangsdienst auf `srv001`.
Die vollständige Begründung, die Schritte S0 bis S5 und die Verifikationsmatrix
stehen in `specs/signal_solution_design.md`.

## Inhalt

| Datei | Ziel auf srv001 |
| :--- | :--- |
| `signal-cli.service` | `/etc/systemd/system/signal-cli.service` |
| `signal-cli.env.example` | `/etc/signal-cli/signal-cli.env` (Werte eintragen) |

## Reihenfolge

1. S0: Ubuntu-Version, Architektur, Java-Version und ausgehende Verbindung prüfen.
2. S1: Dienstbenutzer `signal-cli` und Verzeichnisse anlegen.
3. S2: `signal-cli` nach `/opt/signal-cli` installieren, Prüfsumme verifizieren.
4. S3: Konto interaktiv registrieren und verifizieren.
5. S4: Environment-Datei und Unit-File installieren, Dienst aktivieren.
6. S5: Autostart, Loopback-Bindung, Firewall und Empfangsereignis belegen.

## Installation der Vorlagen

```bash
sudo install -o root -g root -m 0644 signal-cli.service \
     /etc/systemd/system/signal-cli.service
sudo install -o root -g signal-cli -m 0640 signal-cli.env.example \
     /etc/signal-cli/signal-cli.env
sudoedit /etc/signal-cli/signal-cli.env
sudo systemctl daemon-reload
sudo systemctl enable --now signal-cli.service
```

## Regeln

- Keine echte Telefonnummer, kein Verifizierungscode und kein Schlüssel in
  diesem Verzeichnis oder im Repository.
- Der JSON-RPC-Port bleibt auf `127.0.0.1` beschränkt; er kann Nachrichten
  senden und ist damit ein privilegierter Kanal.
- Der Dienst wertet in HAD-0001 keine Nachricht aus und löst keine Aktion aus.
- `MemoryDenyWriteExecute` nicht ergänzen: Der JVM-Dienst benötigt
  beschreibbaren Speicher für den JIT.
- `/var/lib/signal-cli` enthält die Kontoidentität und wird beim Rollback nicht
  gelöscht.
