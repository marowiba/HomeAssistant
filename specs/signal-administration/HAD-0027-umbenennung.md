# HAD-0027: Umbenennung Allow List, Audit Log, Event Log

## Ziel

Navigation und Seitenüberschriften verwenden einheitlich die englischen
Bezeichnungen „Allow List“, „Audit Log“ und „Event Log“.

## Ausgangslage

- Die Navigation und die Seitentitel verwenden „Allowlist“, „Audit-Log“ und
  „Ereignislog“.
- Das Benutzerhandbuch verwendet dieselben Bezeichnungen.
- URLs, Routen und CSS-Klassen sind bereits englisch und bleiben unverändert.

## Umsetzung

### S1: Oberfläche

- `NAV` in `templates.py`: „Allow List“, „Event Log“, „Audit Log“.
- Seitentitel: `allowlist_page` → „Allow List“, `events_page` → „Event Log“,
  `audit_page` → „Audit Log“.
- Überschriften: „Allow List“, „Audit Log“.
- Detailseite: Seitentitel „Event-Detail“ statt „Ereignis-Detail“.
- Kennzahl im Dashboard: „Allow-List-Einträge“.

### S2: Dokumentation

- `docs/signal-admin-benutzerhandbuch.md` verwendet die neuen Bezeichnungen in
  Navigation, Überschriften und Verweisen.

### S3: Unveränderte Bezeichner

- Routen `/allowlist`, `/events`, `/audit`, CSS-Klassen, Formularfelder,
  Konfigurationsschlüssel und Audit-Aktionen bleiben unverändert.
- Die deutschen Fließtexte („Ereignis löschen“, „Einträge“) bleiben erhalten;
  umbenannt werden nur die drei Produktbezeichnungen.

## Entscheidungen

- **E1:** Die drei Bezeichnungen werden englisch geführt, weil sie Produkt- und
  Navigationsnamen sind. Die Bedienhinweise bleiben deutsch.
- **E2:** „Event-Detail“ wird mit umbenannt, damit die Unterseite zur
  Navigation passt.
- **E3:** Keine Aliase oder Weiterleitungen für die alten Bezeichnungen, weil
  nur Texte und keine URLs betroffen sind.

## Verifikation

- Navigation und Seitentitel zeigen „Allow List“, „Audit Log“, „Event Log“.
- Das Handbuch verwendet dieselben Bezeichnungen.
- Tests prüfen die neuen Titel und Überschriften.
- 248 Tests grün, 100 % Zeilenabdeckung in `signal-admin/signal_admin`.
