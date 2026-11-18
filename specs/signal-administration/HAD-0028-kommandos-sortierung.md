# HAD-0028: Kommandos nach Kommando und Entität sortierbar

## Ziel

Die Kommando-Ansicht unter `/commands` lässt sich nach Kommando und Entität
auf- und absteigend sortieren. Standard bleibt die Konfigurationsreihenfolge.

## Ausgangslage

- Die Tabelle zeigt die Kommandos in der Reihenfolge der Konfiguration.
- Die Entität ist nur als Eingabefeld in der Bearbeitungszeile sichtbar.

## Umsetzung

### S1: Sortierung

- `sort` und `dir` mit weißer Liste: `text`, `entity`.
- Ohne `sort` bleibt die Konfigurationsreihenfolge erhalten.
- Sortiert wird stabil und ohne Beachtung der Groß-/Kleinschreibung.
- Ungültige Werte fallen auf die Konfigurationsreihenfolge zurück.
- Der aktive Spaltenkopf zeigt ▲ oder ▼.

### S2: Tabelle

- Neue Spalte „Entität“ zeigt `entity_id` als Text, leer als `-`.
- Die Spaltenköpfe „Kommando“ und „Entität“ sind Sortierlinks auf
  `/commands`.
- Die Bearbeitungsformulare bleiben unverändert in der ersten Spalte.

## Entscheidungen

- **E1:** Die Entität erhält eine eigene Anzeigespalte, weil sie sonst nicht
  als Spalte sortierbar wäre. Das Formular bleibt unverändert.
- **E2:** Standard ist bewusst keine Sortierung, damit die gewohnte
  Konfigurationsreihenfolge erhalten bleibt.
- **E3:** Sortierung über Query-Parameter, damit sie ohne JavaScript
  funktioniert.

## Verifikation

- Beide Spalten in beiden Richtungen.
- Ungültige Werte ändern die Reihenfolge nicht.
- Sortierlinks und Entitätsspalte im HTML.
- 264 Tests grün, 100 % Zeilenabdeckung in `signal-admin/signal_admin`.
