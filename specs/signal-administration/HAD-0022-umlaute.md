# HAD-0022: UI-Texte mit korrekten deutschen Umlauten

## Ziel

Alle sichtbaren Texte der Weboberfläche verwenden die korrekte deutsche
Rechtschreibung mit `ä`, `ö`, `ü` und `ß`. Technische Bezeichner bleiben
unverändert.

## Ausgangslage

- `templates.py` und `app.py` verwenden transliterierte Umlaute, etwa
  „zulaessig“, „loeschen“, „Eintraege“, „waehlen“.
- Auch die aus `config_store.py` und `status.py` stammenden Meldungen
  erscheinen als Flash- oder Statusdetail in der Oberfläche und sind
  transliteriert.
- Tests prüfen teilweise auf die transliterierten Texte.

## Umsetzung

### S1: Sichtbare Texte

- `templates.py`: Navigation, Überschriften, Schaltflächen, Bestätigungen,
  Tabellenüberschriften und Hinweise.
- `app.py`: Fehlermeldungen, Flash-Texte und Kennzahlen.
- `config_store.py`: Validierungs- und Ladefehler, die als Flash erscheinen.
- `status.py`: Statusdetails für Signal, Home Assistant und Dienstprüfung.
- Docstrings der betroffenen Module werden mit angepasst.

### S2: Unveränderte Bezeichner

- CSS-Klassen, HTML-Attribute, Formularfeldnamen, Routen, URLs, Dateinamen,
  Konfigurationsschlüssel und Audit-Aktionen bleiben unverändert.
- Python-Bezeichner und JSON-Schlüssel bleiben unverändert.

### S3: Tests

- Tests, die auf transliterierte Texte prüfen, werden auf die korrekte
  Schreibweise umgestellt.
- Zusätzliche Prüfungen decken die neuen Texte ab, etwa „Hinzufügen“,
  „Ausgewählte löschen“, „Integrität“ und „Bereinigung jetzt ausführen“.

## Entscheidungen

- **E1:** Die Rechtschreibung wird direkt in den Quelltexten korrigiert, nicht
  über eine Übersetzungsschicht. Die Oberfläche ist einsprachig.
- **E2:** Fehlertexte aus `config_store.py` und `status.py` zählen zu den
  sichtbaren Texten, weil sie unverändert in der Oberfläche erscheinen.
- **E3:** Technische Bezeichner bleiben unverändert, damit Konfiguration,
  Audit-Kette und Tests stabil bleiben.

## Verifikation

- Keine transliterierten Umlaute mehr in sichtbaren Texten der vier Module.
- Tests prüfen die korrigierten Texte.
- 248 Tests grün, 100 % Zeilenabdeckung in `signal-admin/signal_admin`.
