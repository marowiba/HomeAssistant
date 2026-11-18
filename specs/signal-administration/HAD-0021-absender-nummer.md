# HAD-0021: Absender-Nummer nicht als UUID anzeigen

## Ziel

Die Ereignis-Detailansicht zeigt im Feld `Absender-Nummer` nur eine echte
Telefonnummer. Eine UUID erscheint ausschließlich im Feld `Absender-UUID`.

## Ausgangslage

- Signal liefert in `sourceNumber` eine UUID, wenn der Absender die
  Nummernweitergabe abgeschaltet hat.
- `event_detail_page` zeigt den Wert unverändert als Nummer an.
- Die gespeicherten Ereignisse bleiben unverändert.

## Umsetzung

### S1: Erkennung

- `templates.UUID_PATTERN` prüft das Muster
  `8-4-4-4-12` Hex-Zeichen.
- `_is_uuid(value)` erkennt nur Textwerte, die vollständig dem Muster
  entsprechen.

### S2: Anzeige

- Sieht `sender_number` wie eine UUID aus, zeigt das Feld `Absender-Nummer`
  den Wert `-`.
- Ist `sender_uuid` leer, übernimmt das Feld `Absender-UUID` die UUID aus
  `sender_number`. Damit geht die Information nicht verloren.
- Ist `sender_uuid` gesetzt, bleibt dieser Wert maßgeblich.
- Fehlt beides, zeigt `Absender-Nummer` den Wert `-`.

## Entscheidungen

- **E1:** Die Erkennung erfolgt im Rendering, nicht beim Schreiben. Alte
  Ereignisse werden dadurch ebenfalls korrekt dargestellt.
- **E2:** Die UUID wird nicht verworfen, sondern in das dafür vorgesehene
  Feld verschoben.
- **E3:** Das Muster ist bewusst streng; Nummern mit Bindestrichen werden
  nicht fälschlich als UUID erkannt.

## Verifikation

- Anzeige mit Nummer, mit UUID in `sender_number`, mit beiden Werten und ohne
  Absender.
- Die UUID erscheint genau einmal, im Feld `Absender-UUID`.
- 264 Tests grün, 100 % Zeilenabdeckung in `signal-admin/signal_admin`.
