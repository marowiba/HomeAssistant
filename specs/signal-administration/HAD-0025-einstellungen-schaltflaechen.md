# HAD-0025: Einstellungen – Schaltflächen und Seitenlayout

## Ziel

Die Einstellungsseite ist nach UI/UX-Gesichtspunkten gestaltet: zwei klar
getrennte Bereiche, natürliche Schaltflächenbreiten, einheitliche Ausrichtung
und nachvollziehbare Aktionsgruppen. Volle Breite wird vermieden.

## Ausgangslage

- Die vier Aktionen standen in getrennten Blöcken mit unterschiedlicher
  Ausrichtung.
- Eine erste Umsetzung nutzte `btn-block` über die volle Panelbreite. Das ist
  auf dem Desktop kein gutes Layout und wurde im UAT verworfen.

## Umsetzung

### S1: Seitenraster

- `.settings-grid` ordnet „Aufbewahrung“ und „Sicherung“ auf dem Desktop
  zweispaltig an (`repeat(auto-fit, minmax(320px, 1fr))`), auf kleinen
  Bildschirmen einspaltig.
- Jeder Bereich bleibt ein eigenes Panel mit Überschrift und kurzem
  Erklärungstext.

### S2: Aktionszeilen

- `.form-row` stellt Eingabe und Schaltfläche nebeneinander, bricht bei Platz-
  mangel um.
- `.form-row .btn` behält seine natürliche Breite (`min-width: 150px`), keine
  volle Breite.
- `.form-row-between` verteilt Hinweistext und Aktion, `.form-row-end`
  richtet die Wiederherstellen-Aktion rechts aus.
- `.panel-divider` trennt die beiden Aktionen innerhalb eines Bereichs.
- `.form-hint` liefert kurze Erklärungen ohne die Aktionszeile zu sprengen.

### S3: Mobile

- `.form-row` wird einspaltig; Schaltflächen bleiben natürliche Breite und
  werden links ausgerichtet.
- `.settings-grid` wird einspaltig.

## Entscheidungen

- **E1:** Natürliche Schaltflächenbreite statt `btn-block`. Aktionen bleiben
  als Aktion erkennbar und dominieren die Seite nicht.
- **E2:** Zwei Bereiche mit je zwei Aktionen. Das entspricht der fachlichen
  Gruppierung und reduziert die visuelle Last.
- **E3:** Keine Verhaltensänderung; Formulare, Ziele und CSRF-Felder bleiben
  unverändert.

## Verifikation

- Vier `form-row`-Blöcke, kein `btn-block`, kein `settings-action`.
- Zwei Panels in `settings-grid`, je zwei Aktionen.
- 264 Tests grün, 100 % Zeilenabdeckung in `signal-admin/signal_admin`.
- UAT: Schaltflächen in natürlicher Breite, sauber ausgerichtet, mobil
  einspaltig.
