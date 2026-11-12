# Home-Assistant-Dashboards

## Grundlage der Analyse

Die Bestandsaufnahme wurde über den Home-Assistant-MCP-Server erstellt. Er meldet vier Dashboards im **Storage-Modus**. Die Konfiguration liegt daher in Home Assistant und wurde vom MCP als strukturierte Konfiguration mit `views`, `sections` und Karten geliefert – nicht als YAML-Datei. Die unten gezeigten Strukturen und Entitäten entsprechen diesem ausgelesenen Stand.

Es gibt 14 explizit konfigurierte Ansichten in drei Dashboards. Das vierte Dashboard („Karte“) verwendet eine Strategie, deren Ansichten erst zur Laufzeit erzeugt werden. Der MCP meldet außerdem **keine registrierten Lovelace-Ressourcen** (etwa zusätzliche Karten oder Themes).

## Übersicht aller Dashboards

| Dashboard | Primärer Zweck | Konfiguration und Layout |
|---|---|---|
| **Karte** (`map`) | Karten-/Standortansicht | Storage-Dashboard mit `strategy: {type: map}`; Ansichten werden zur Laufzeit erzeugt und sind in der gespeicherten Konfiguration nicht einzeln aufgeführt. Nur für Administratoren, nicht in der Seitenleiste. |
| **Erdgeschoss** (`dashboard-erdgeschoss`) | Bedienung und Informationen für Räume im Erdgeschoss | Sechs `sections`-Ansichten: Küche, Wohnzimmer, Terrasse EG, Straße, Schlafzimmer und Bad. Sections enthalten überwiegend `grid`-Karten mit `heading`, `area`, `tile`, `entities` und vereinzelt `entity`/`graph`. |
| **Untergeschoss** (`dashboard-untergeschoss`) | Räume und Geräte im Untergeschoss | Vier `sections`-Ansichten: Büro Matthias, Lounge, Büro Stefaniya und Terrasse UG. Sections mit `grid`; vor allem `heading`, `area`, `tile` und `entities`, ergänzt um `entity`/`graph`. |
| **Übersicht** (`lovelace`) | Zentrale Steuerung und systemübergreifende Informationen | Vier `sections`-Ansichten: Beleuchtung, Heizung (`heizung`), Auto (`auto`) und Dokumentation (`dokumentation`). Sections mit `grid`; `tile`/`entities`, Klima- und Graph-Karten sowie eine Markdown-Karte. Die Ansichten Beleuchtung und Heizung gruppieren Geräte nach Etage bzw. Raum. |

Bei Sections-Ansichten sind meist explizite `heading`-Karten in `grid`-Karten verschachtelt. Angegebene `max_columns`-Werte reichen von 3 bis 4; wo keiner gesetzt ist, greift der Home-Assistant-Standard.

## Struktur & Entitäten

### Karte

- **Aufbau:** Strategie `map`; keine statisch gespeicherten Views oder Karten, die sich aus der abgefragten Konfiguration beschreiben ließen.
- **Zugriff:** `require_admin: true`; `show_in_sidebar: false`.
- **Entitäten:** Die Strategie-Konfiguration weist keine einzelnen Entitäten aus.

### Erdgeschoss

| Ansicht | Hauptbereiche und Schlüssel-Entitäten |
|---|---|
| **Küche** | Beleuchtung über den Bereich `kuche`; Automationen `automation.erste_taste_gedruckt` und `automation.kuchenlicht_aus`; Batterie `sensor.paulmann_switch_1_batterie`. |
| **Wohnzimmer** | Beleuchtung mit drei Stehlampen-Schaltern; Klima für Wohnzimmer und Flur (`climate.raumkl_wohnzimmer_eg`, `climate.raumkl_flur`, Temperatur-/Feuchtigkeitssensoren und Offset-Zahlen); Unterhaltung (`media_player.lg_webos_tv_nano81t6a_2`); Licht-Automationen. Vier Badges zeigen Fahrzeit- und Büroklima-Sensoren. |
| **Terrasse EG** | Beleuchtung über den Bereich `terrasse_eg`; Automationen `automation.terrasse_eg_an` und `automation.terrasse_eg_aus`. |
| **Straße** | Fassadenlicht-Schalter; Wetter mit Sonnenauf-/untergang sowie `weather.forecast_home_1` und `weather.forecast_heidelberg_bergstrasse_58`; Automationen. |
| **Schlafzimmer** | Wecker mit `sensor.somneo_alarm_status` und `sensor.somneo_next_alarm`; Klima (`climate.raumkl_schlafzimmer`, Feuchtigkeit und Temperatur); Somneo-Licht- und Offset-Automationen. Temperatur und Offset erscheinen in mehr als einer Karte. |
| **Bad** (`bad`) | Klima mit `climate.raumkl_bad_eg`, Feuchtigkeit, Temperatur und Offset; zusätzlich Graph-Darstellung. |

### Untergeschoss

| Ansicht | Hauptbereiche und Schlüssel-Entitäten |
|---|---|
| **Büro Matthias** | Beleuchtung über die Bereiche `test_buro_matthias` und `wohnzimmer_ug_2`; Home-Office-Status, Heizung und Raumklima; Computer-Anlage, Multimedia und Fernseher; Geräte-Tracker und Akkus beider Mobiltelefone; Druckerstatus und Toner; Automationen. Der Multimedia-Schalter und der schwarze Toner-Sensor sind jeweils doppelt eingebunden. |
| **Lounge** | Beleuchtung über `lounge` und `terrasse_ug`; Klima mit `climate.raumkl_lounge`, Temperatur/Feuchtigkeit und Offset; Licht-Automationen sowie Wandtaster-Batterie. |
| **Büro Stefaniya** | Beleuchtung über `buro_stefaniya` und `terrasse_ug`; Klima-/Temperaturkarten referenzieren dieselben Lounge-Entitäten wie die Lounge-Ansicht (`climate.raumkl_lounge`, `sensor.raumth_lounge_*`); Terrassen-Automationen und Wandtaster-Batterie. |
| **Terrasse UG** (`terrasse-ug`) | Beleuchtung über `terrasse_ug`; Außentemperatur, Feuchtigkeit und Batterie; vier Terrassen-Automationen. Ein vierter Abschnitt mit der Überschrift „Neuer Abschnitt“ ist leer. |

### Übersicht

| Ansicht | Hauptbereiche und Schlüssel-Entitäten |
|---|---|
| **Beleuchtung** | Zentrale Steuerung `switch.alle_lichter`; EG- und UG-Lichtschalter; Energie-/Leistungswerte der Wohnzimmer-Multimedia-Steckdose. Badges zeigen Wochentag und Zeit. |
| **Heizung** (`heizung`) | Etagenbereiche mit Raumgruppen (EG: Wohnzimmer, Flur, Schlafzimmer, Bad; UG: Büro/Lounge, Bad, Diele); Klima-Regler, Temperaturen/Feuchtigkeit, Offsets sowie Büro-Heizungsstatus, Solltemperatur und berechnete Heizzeiten. Der UG-Bereich bündelt 26 verschiedene Entitäten. Ein dritter Abschnitt ist leer und unbeschriftet; `sensor.thermometer_buro_matthias_temperatur` kommt in mehreren Karten vor. |
| **Auto** (`auto`) | ID.7-Steuerung: 7 Lade-/Klima-/Schloss-Schalter, 35 Telemetrie- und Status-Entitäten, 11 Einstellungen sowie 10 API-/Verbindungs-/Diagnose-Entitäten. Dazu `update.volkswagen_connect_update`. Ein leerer Abschnitt „Neuer Abschnitt“ steht am Anfang. Unter den Diagnose-Entitäten befindet sich `sensor.id_7_api_token`; diese Dokumentation enthält keine Sensorwerte. |
| **Dokumentation** (`dokumentation`) | Eine Section „Systemdokumentation“ mit einer Markdown-Karte; keine direkt referenzierten Entitäten. |

## Optimierungs-Vorschläge

Die Vorschläge beruhen auf der ausgelesenen Karten- und Entitätenstruktur. Eine gerenderte Bildschirmansicht wurde nicht ausgewertet; die tatsächliche Wirkung von Abständen, Umbrüchen und Kartenhöhen sollte insbesondere auf Mobilgeräten geprüft werden.

### KISS – Einfachheit und Fokus

- Leere Platzhalter entfernen oder erst dann befüllen: „Neuer Abschnitt“ auf Terrasse UG und Auto sowie der leere, unbeschriftete Abschnitt in Heizung.
- Doppelungen innerhalb eines Dashboards bereinigen: den Multimedia-Schalter und Toner-Sensor im Büro Matthias sowie Schlafzimmer-Temperatur und Offset. Wenn die Wiederholung bewusst für verschiedene Abläufe gedacht ist, sollte sie klar benannt sein.
- Die Auto-Ansicht auf tägliche Aktionen reduzieren: Laden, Ladezustand, Reichweite und Tür-/Fensterstatus nach vorn; selten verwendete Einstellungen und Diagnosewerte in einen getrennten Bereich oder eine Unteransicht verschieben.
- In der Büro-Stefaniya-Ansicht prüfen, ob die Lounge-Klimaentitäten beabsichtigt sind. Falls ja, die gemeinsame Nutzung deutlich benennen; andernfalls die richtigen Raum-Entitäten zuordnen.
- Einfache Standardkarten und Sections beibehalten. Für die bestehenden Funktionen ist anhand der Konfiguration kein Bedarf an zusätzlichen Karten-Ressourcen erkennbar.

### CAVAMAN – Visuelle Hierarchie und Bedienbarkeit

- Häufig genutzte Aktionen und schnelle Zustände zuerst platzieren: Licht, Raumtemperatur und Heizungsstatus vor Automationen, Batterien und Diagnoseinformationen.
- Im Wohnzimmer-Dashboard die vier Badges (Büro-Fahrzeiten und Büroklima) auf Relevanz für die Wohnzimmeransicht prüfen. Für eine schnelle Erfassung sollten Badges vor allem die Zustände des jeweiligen Raums zeigen.
- Die Heizungsansicht in klar erkennbare Raumgruppen mit gleichbleibender Reihenfolge gliedern: Ist-/Solltemperatur und Regler zusammen, Zusatzsensoren danach. Die große UG-Gruppe mit 26 Entitäten sollte in unmittelbar bedienbare Raumsteuerung und ergänzende Mess-/Zeitinformationen aufgeteilt werden.
- Die Auto-Ansicht nach Aufgaben statt nach technischen Entity-Gruppen ordnen: **Fahren/Sicherheit**, **Laden**, **Klima** und zuletzt **Technik/Diagnose**. Derzeit tragen mehrere Sections denselben Titel „ID.7“, was ihre Funktion auf einen Blick nicht unterscheidet.
- Raumansichten mit konsistenten Überschriften und Begriffen versehen; „Automatitionen“, „Neuer Abschnitt“ und unterschiedliche Raum-/Gerätenamen erschweren das Scannen.
- `max_columns` pro Ansicht bewusst auf die jeweilige Informationsdichte abstimmen und auf schmalen Displays prüfen. Die Sections passen sich an die verfügbare Breite an; eine Begrenzung auf 3 oder 4 Spalten sollte daher eine gezielte Dichteentscheidung sein.

### PONYTAIL – YAML-Sauberkeit, Performance und visuelle Harmonie

- Die drei statischen Dashboards nutzen den Sections-Aufbau mit wiederkehrenden `grid`-/`heading`-Mustern. Diese einfache Struktur beibehalten und wiederkehrende Raumkonventionen (Titel, Klima-Reihenfolge, Sensoren) vereinheitlichen, statt zusätzliche Verschachtelung einzuführen.
- Die Konfiguration ist Storage-basiert, nicht YAML-basiert. Änderungen daher über den Home-Assistant-Dashboard-Editor oder einen dafür vorgesehenen API/MCP-Weg durchführen; keine `.storage`-Dateien manuell bearbeiten.
- Keine Templates oder Custom Cards nur zur vermeintlichen Wiederverwendung ergänzen: Es sind keine zusätzlichen Lovelace-Ressourcen registriert. Wiederkehrende Standardkarten reichen für die vorhandenen Muster aus; berechnete Inhalte nur bei einem konkreten Bedarf bündeln.
- Doppelte Entity-Referenzen und große, flache Entity-Mengen reduzieren. Das macht Konfiguration und Wartung übersichtlicher; besonders die 35 Telemetrie-Karten der Auto-Ansicht sollten auf tatsächlich benötigte Zustände begrenzt werden.
- Technische/diagnostische Entitäten klar von der normalen Bedienoberfläche trennen. Insbesondere `sensor.id_7_api_token` nicht als alltägliche Statuskarte präsentieren; prüfen, ob diese Entität überhaupt in einem für normale Nutzer sichtbaren Dashboard benötigt wird.
- Einheitliche Section-Titel und sinnvolle `max_columns`-Werte über ähnliche Raumansichten hinweg verwenden. Das verbessert Wartbarkeit und ein ruhigeres, konsistentes Erscheinungsbild.
