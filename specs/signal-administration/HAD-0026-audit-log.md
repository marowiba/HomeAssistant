# HAD-0026: Audit Log – sortierbar und verständlich

## Ziel

Die Spalten des Audit Logs sind sortierbar, der Integritätsstatus ist
erklärt, Aktionen tragen verständliche Bezeichnungen und eine Legende
erklärt Hash und Prüfkette.

## Ausgangslage

- Die Tabelle zeigt die Einträge in ID-absteigender Reihenfolge ohne
  Sortierlinks.
- „Kette unversehrt“ und die rohen Aktionsnamen sind für Anwender schwer zu
  deuten.

## Umsetzung

### S1: Sortierung

- `sort` und `dir` mit weißer Liste: `id`, `ts`, `actor`, `action`, `target`,
  `detail`, `hash`.
- Standard ist `ts` absteigend.
- Ungültige Werte fallen auf den Standard zurück.
- Die Sortierung erfolgt stabil auf der Liste aus `AuditLog.list()`.
- Der aktive Spaltenkopf zeigt ▲ oder ▼.

### S2: Verständliche Inhalte

- Aktionen werden über `AUDIT_ACTION_LABELS` übersetzt, etwa
  `allowlist.add` → „Allow-List-Eintrag angelegt“.
- Unbekannte Aktionen bleiben im Original erhalten.
- Bei intakter Kette erscheint der Satz „Die Einträge sind unverändert; die
  Prüfkette ist vollständig.“
- Bei gebrochener Kette erscheint „Mindestens ein Eintrag wurde nachträglich
  verändert.“
- Eine Legende erklärt Hash und Prüfkette.

## Entscheidungen

- **E1:** Sortierung über Query-Parameter wie im Event Log, damit sie ohne
  JavaScript funktioniert und in Links erhalten bleibt.
- **E2:** Die Übersetzung ist eine reine Anzeige; gespeicherte Aktionen und
  die Hash-Kette bleiben unverändert.
- **E3:** Die Legende steht unter der Tabelle und erklärt nur die beiden
  Begriffe, die Anwender sonst nicht einordnen können.

## Verifikation

- Standardreihenfolge Zeit absteigend.
- Sortierung nach Akteur auf- und absteigend, Sortierung nach Hash.
- Ungültige Werte fallen auf den Standard zurück.
- Neue Texte und Sortierlinks im HTML.
- 264 Tests grün, 100 % Zeilenabdeckung in `signal-admin/signal_admin`.
