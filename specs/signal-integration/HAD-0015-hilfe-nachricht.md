# HAD-0015: Signal-Hilfe-Nachricht mit den unterstützten Kommandos

## Ziel

Auf eine definierte Hilfe-Anfrage antwortet die Bridge mit einer Signal-Nachricht,
die alle unterstützten Kommandos und ihre Bedeutung auflistet. Die Hilfe löst
keine Home-Assistant-Aktion aus und wird nur an freigegebene Absender gesendet.

## Kommando

- `Hilfe` und `?`, unabhängig von Groß-/Kleinschreibung und Leerraum.
- Ergebnis: `help`.
- `HO Hilfe` ist ausdrücklich **kein** Kommando und bleibt ohne Antwort.

## Ablauf

1. `command_parser.parse_command` erkennt `hilfe` und `?` und liefert `help`.
2. `bridge.build_record` markiert das Kommando als `actionable`, sofern der
   Absender freigegeben ist.
3. `ha_client.perform_action` führt für `help` keine Aktion aus
   (`attempted=False`, `detail="keine Aktion"`).
4. `signal_client.build_reply` erzeugt die Hilfe aus
   `command_parser.build_help_text()`.
5. Die Antwort geht an den Absender.

## Hilfe-Text

Der Text wird aus der festen Kommandoliste in
`command_parser.COMMAND_DESCRIPTIONS` erzeugt. Bei HAD-0010 (eigene Kommandos)
wird die Liste aus der Konfiguration abgeleitet.

## Sicherheit

- Nur freigegebene Absender erhalten eine Antwort.
- Keine Home-Assistant-Aktion, keine freien Dienste oder Templates.
- Das Kommando lässt sich in der Administration ein-/ausschalten.

## Verifikation

- Unit-Tests für Parser, Bridge, HA-Client, Signal-Client und Administration.
- 100 % Zeilenabdeckung, Sonar 0 Issues.
- Deployment auf `srv001` am 2026-11-18 geprüft. Die installierte
  Kommandotabelle lautet `['?', 'hilfe', 'ho m an', 'ho m aus', 'ho m status']`;
  `parse_command` liefert `help` für `Hilfe` und `?` sowie `None` für
  `HO Hilfe`. Signal-Test bestätigt: `Hilfe` und `?` antworten, `HO Hilfe`
  bleibt stumm.
- Hinweis: Ein zuvor ausgeliefertes Archiv war vor der letzten Parser-Änderung
  gebaut worden. Deshalb ersetzt das Deployment die vier Python-Dateien jetzt
  einzeln per `install` und entfernt `__pycache__`, statt sich auf das
  Überschreiben per `tar` zu verlassen.
