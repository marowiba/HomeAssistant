"""HAD-0003: Erkennung der Home-Office-Kommandos.

Es werden ausschliesslich die drei definierten Kommandos akzeptiert. Die
Auswertung ignoriert Gross- und Kleinschreibung sowie zusaetzlichen Leerraum.
Unbekannte, abweichende oder mehrdeutige Texte ergeben None und loesen damit
keine Aktion aus.
"""

from __future__ import annotations

COMMAND_ON = "on"
COMMAND_OFF = "off"
COMMAND_STATUS = "status"

COMMANDS: dict[str, str] = {
    "ho m an": COMMAND_ON,
    "ho m aus": COMMAND_OFF,
    "ho m status": COMMAND_STATUS,
}


def normalize(text: str | None) -> str | None:
    """Vereinheitlicht Leerraum und Gross-/Kleinschreibung.

    Mehrfache Leerzeichen, Tabulatoren und Zeilenumbrueche werden zu einem
    einzelnen Leerzeichen. Leere Eingaben ergeben None.
    """
    if text is None:
        return None
    collapsed = " ".join(text.split())
    if not collapsed:
        return None
    return collapsed.casefold()


def parse_command(text: str | None) -> str | None:
    """Gibt `on`, `off` oder `status` zurueck, sonst None.

    Die Zuordnung erfolgt ueber exakte Gleichheit nach der Normalisierung.
    Damit sind `HO M AN`, `ho m an` und `Ho M An` gleichbedeutend, waehrend
    `HO M an aus`, `HO M an!` oder `HO M` keine Aktion ausloesen.
    """
    normalized = normalize(text)
    if normalized is None:
        return None
    return COMMANDS.get(normalized)
