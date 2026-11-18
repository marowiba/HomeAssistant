"""HAD-0003/HAD-0010: Erkennung der konfigurierten Signal-Kommandos.

Die Kommandos kommen aus der Konfiguration. Es gibt Literal-Kommandos und
Werte-Kommandos mit dem Platzhalter ``{wert}`` am Ende. Die Auswertung ignoriert
Gross- und Kleinschreibung sowie zusaetzlichen Leerraum.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

VALUE_PLACEHOLDER = "{wert}"

ACTION_ON = "on"
ACTION_OFF = "off"
ACTION_STATUS = "status"
ACTION_SET_VALUE = "set_value"
ACTION_HELP = "help"

ACTIONS = (ACTION_ON, ACTION_OFF, ACTION_STATUS, ACTION_SET_VALUE, ACTION_HELP)
ENTITY_ACTIONS = (ACTION_ON, ACTION_OFF, ACTION_STATUS, ACTION_SET_VALUE)
VALUE_ACTIONS = (ACTION_SET_VALUE,)

# Feste Zuordnung von Entitaets-Domain zu Dienst und Nutzlast-Schluessel.
VALUE_SERVICES: dict[str, tuple[str, str, str]] = {
    "climate": ("climate", "set_temperature", "temperature"),
    "number": ("number", "set_value", "value"),
    "input_number": ("input_number", "set_value", "value"),
}

_VALUE_RE = re.compile(r"^-?\d{1,6}(?:[.,]\d{1,3})?$")


@dataclass(frozen=True)
class Command:
    """Ein konfiguriertes Kommando."""

    id: str
    text: str
    action: str
    entity_id: str | None = None
    min: float | None = None
    max: float | None = None
    unit: str | None = None
    enabled: bool = True


@dataclass(frozen=True)
class ParsedCommand:
    """Ergebnis der Kommandoerkennung, optional mit Wert."""

    command: Command
    value: float | None = None


def normalize(text: str | None) -> str | None:
    """Vereinheitlicht Leerraum und Gross-/Kleinschreibung."""
    if text is None:
        return None
    collapsed = " ".join(text.split())
    if not collapsed:
        return None
    return collapsed.casefold()


def parse_value(raw: str | None) -> float | None:
    """Liest eine Zahl mit Komma oder Punkt. None bei ungueltiger Eingabe."""
    if raw is None:
        return None
    text = raw.strip()
    if not _VALUE_RE.match(text):
        return None
    return round(float(text.replace(",", ".")), 2)


def format_value(value: float | None) -> str:
    """Formatiert eine Zahl in deutscher Schreibweise mit Komma."""
    if value is None:
        return ""
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return text.replace(".", ",")


def describe(command: Command) -> str:
    """Kurzbeschreibung einer Aktion fuer Hilfe und Oberflaeche."""
    if command.action == ACTION_ON:
        return "einschalten"
    if command.action == ACTION_OFF:
        return "ausschalten"
    if command.action == ACTION_STATUS:
        return "Status abfragen"
    if command.action == ACTION_HELP:
        return "diese Hilfe anzeigen"
    if command.action == ACTION_SET_VALUE:
        low = format_value(command.min)
        high = format_value(command.max)
        unit = f" {command.unit}" if command.unit else ""
        return f"Wert setzen ({low} bis {high}{unit})"
    return command.action


def build_help_text(commands: tuple[Command, ...]) -> str:
    """Erzeugt die Hilfe aus den aktiven Kommandos."""
    lines = ["Verfuegbare Kommandos:"]
    for command in commands:
        if not command.enabled:
            continue
        lines.append(f"- {command.text}: {describe(command)}")
    return "\n".join(lines)


def _value_prefix(command: Command) -> str | None:
    if VALUE_PLACEHOLDER not in command.text:
        return None
    prefix = command.text.split(VALUE_PLACEHOLDER, 1)[0]
    return normalize(prefix)


def parse_command(
    text: str | None, commands: tuple[Command, ...]
) -> ParsedCommand | None:
    """Ordnet einen Text einem Kommando zu. None bei unbekanntem Text."""
    normalized = normalize(text)
    if normalized is None:
        return None

    for command in commands:
        if not command.enabled or VALUE_PLACEHOLDER in command.text:
            continue
        if normalize(command.text) == normalized:
            return ParsedCommand(command)

    value_commands = [
        command
        for command in commands
        if command.enabled and VALUE_PLACEHOLDER in command.text
    ]
    value_commands.sort(key=lambda item: len(item.text), reverse=True)
    for command in value_commands:
        prefix = _value_prefix(command)
        if not prefix or not normalized.startswith(prefix + " "):
            continue
        value = parse_value(normalized[len(prefix) :])
        if value is None:
            continue
        return ParsedCommand(command, value)
    return None
