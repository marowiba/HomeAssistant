# Proposal: Home-Assistant-Dashboards zentralisieren

## Management Summary

Die tägliche Bedienung verteilt sich derzeit auf drei Storage-Dashboards: **Übersicht** mit vier Ansichten sowie **Erdgeschoss** mit sechs und **Untergeschoss** mit vier Ansichten. Dadurch muss man für Raumfunktionen zwischen Dashboards und anschließend zwischen deren Ansichten wechseln. Die Übersichtsansicht enthält bereits zentrale Beleuchtungs-, Heizungs- und Fahrzeugbereiche, während die Etagen-Dashboards parallel Raumsteuerungen, Automationen und Statusinformationen anbieten.

**Kernziel:** „Übersicht“ wird zum einzigen täglichen Einstieg. Die Inhalte werden dort nach Aufgaben sortiert und auf sechs Hauptansichten gebündelt:

1. **Zuhause** – wichtigste Statusinformationen und eine zentrale Schnellaktion
2. **Licht** – zentrale Beleuchtung nach Etage
3. **Klima** – Heizungssteuerungen und Raumklima für beide Etagen
4. **Erdgeschoss** – nur raumspezifische Inhalte, die nicht schon in Licht oder Klima liegen
5. **Untergeschoss** – nur raumspezifische Inhalte, die nicht schon in Licht oder Klima liegen
6. **Auto** – Fahrzeugfunktionen und relevante Fahrzeugzustände

Selten benötigte Geräte- und Systeminformationen sowie die bestehende Dokumentation werden in eine erreichbare **System-Unteransicht** verschoben. Die Etagen-Dashboards bleiben während der Einführung unverändert als Rückfallmöglichkeit erhalten und werden erst nach erfolgreicher Prüfung aus der Seitenleiste genommen. Das ist ein Architekturvorschlag, keine Änderung an Home Assistant.

## Ist-Analyse vs. Soll-Architektur

### Ist-Zustand

| Bereich | Aktuelle Struktur | Konsequenz im Alltag |
|---|---|---|
| **Übersicht** | Beleuchtung, Heizung, Auto, Dokumentation | Gute Basis, aber weder alle Räume noch alle Etagenfunktionen sind hier vollständig auffindbar. |
| **Erdgeschoss** | Küche, Wohnzimmer, Terrasse EG, Straße, Schlafzimmer, Bad | Raumfunktionen, Klima, Automationen und Geräte sind auf eigene Ansichten verteilt. |
| **Untergeschoss** | Büro Matthias, Lounge, Büro Stefaniya, Terrasse UG | Raum- und Geräteinformationen liegen zusätzlich in einem anderen Dashboard. |
| **Wiederholungen/Platzhalter** | Zum Beispiel wiederholte Temperatur-/Offset-Referenzen, doppelte Geräte im Büro Matthias und leere Abschnitte | Mehr Inhalt und Scrollen, ohne dass dadurch die Navigation eindeutiger wird. |
| **Auto** | Mehrere Abschnitte mit demselben Titel und viele Status-/Diagnose-Entitäten | Häufig benötigte Fahrzeugaktionen konkurrieren mit umfangreichen technischen Details. |

Die Dashboards wurden über MCP als **Storage-Konfiguration** ausgelesen. Es handelt sich nicht um YAML-Dashboards mit gepflegten Quelldateien. Die vorgeschlagenen YAML-Ausschnitte unten zeigen daher die Lovelace-Struktur, sind aber **kein direkt einzuspielender vollständiger Export**.

### Soll-Architektur und Inhaltszuordnung

| Neue Ansicht in „Übersicht“ | Übernommene Inhalte | Abgrenzung gegen Redundanz |
|---|---|---|
| **Zuhause** | Kurze Statusleiste, zum Beispiel die vorhandenen Fahrzeit-Sensoren `sensor.fahrzeit_buro` und `sensor.fahrzeit_stefa`; zentrale Aktion `switch.alle_lichter` | Keine zweite Sammlung aller Raumlichter oder Klima-Detailkarten. Auf der Startansicht nur den Überblick und die eine festgelegte Schnellaktion zeigen. |
| **Licht** | Beleuchtung der Übersicht plus die Lichtschalter aus Küche, Wohnzimmer, Straße, Terrasse EG, Lounge, Büros und Terrasse UG; nach Erdgeschoss und Untergeschoss gruppiert | Jedes einzelne Licht erhält hier genau einen primären Bedienort. Der globale Schalter bleibt auf „Zuhause“; keine erneute Kopie in der Raumübersicht. |
| **Klima** | Heizungsansicht plus Klima- und Temperaturinformationen aus beiden Etagen-Dashboards | Räume nach Etage gruppieren. Pro Raum Soll-/Istwert und Regler beieinander; zusätzliche Sensoren und Heizzeit-Details nachrangig. Keine zweiten Klima-Regler in den Etagenansichten. |
| **Erdgeschoss** | Küchen-Automationen und Batterie; Wohnzimmer-Multimedia und lokale Automationen; Terrassen-Automationen; Straßen-/Wetterinformationen; Schlafzimmer-Wecker, Somneo-Status und zugehörige Automationen | Lichtsteuerung (auch `light.somneo_light`) und Raumklima bleiben in den zentralen Ansichten „Licht“ bzw. „Klima“. Raumansichten behalten nur ihren exklusiven Kontext. |
| **Untergeschoss** | Home-Office-Status, Computer-/Multimedia-Geräte, Lounge- und Terrassen-Automationen, Tasterbatterien sowie lokale Raumzustände | Geteilte Lounge-Klimaentitäten nur einmal in „Klima“ zeigen. Vor der Migration prüfen, ob die Klima-Karten im Büro Stefaniya absichtlich auf Lounge-Entitäten zeigen. |
| **Auto** | Bestehende ID.7-Steuerungen und Statusinformationen | Häufige Aktionen und Laden zuerst; selten genutzte Konfiguration und Diagnose deutlich abgesetzt bzw. in „System“ verschieben. Nicht benötigte Entitäten weglassen. |
| **System-Unteransicht** | Drucker- und Telefonstatus, technische Diagnose und bisherige Markdown-Dokumentation | Über einen klaren Einstieg erreichbar, aber kein prominenter täglicher Hauptreiter. Diagnoseinformationen nicht mit Alltagssteuerungen vermischen. |

Die Grundregel lautet **eine führende Ansicht pro Steuerungsaufgabe**. Ein kompakter Status darf auf „Zuhause“ wiederholt werden, wenn er dort den Überblick verbessert; dieselbe steuerbare Karte sollte nicht zusätzlich an mehreren Stellen gepflegt werden.

## Konkreter Umsetzungsplan / YAML-Strukturvorschlag

### Reihenfolge der Umsetzung

1. **Bestand sichern und Entitäten prüfen.** Vorhandene Storage-Konfigurationen exportieren bzw. ihre aktuellen `config_hash`-Werte erfassen. Doppelte Entitäten und die Zuordnung der Lounge-/Büro-Stefaniya-Klimaentitäten fachlich verifizieren; Entity-IDs nicht erraten oder umbenennen.
2. **Übersicht neu gliedern.** Sechs Hauptansichten in der Reihenfolge **Zuhause → Licht → Klima → Erdgeschoss → Untergeschoss → Auto** anlegen. Raumansichten aus den bisherigen Etagen-Dashboards aufteilen und in die Zielansichten verschieben.
3. **Details konsolidieren.** Leere Abschnitte wie „Neuer Abschnitt“ und unbeschriftete Platzhalter entfernen. Doppelte Karten nach Prüfung bereinigen. In Auto die gleichnamigen „ID.7“-Abschnitte aussagekräftig benennen und nur relevante Statuswerte sichtbar lassen.
4. **Systeminformationen auslagern.** Drucker, Mobiltelefone, Diagnose und die bisherige Dokumentation in einer `subview: true`-Ansicht gruppieren. Von „Zuhause“ oder „Auto“ einen bewussten Einstieg dorthin anbieten.
5. **Prüfen, dann Navigation umstellen.** Auf Mobilgerät und Desktop testen: Bedienbarkeit, Sichtbarkeit wichtiger Zustände, alle Aktionen, Ansichtspfade und Berechtigungen. Die Etagen-Dashboards erst nach Abnahme mit `show_in_sidebar: false` aus der Seitenleiste nehmen; nicht löschen. Bei Problemen bleiben sie als Rückfall erreichbar.

Da die vorhandenen Dashboards im Storage-Modus liegen, sollte eine Umsetzung über den Home-Assistant-Dashboard-Editor oder einen passenden API/MCP-Schreibweg erfolgen. **Nicht** `.storage`-Dateien manuell bearbeiten. Bei API-Änderungen die aktuelle Konfiguration und ihren Hash unmittelbar vorher erneut lesen und Änderungen gegen diesen Stand absichern.

### Beispiel für Ansichten und Karten

Die folgenden Ausschnitte illustrieren drei Zielansichten und verwenden bereits vorhandene Entitäten. Die Raumlisten sind exemplarisch; vor einer vollständigen Migration müssen alle Karten aus dem Live-Stand zugeordnet und geprüft werden.

```yaml
views:
  - title: Zuhause
    path: zuhause
    type: sections
    max_columns: 3
    badges:
      - type: entity
        entity: sensor.fahrzeit_buro
        name: Büro
      - type: entity
        entity: sensor.fahrzeit_stefa
        name: Stefaniya
    sections:
      - type: grid
        cards:
          - type: heading
            heading: Schnellzugriff
            heading_style: title
          # Der globale Lichtschalter hat hier seinen einzigen Bedienort.
          - type: tile
            entity: switch.alle_lichter
          - type: button
            name: System
            icon: mdi:cog
            tap_action:
              action: navigate
              navigation_path: /lovelace/system

  - title: Licht
    path: licht
    type: sections
    max_columns: 3
    sections:
      - type: grid
        cards:
          - type: heading
            heading: Erdgeschoss
            heading_style: title
          - type: tile
            entity: switch.kuchenlicht_schalter
          - type: tile
            entity: switch.stehlampe_1_schalter
          - type: tile
            entity: switch.stehlampe_2_schalter
          - type: tile
            entity: switch.stehlampe_3_schalter
      - type: grid
        cards:
          - type: heading
            heading: Untergeschoss
            heading_style: title
          - type: tile
            entity: switch.deckenlicht_lounge_schalter
          - type: tile
            entity: switch.deckenlicht_buro_matthias_schalter
          - type: tile
            entity: switch.deckenlicht_buro_stefaniya_schalter

  - title: Klima
    path: klima
    type: sections
    max_columns: 3
    sections:
      - type: grid
        cards:
          - type: heading
            heading: Erdgeschoss · Wohnzimmer
            heading_style: title
          - type: tile
            entity: climate.raumkl_wohnzimmer_eg
          - type: tile
            entity: sensor.raumth_wohnzimmer_eg_temperature
          - type: tile
            entity: sensor.raumth_wohnzimmer_eg_humidity
      - type: grid
        cards:
          - type: heading
            heading: Untergeschoss · Lounge
            heading_style: title
          - type: tile
            entity: climate.raumkl_lounge
          - type: tile
            entity: sensor.raumth_lounge_temperature
          - type: tile
            entity: sensor.raumth_lounge_humidity

  - title: System
    path: system
    type: sections
    subview: true
    sections:
      - type: grid
        cards:
          - type: heading
            heading: Geräte und Dokumentation
            heading_style: title
          # Drucker-, Telefon- und Dokumentationskarten hier bündeln.
```

In den vollständigen Ansichten **Erdgeschoss** und **Untergeschoss** werden `heading`-Karten und Sections nach Raum bzw. Aufgabe gegliedert. Dort verbleiben zum Beispiel Schlafzimmer-Wecker, Terrasse-Automationen, Wetter und Mediengeräte – nicht aber weitere Kopien der zentralen Licht- oder Klimasteuerungen.

### Struktur- und Performance-Leitplanken

- `sections` und `grid` sind hier die nativen Lovelace-Ansichts-/Abschnittslayouts; sie erfordern keine Custom Card. Für die bestehenden Inhalte sind zusätzliche HACS-Karten nicht nötig.
- Sections direkt und flach halten. Die aktuelle Struktur kann `type: grid`-Abschnitte mit `cards` und `heading`-Karten abbilden; weitere verschachtelte Grid-Karten nur einsetzen, wenn ein festes Kartenraster einen konkreten Vorteil bietet.
- `tile`, `entities`, `heading` und bei Bedarf `markdown` als Standardkarten bevorzugen. Conditional Cards nur dort einsetzen, wo ein Inhalt tatsächlich abhängig von einem Zustand ein- oder ausgeblendet werden soll – nicht als Ersatz für klare Navigation.
- Kein Template oder Custom-Card-Framework nur für vermeintliche Wiederverwendung einführen. Lovelace-Konfigurationen des Storage-Dashboards sind keine modularen YAML-Quelldateien mit frei pflegbaren `!include`-Bausteinen. Wiederverwendung zunächst durch einheitliche, einfache Kartenmuster erreichen.
- Die Anzahl der sichtbaren Entitäten begrenzen. Besonders die Auto-Ansicht (aktuell viele Telemetrie- und Diagnosekarten) auf Bedienung, Laden und relevante Sicherheit reduzieren. Technische Diagnose gehört in die System-Unteransicht.

## Vorteile nach KISS, CAVAMAN & PONYTAIL

### KISS

- Ein täglicher Einstieg statt Wechsel zwischen „Übersicht“, „Erdgeschoss“ und „Untergeschoss“.
- Etagenansichten bündeln Raumfunktionen, ohne für jeden Raum einen eigenen Hauptreiter anzulegen.
- Leere Abschnitte, redundante Karten und selten benötigte Diagnosewerte werden entfernt oder ausgelagert.
- Ein klarer Zuständigkeitsort für Licht, Klima und Fahrzeugfunktionen vereinfacht spätere Änderungen.

### CAVAMAN

- Die Startansicht zeigt wenige, schnell erfassbare Informationen statt einer verkleinerten Kopie aller Detailansichten.
- Hauptreiter folgen Aufgaben und mentalen Modellen: Zuhause, Licht, Klima, Etagen und Auto.
- Innerhalb einer Raumgruppe stehen zusammengehörige Bedienung und Status beieinander; seltene Informationen folgen nachrangig.
- Eine Prüfung auf Telefon und Desktop stellt sicher, dass Reihenfolge, Informationsdichte und Abschnittsbreite zur tatsächlichen Nutzung passen.

### PONYTAIL

- Native, einheitliche Sections- und Kartenmuster sind leichter lesbar und wartbar als unnötige Verschachtelung oder zusätzliche Custom Cards.
- Weniger Karten und keine doppelt gepflegten Steuerungen halten die Konfiguration übersichtlich und reduzieren visuelle sowie wartungsbezogene Last.
- Die Storage-Konfiguration wird über den vorgesehenen Home-Assistant-Weg gepflegt; Änderungen lassen sich vor der Umsetzung sichern und gegen einen aktuellen Konfigurationsstand absichern.
- Die Trennung von Alltag und Systemdiagnose schafft eine klare Struktur, ohne technische Detailinformationen zu verlieren.
