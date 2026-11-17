# Spezifikationen und Solution Designs

Dieses Verzeichnis enthält die fachlichen Designs, gegliedert nach Epic. Die
Epics entsprechen der Spalte `Feature` in `backlog.md`.

## Struktur

```text
specs/
  <epic>/
    design.md              Epic-Design: Ziel, Architektur, Abgrenzung
    HAD-xxxx-<thema>.md    Solution Design je Ticket
    <weitere>.md           Ergänzende Dokumente, z. B. Analyse oder Proposal
```

## Regeln

- Ein Unterordner pro Epic, Name in Kleinschreibung mit Bindestrichen.
- Umlaute werden transliteriert: `ä` zu `ae`, `ö` zu `oe`, `ü` zu `ue`, `ß` zu
  `ss`. Beispiel: „Codequalität und SAST" wird zu `codequalitaet-sast`.
- `design.md` beschreibt das Epic übergreifend und ist die Referenz für alle
  Tickets dieses Epics.
- Ticket-Designs beginnen mit der Ticket-ID, damit sie sortierbar und eindeutig
  sind.
- Ergänzende Dokumente behalten einen sprechenden Namen, etwa `analysis.md` für
  eine Bestandsaufnahme oder `proposal.md` für ein noch nicht beschlossenes
  Konzept.
- Querverweise immer mit vollständigem Pfad ab Repository-Wurzel.
- Bei Widersprüchen gilt: Ticket in `backlog.md` vor Solution Design vor
  Epic-Design.

## Bestand

| Epic | Ordner | Dateien |
| :--- | :--- | :--- |
| Signal-Integration | `specs/signal-integration/` | `design.md`, `HAD-0001-empfangsdienst.md`, `HAD-0002-allowlist-und-chatlog.md`, `HAD-0003-kommandoerkennung.md`, `HAD-0004-home-assistant-anbindung.md` |
| Dashboards | `specs/dashboards/` | `analysis.md`, `proposal.md` |

`specs/dashboards/` ist eine **bewusste Ausnahme** von der Regel „ein Ordner pro
Feature". Die Dateien entstanden vor der Einführung des Backlogs, und es gibt
kein Feature `Dashboards`. Der Ordner enthält eine Bestandsaufnahme und ein
Konzept, aber noch kein beschlossenes Design. Der Name ist bereits so gewählt,
dass er ohne Umbenennung zum Epic werden kann, sobald ein entsprechendes Feature
mit Tickets angelegt wird.

## Noch nicht angelegte Epics

Für diese Epics aus `backlog.md` entsteht der Ordner mit dem ersten Ticket:

| Epic | Tickets |
| :--- | :--- |
| Signal-Administration | HAD-0008 |
| Codequalität und SAST | HAD-0007 |
