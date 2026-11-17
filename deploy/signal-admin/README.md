# Signal-Administration (HAD-0008)

Reine Server-Webanwendung auf `srv001` zur Verwaltung der Signal-Integration.
Erreichbar unter `http://signal-admin.srv001` (bzw.
`http://signal-admin.srv001.fritz.box`), nur im lokalen Netzwerk. Keine
Desktop-Installation, keine Internetveroeffentlichung, keine eingehende
Portfreigabe.

## Architektur

- Die Anwendung bindet an `127.0.0.1:8090`.
- nginx (Port 80) leitet `signal-admin.srv001` als Reverse-Proxy an
  `127.0.0.1:8090` weiter (wie `sonar.srv001` und `rpace.srv001`).
- Der Dienst laeuft als Benutzer `signal-cli`, damit er die
  Bridge-Konfiguration und das Ereignislog lesen und schreiben kann.

## Voraussetzungen

- Python 3.11 oder neuer (Standardbibliothek, keine externen Pakete).
- Laufender `signal-bridge.service` und `signal-cli`.
- nginx auf Port 80.
- Schreibrechte auf `/etc/signal-bridge/config.json` und
  `/var/lib/signal-bridge/messages.jsonl` (Benutzer `signal-cli`).

## Installation

```bash
# 1. Verzeichnisse
sudo install -d -o signal-cli -g signal-cli -m 0750 /var/lib/signal-admin
sudo install -d -o root -g signal-cli -m 0750 /etc/signal-admin
sudo install -d -o root -g root -m 0755 /opt/signal-admin

# 2. Anwendung entpacken
sudo tar -xzf /tmp/signal-admin-deploy.tar.gz -C /opt/signal-admin
sudo chown -R root:root /opt/signal-admin

# 3. Umgebung mit zufaelligem Secret
SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")
sudo tee /etc/signal-admin/signal-admin.env >/dev/null <<EOF
SIGNAL_ADMIN_HOST=127.0.0.1
SIGNAL_ADMIN_PORT=8090
SIGNAL_ADMIN_SECRET=$SECRET
EOF
sudo chown root:signal-cli /etc/signal-admin/signal-admin.env
sudo chmod 0640 /etc/signal-admin/signal-admin.env

# 4. Bridge-Konfiguration fuer signal-cli schreibbar machen
sudo chown signal-cli:signal-cli /etc/signal-bridge/config.json

# 5. systemd-Dienst
sudo install -o root -g root -m 0644 /tmp/signal-admin.service /etc/systemd/system/signal-admin.service
sudo systemctl daemon-reload
sudo systemctl enable --now signal-admin.service

# 6. nginx-Reverse-Proxy
sudo install -o root -g root -m 0644 /tmp/signal-admin.nginx.conf /etc/nginx/sites-available/signal-admin.conf
sudo ln -sf /etc/nginx/sites-available/signal-admin.conf /etc/nginx/sites-enabled/signal-admin.conf
sudo nginx -t && sudo systemctl reload nginx

# 7. Administratorkonto (Passwort interaktiv)
sudo -u signal-cli env \
  SIGNAL_ADMIN_SECRET="$(sudo grep '^SIGNAL_ADMIN_SECRET=' /etc/signal-admin/signal-admin.env | cut -d= -f2-)" \
  PYTHONPATH=/opt/signal-admin \
  python3 -m signal_admin.app \
  --config /etc/signal-bridge/config.json \
  --log /var/lib/signal-bridge/messages.jsonl \
  --db /var/lib/signal-admin/admin.db \
  --create-user admin
```

## Pruefung

```bash
systemctl status signal-admin.service --no-pager
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8090/login
curl -s -o /dev/null -w "%{http_code}\n" -H "Host: signal-admin.srv001" http://127.0.0.1/login
```

Beide `curl`-Aufrufe liefern `200`.

## Sicherheit

- Anmeldung mit PBKDF2-HMAC-SHA256, Sitzungs-Cookies `HttpOnly` und
  `SameSite=Strict`, CSRF-Schutz fuer alle schreibenden Anfragen.
- Login-Rate-Limit pro Client-Adresse (ueber `X-Forwarded-For` von nginx).
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

Aenderungen an Allowlist, Kommandos und Aufbewahrung schreibt die Weboberflaeche
atomar in `/etc/signal-bridge/config.json`. Die Bridge liest die Konfiguration
beim Start; fuer Kommando-Aenderungen den Dienst neu starten:

```bash
sudo systemctl restart signal-bridge.service
```
