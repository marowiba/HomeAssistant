# Design: Signal-Kommandos für Home Assistant

## Ziel

Home-Assistant-Geräte sollen über eindeutig definierte Nachrichten in einem
Signal-Chat gesteuert werden können. Der erste Anwendungsfall ist Matthias'
Home-Office-Status: per Chat ein- oder ausschalten.

Dieses Dokument beschreibt nur das Design. Es werden hier weder Dienste
installiert noch Home-Assistant-Konfigurationen oder Server geändert.

Die konkrete, abarbeitbare Umsetzung des ersten Schritts (Empfangsdienst auf
`srv001`, HAD-0001) ist in `specs/signal_solution_design.md` beschrieben.

## Vorgeschlagene Architektur

Ein kleiner Signal-zu-Home-Assistant-Dienst läuft auf dem Ubuntu-Server
`srv001` im Heimnetz. `signal-cli` läuft dort dauerhaft im Daemon-Modus und
empfängt Nachrichten über seine ausgehende Verbindung zu Signal. Der Dienst
verarbeitet eingehende Nachrichten als Ereignisse, prüft Absender und
Befehlsformat und leitet ausschließlich erlaubte Aktionen an Home Assistant
weiter. Ein regelmäßiger Cronjob, der Signal nur in festen Abständen abfragt,
ist für den Chat-Betrieb nicht vorgesehen.

```text
Signal-App
    │ Nachricht
    ▼
Signal-Dienst auf srv001 (signal-cli + Befehlsprüfung)
    │ lokaler HTTPS/HTTP-Webhook-Aufruf
    ▼
Home Assistant (Webhook-Automation)
    │ feste Aktion für genau ein Ziel
    ▼
switch.haustechnik_shc41ccf4_matthias_im_home_office
```

Der Ubuntu-Server darf ausgehend auf Signal zugreifen, ist aber nicht aus dem
Internet erreichbar. Dafür sind keine eingehenden Portfreigaben oder ein
öffentlich erreichbarer Endpunkt erforderlich. Der Signal-Dienst auf `srv001`
baut die Verbindung nach außen auf; der Aufruf von Home Assistant erfolgt
separat über das Heimnetz. Der Ubuntu-Server ist die vorgesehene, aber nicht
zwingende Laufzeitumgebung.

### Zuständigkeiten

- **Signal-Empfang:** `signal-cli` läuft kontinuierlich als Daemon und empfängt
  Nachrichten für ein dediziertes Signal-Konto. Die Kopplung an ein bestehendes
  Konto wäre ebenfalls denkbar, sollte aber nicht ungeprüft persönliche
  Nachrichten für die Steuerung verwenden. Der Befehlsdienst verarbeitet
  eintreffende Ereignisse fortlaufend, statt Nachrichten nur periodisch
  abzurufen.
- **Befehlsdienst:** Er akzeptiert nur freigegebene Signal-Absender und eine
  kleine, explizite Befehlsliste. Er ordnet jeden Befehl einer fest
  hinterlegten Aktion zu.
- **Home Assistant:** Webhook-Automationen führen die konkreten Aktionen aus.
  Pro Aktion wird ein eigener, nicht erratbarer Webhook verwendet; die
  Webhooks sind auf lokale Aufrufe beschränkt (`local_only`).
- **Antwort:** Der Befehlsdienst sendet über Signal eine Bestätigung oder eine
  verständliche Fehlermeldung zurück.

Webhooks vermeiden einen breit berechtigten Home-Assistant-API-Token auf dem
Ubuntu-Server. Die Webhook-IDs sind dennoch wie Zugangsdaten zu schützen und
nicht in Nachrichten, Logs oder öffentlichen Dateien auszugeben.

### Netzwerk und Antwortzeit

- `srv001` benötigt eine funktionierende **ausgehende** Internetverbindung zu
  Signal. Von außen initiierte Verbindungen zum Ubuntu-Server sind nicht
  erforderlich; er wird nicht veröffentlicht und erhält keine Portfreigabe.
- Home Assistant wird vom Ubuntu-Dienst über eine lokale Adresse im Heimnetz
  angesprochen. Auch dafür wird kein externer Zugriff auf Home Assistant
  benötigt.
- Mit dem dauerhaft laufenden Daemon kann der Ablauf quasi in Echtzeit
  reagieren: Nachricht empfangen, Befehl prüfen, Home Assistant aufrufen und
  Bestätigung über Signal zurücksenden. Eine garantierte Echtzeit oder feste
  maximale Antwortzeit gibt es nicht; Signal, Internet, Ubuntu und Home
  Assistant müssen verfügbar sein.
- Bei einem Verbindungsabbruch kann die Bearbeitung verzögert werden. Der
  Daemon und der Befehlsdienst sollten daher automatisch neu starten und
  Fehler melden. Ob während einer Unterbrechung eingegangene Nachrichten später
  zugestellt werden, hängt von Signal und dem Zustand des Clients ab und ist
  keine Echtzeitgarantie.

## Erstes Beispiel: Matthias im Home Office

### Befehle

| Signal-Nachricht | Aktion in Home Assistant | Antwort |
|---|---|---|
| `HO M an` | `switch.turn_on` für `switch.haustechnik_shc41ccf4_matthias_im_home_office` | „Home Office ist eingeschaltet.“ |
| `HO M aus` | `switch.turn_off` für `switch.haustechnik_shc41ccf4_matthias_im_home_office` | „Home Office ist ausgeschaltet.“ |
| `HO M Status` | Zustand von `switch.haustechnik_shc41ccf4_matthias_im_home_office` abfragen | Antwort mit dem aktuellen Zustand („eingeschaltet“ oder „ausgeschaltet“) |

Bei der Befehlsauswertung wird die Groß-/Kleinschreibung ignoriert; zum Beispiel
sind `HO M AN`, `ho m an` und `Ho M An` gleichbedeutend. Nach dieser
Normalisierung werden nur die drei oben definierten Kommandos akzeptiert.
Unbekannte oder mehrdeutige Texte lösen keine Aktion aus. Die Schaltbefehle
setzen den gewünschten Zustand direkt. Ein Umschaltbefehl wie `toggle` ist
absichtlich nicht vorgesehen: Wiederholte Nachrichten bleiben so
vorhersehbar und schalten den Zustand nicht versehentlich zurück.

Für `HO M Status` wird der aktuelle Schalterzustand zurückgemeldet. Ist der
Zustand nicht verfügbar oder unbekannt, antwortet der Dienst mit einem
entsprechenden Fehlerhinweis und behauptet weder „an“ noch „aus“.

Die bestehende Home-Assistant-Logik reagiert auf den Zustand des Switches und
setzt die Solltemperatur entsprechend. Das Signal-System steuert nur den
Switch; es dupliziert weder die Heizungslogik noch sendet es beliebige
Entitäts- oder Dienstnamen aus dem Chat an Home Assistant.

## Sicherheit und Fehlerverhalten

- Nur explizit freigegebene Signal-Absender dürfen Befehle ausführen. Andere
  Absender werden niemals zur Steuerung verwendet: Ihre eingehenden
  Chatnachrichten werden mit Absender und Empfangszeit in ein lokales Chat-Log
  geschrieben, aber nicht als Befehle ausgewertet und lösen keine
  Home-Assistant-Aktion aus.
- Das Chat-Log ist nur für berechtigte Administratoren zugänglich. Da es
  Nachrichteninhalte enthalten kann, sind Speicherort, Dateiberechtigungen und
  eine angemessene Aufbewahrungs- und Löschfrist festzulegen.
- Es werden nur die oben definierten, vollständig erkannten Befehle
  akzeptiert. Unbekannte oder mehrdeutige Texte lösen keine Aktion aus.
- Der Dienst bietet keinen generischen Proxy für Home-Assistant-Dienste,
  Entitäten, Templates oder beliebige URLs.
- Die Home-Assistant-Webhooks sind nur aus dem lokalen Netz erreichbar; HA und
  der Ubuntu-Server werden dafür nicht öffentlich freigegeben.
- Webhook-IDs und Signal-Konto-Zugangsdaten gehören in geschützte
  Konfiguration bzw. Secret-Speicher, nicht in das Repository.
- Aktionen sind idempotent (`turn_on`/`turn_off`). Bei Netzwerk- oder
  Home-Assistant-Fehlern meldet der Dienst einen Fehler, statt eine erfolgreiche
  Ausführung vorzutäuschen.
- Logs sollten Absender und Ergebnis zur Fehlerdiagnose enthalten, aber keine
  Webhook-IDs, Zugangsdaten oder unnötigen Nachrichteninhalte.

## Abgrenzung und mögliche Erweiterungen

Der erste Schritt umfasst die drei Befehle zum Ein- und Ausschalten sowie zur
Statusabfrage für Matthias' Home Office. Weitere Geräte, Gruppen, Rollen oder
freie natürliche Sprache sind nicht Teil dieses Designs. Sie sollten jeweils
mit eindeutigen Befehlen, festgelegten Zielen und passenden Berechtigungen
ergänzt werden.
