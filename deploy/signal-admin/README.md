# Signal-Administration (HAD-0008)

Reine Server-Webanwendung auf `srv001` zur Verwaltung der Signal-Integration.
Erreichbar unter `http://signal-admin.srv001` (bzw. `http://signal-admin.srv001:8090`),
nur im lokalen Netzwerk. Keine Desktop-Installation, keine Internetveroeffentlichung,
keine eingehende Portfreigabe.

## Voraussetzungen

- Python 3.11 oder neuer (Standardbibliothek, keine externen Pakete).
- Laufender `signal-bridge.service` und `signal-cli`.
- Schreibrechte auf `/etc/signal-bridge/config.json` und
  `/var/lib/signal-bridge/messages.jsonl`.

## Installation

```bash
# 1. Dienstbenutzer und Verzeichnisse
sudo useradd --system --home /var/lib/signal-admin --shell /usr/sbin/nologin signal-admin
sudo install -d -o signal-admin -g signal-admin -m 0750 /var/lib/signal-admin
sudo install -d -o root -g signal-admin -m 0750 /etc/signal-admin
sudo install -d -o root -g root -m 0755 /opt/signal-admin

# 2. Anwendung kopieren (aus dem Repository)
sudo cp -r signal-admin/signal_admin /opt/signal-admin/
sudo cp deploy/signal-admin/README.md /opt/signal-admin/README.md

# 3. Umgebung
sudo cp deploy/signal-admin/signal-admin.env.example /etc/signal-admin/signal-admin.env
sudo chown root:signal-admin /etc/signal-admin/signal-admin.env
sudo chmod 0640 /etc/signal-admin/signal-admin.env
# SIGNAL_ADMIN_SECRET setzen:
python3 -c "import secrets; print(secrets.token_urlsafe(48))"

# 4. Administratorkonto anlegen (Passwort wird interaktiv abgefragt)
sudo -u signal-admin env SIGNAL_ADMIN_SECRET="$(sudo grep ^SIGNAL_ADMIN_SECRET /etc/signal-admin/signal-admin.env | cut -d= -f2-)" \
  python3 -m signal_admin.app \
  --config /etc/signal-bridge/config.json \
  --log /var/lib/signal-bridge/messages.jsonl \
  --db /var/lib/signal-admin/admin.db \
  --create-user admin

# 5. systemd-Dienst
sudo cp deploy/signal-admin/signal-admin.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now signal-admin.service
```

## Netzwerk und URL

- `SIGNAL_ADMIN_HOST` auf die LAN-Adresse von `srv001` setzen, damit der Dienst
  im lokalen Netz erreichbar ist. `127.0.0.1` laesst nur lokale Zugriffe zu.
- Fuer die URL `http://signal-admin.srv001` einen DNS- oder Hosts-Eintrag auf
  `srv001` anlegen. Ohne Reverse-Proxy den Port mitgeben
  (`http://signal-admin.srv001:8090`).
- Optional leitet ein Reverse-Proxy (nginx) Port 80 auf `127.0.0.1:8090` um.
- Die Firewall (`ufw`) beschraenkt den Port auf das lokale Netz, z. B.:
  `sudo ufw allow from 192.168.1.0/24 to any port 8090 proto tcp`.

## Sicherheit

- Anmeldung mit PBKDF2-HMAC-SHA256, Sitzungs-Cookies `HttpOnly` und
  `SameSite=Strict`, CSRF-Schutz fuer alle schreibenden Anfragen.
- Login-Rate-Limit pro Client-Adresse.
- Sicherheitsheader: CSP, `X-Frame-Options: DENY`, `X-Content-Type-Options`,
  `Referrer-Policy`.
- Audit-Log append-only mit Hash-Kette; Aenderungen und Loeschungen werden
  manipulationserkennbar protokolliert.
- Keine Secrets in Logs oder Antworten.

## Betrieb

```bash
sudo systemctl status signal-admin.service
sudo journalctl -u signal-admin.service -n 50 --no-pager
```

Konfiguration und Ereignislog werden direkt von der Bridge gelesen. Aenderungen
an Allowlist, Kommandos und Aufbewahrung schreibt die Weboberflaeche atomar in
`/etc/signal-bridge/config.json`. Die Bridge liest die Konfiguration beim Start;
fuer Kommando-Aenderungen den Dienst neu starten:

```bash
sudo systemctl restart signal-bridge.service
```
