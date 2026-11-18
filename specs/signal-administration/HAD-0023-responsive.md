# HAD-0023: Responsive Oberfläche für mobile Geräte

## Ziel

Die Weboberfläche ist auf Smartphones und Tablets vollständig bedienbar. Alle
Kacheln, Panels und Tabellen bleiben innerhalb der zulässigen Spaltenbreite.

## Ausgangslage

- Die Sidebar hat eine feste Breite von 240 px und bleibt auf kleinen
  Bildschirmen sichtbar.
- Tabellen mit `min-width: 640px` schoben das gesamte Inhaltsraster über die
  Viewportbreite.
- Kacheln und Inline-Formulare konnten Inhalte über den Rand hinaus drücken.
- Die Oberfläche nutzt kein externes Framework.

## Umsetzung

### S1: Menü

- Der Kopfbereich enthält die Schaltfläche `Menü` mit `data-menu-toggle`,
  `aria-controls="sidebar"` und `aria-expanded`.
- Die Sidebar trägt `id="sidebar"` und `data-sidebar`.
- `admin.js` schaltet `menu-open` am `body`, aktualisiert `aria-expanded` und
  schließt das Menü beim Klick auf einen Navigationseintrag.

### S2: Spaltenbreite

- Unter 720 px:
  - `.content` scrollt nicht mehr horizontal (`overflow-x: hidden`).
  - `.panel` bleibt bei `max-width: 100%` und scrollt breite Tabellen intern
    (`overflow-x: auto`). Die Tabelle verlässt damit nicht mehr die Kachel.
  - `.cards` wird einspaltig, `.card` erhält `min-width: 0`, Kartenwerte
    brechen mit `overflow-wrap: anywhere` um.
  - `.grid-form` und `.settings-grid` werden einspaltig.
  - `.actions` und `.inline-form` stapeln ihre Felder; Eingaben und Selects
    nutzen die volle Kachelbreite.
  - `.detail th` wird auf 40 % Breite gesetzt.
  - Der Kopfbereich wird kompakt: kleinere Marke, Benutzername ausgeblendet.
  - Schaltflächen erhalten mindestens 40 px Höhe.

## Entscheidungen

- **E1:** Tabellen bleiben Tabellen und scrollen innerhalb ihres Panels. Das
  erhält Sortierung und Sammelauswahl.
- **E2:** Kacheln und Panels bekommen `max-width: 100%` und `min-width: 0`.
  Damit respektieren sie die Spaltenbreite, statt sie zu sprengen.
- **E3:** Umsetzung mit CSS und einer kleinen Erweiterung von `admin.js`,
  ohne Framework und ohne zusätzliche Abhängigkeit.

## Verifikation

- Gerenderte Attribute für Viewport, Menü-Schaltfläche und Sidebar.
- `admin.js` enthält die Menü-Logik.
- `admin.css` enthält die Regeln für `overflow-x: hidden`, `settings-grid`,
  `form-row` und die einspaltigen Kacheln.
- 264 Tests grün, 100 % Zeilenabdeckung in `signal-admin/signal_admin`.
- UAT bei 375 px, 768 px und 1280 px: keine horizontale Überbreite, Menü
  bedienbar, Tabellen scrollen in der Kachel.
