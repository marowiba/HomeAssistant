# pyright: basic
"""HAD-0008: HTML-Rendering im GRC-Look (Slate/Emerald)."""

from __future__ import annotations

from html import escape
from typing import Any

NAV = (
    ("dashboard", "/dashboard", "Dashboard"),
    ("allowlist", "/allowlist", "Allowlist"),
    ("commands", "/commands", "Kommandos"),
    ("events", "/events", "Ereignislog"),
    ("audit", "/audit", "Audit-Log"),
    ("status", "/status", "Status"),
    ("settings", "/settings", "Einstellungen"),
)


def _e(value: Any) -> str:
    return escape("" if value is None else str(value), quote=True)


def _badge(ok: bool, text_ok: str, text_bad: str) -> str:
    css = "ok" if ok else "bad"
    return f'<span class="badge {css}">{_e(text_ok if ok else text_bad)}</span>'


def _flash(flash: str | None, error: bool = False) -> str:
    if not flash:
        return ""
    css = "flash error" if error else "flash"
    return f'<div class="{css}">{_e(flash)}</div>'


def layout(
    title: str,
    active: str,
    content: str,
    user: str | None = None,
    csrf: str = "",
    flash: str | None = None,
    error: bool = False,
) -> str:
    nav_items = "".join(
        f'<a class="nav-item{" active" if key == active else ""}" href="{href}">'
        f"{_e(label)}</a>"
        for key, href, label in NAV
    )
    if user:
        user_html = (
            '<form method="post" action="/logout" class="logout">'
            f'<input type="hidden" name="csrf" value="{_e(csrf)}">'
            f'<span class="user">{_e(user)}</span>'
            '<button type="submit" class="btn btn-ghost">Abmelden</button></form>'
        )
    else:
        user_html = ""
    return (
        "<!DOCTYPE html>\n"
        '<html lang="de">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{_e(title)} · Signal-Administration</title>\n"
        '<link rel="stylesheet" href="/static/admin.css">\n</head>\n<body>\n'
        '<header class="topbar">'
        '<a class="brand" href="/dashboard"><span class="brand-mark">SA</span>'
        " Signal-Administration</a>"
        f"{user_html}</header>\n"
        '<div class="shell"><aside class="sidebar"><nav>'
        f"{nav_items}</nav></aside>\n"
        f'<main class="content"><h1>{_e(title)}</h1>{_flash(flash, error)}{content}</main></div>\n'
        '<footer class="footer">Signal-Administration · srv001 · lokales Netzwerk</footer>\n'
        "</body>\n</html>"
    )


def login_page(error: str | None = None, username: str = "") -> str:
    return (
        "<!DOCTYPE html>\n"
        '<html lang="de"><head><meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>Anmeldung · Signal-Administration</title>\n"
        '<link rel="stylesheet" href="/static/admin.css"></head>\n'
        '<body class="login-body">\n'
        '<form class="login-card" method="post" action="/login">\n'
        "<h1>Signal-Administration</h1>\n"
        '<p class="muted">Anmeldung fuer Administratoren</p>\n'
        f"{_flash(error, True)}\n"
        f'<label>Benutzername<input name="username" value="{_e(username)}" '
        'autocomplete="username" required></label>\n'
        '<label>Passwort<input name="password" type="password" '
        'autocomplete="current-password" required></label>\n'
        '<button class="btn btn-primary" type="submit">Anmelden</button>\n'
        "</form>\n</body></html>"
    )


def dashboard_page(
    stats: list[tuple[str, Any]],
    statuses: list[tuple[str, dict[str, Any]]],
    recent: list[dict[str, Any]],
    user: str,
    csrf: str,
) -> str:
    cards = "".join(
        f'<div class="card"><div class="card-label">{_e(label)}</div>'
        f'<div class="card-value">{_e(value)}</div></div>'
        for label, value in stats
    )
    status_rows = "".join(
        f"<tr><td>{_e(name)}</td><td>{_badge(bool(item.get('ok')), 'OK', 'Fehler')}</td>"
        f"<td>{_e(item.get('detail'))}</td></tr>"
        for name, item in statuses
    )
    recent_rows = "".join(
        f"<tr><td>{_e(event.get('ts'))}</td>"
        f"<td>{_e(event.get('sender_name') or event.get('sender_number') or '-')}</td>"
        f"<td>{_e(event.get('text') or '-')}</td>"
        f"<td>{_e(event.get('decision'))}</td></tr>"
        for event in recent
    ) or '<tr><td colspan="4" class="muted">Keine Ereignisse.</td></tr>'
    content = (
        f'<div class="cards">{cards}</div>'
        '<section class="panel"><h2>Verbindungen</h2><table><thead><tr>'
        "<th>Dienst</th><th>Status</th><th>Detail</th></tr></thead><tbody>"
        f"{status_rows}</tbody></table></section>"
        '<section class="panel"><h2>Letzte Ereignisse</h2><table><thead><tr>'
        "<th>Zeit</th><th>Absender</th><th>Text</th><th>Entscheidung</th>"
        f"</tr></thead><tbody>{recent_rows}</tbody></table></section>"
    )
    return layout("Dashboard", "dashboard", content, user, csrf)


def allowlist_page(
    entries: list[dict[str, Any]],
    user: str,
    csrf: str,
    flash: str | None = None,
    error: bool = False,
) -> str:
    rows = []
    for index, entry in enumerate(entries):
        enabled = bool(entry.get("enabled", True))
        rows.append(
            "<tr>"
            f"<td>{_e(entry.get('label'))}</td>"
            f"<td>{_e(entry.get('number') or '-')}</td>"
            f'<td class="mono">{_e(entry.get("uuid") or "-")}</td>'
            f"<td>{_badge(enabled, 'aktiv', 'gesperrt')}</td>"
            '<td class="actions">'
            '<form method="post" action="/allowlist/update" class="inline-form">'
            f'<input type="hidden" name="csrf" value="{_e(csrf)}">'
            f'<input type="hidden" name="index" value="{index}">'
            f'<input name="label" value="{_e(entry.get("label"))}" required>'
            f'<input name="number" value="{_e(entry.get("number") or "")}" placeholder="+49...">'
            f'<input name="uuid" value="{_e(entry.get("uuid") or "")}" placeholder="UUID">'
            '<label class="inline"><input type="checkbox" name="enabled" value="1"'
            f'{" checked" if enabled else ""}> aktiv</label>'
            '<button class="btn" type="submit">Speichern</button></form>'
            '<form method="post" action="/allowlist/delete" class="inline-form" '
            "onsubmit=\"return confirm('Eintrag wirklich loeschen?');\">"
            f'<input type="hidden" name="csrf" value="{_e(csrf)}">'
            f'<input type="hidden" name="index" value="{index}">'
            '<button class="btn btn-danger" type="submit">Löschen</button></form>'
            "</td></tr>"
        )
    body = "".join(rows) or '<tr><td colspan="5" class="muted">Keine Eintraege.</td></tr>'
    content = (
        '<section class="panel"><h2>Neuen Eintrag anlegen</h2>'
        '<form class="grid-form" method="post" action="/allowlist/add">'
        f'<input type="hidden" name="csrf" value="{_e(csrf)}">'
        '<label>Bezeichnung<input name="label" required></label>'
        '<label>Nummer<input name="number" placeholder="+49..."></label>'
        '<label>UUID<input name="uuid" placeholder="UUID"></label>'
        '<label class="inline"><input type="checkbox" name="enabled" value="1" checked>'
        " aktiv</label>"
        '<button class="btn btn-primary" type="submit">Hinzufuegen</button></form></section>'
        '<section class="panel"><h2>Allowlist</h2><table><thead><tr>'
        "<th>Bezeichnung</th><th>Nummer</th><th>UUID</th><th>Status</th><th>Aktionen</th>"
        f"</tr></thead><tbody>{body}</tbody></table></section>"
    )
    return layout("Allowlist", "allowlist", content, user, csrf, flash, error)


def commands_page(
    commands: list[dict[str, Any]],
    user: str,
    csrf: str,
    flash: str | None = None,
    error: bool = False,
) -> str:
    rows = []
    for command in commands:
        enabled = bool(command.get("enabled", True))
        rows.append(
            "<tr>"
            f'<td class="mono">{_e(command.get("text"))}</td>'
            f"<td>{_e(command.get('description'))}</td>"
            f"<td>{_badge(enabled, 'aktiv', 'deaktiviert')}</td>"
            "<td>"
            '<form method="post" action="/commands/toggle" class="inline-form">'
            f'<input type="hidden" name="csrf" value="{_e(csrf)}">'
            f'<input type="hidden" name="command" value="{_e(command.get("id"))}">'
            f'<input type="hidden" name="enabled" value="{"0" if enabled else "1"}">'
            f'<button class="btn" type="submit">{"Deaktivieren" if enabled else "Aktivieren"}'
            "</button></form></td></tr>"
        )
    body = "".join(rows)
    content = (
        '<section class="panel"><h2>Feste Kommandos</h2>'
        '<p class="muted">Nur diese vier Kommandos sind zulaessig. Es lassen sich '
        "keine frei ausfuehrbaren Home-Assistant-Dienste oder Templates anlegen.</p>"
        "<table><thead><tr><th>Kommando</th><th>Bedeutung</th><th>Status</th>"
        f"<th>Aktion</th></tr></thead><tbody>{body}</tbody></table></section>"
    )
    return layout("Kommandos", "commands", content, user, csrf, flash, error)


def events_page(
    events: list[dict[str, Any]],
    filters: dict[str, str],
    user: str,
    csrf: str,
    page: int,
    total_pages: int,
    total: int,
    flash: str | None = None,
    error: bool = False,
) -> str:
    rows = []
    for event in events:
        rows.append(
            "<tr>"
            f'<td><input type="checkbox" name="ids" value="{_e(event.get("_id"))}" '
            'form="delete-form"></td>'
            f"<td>{_e(event.get('ts'))}</td>"
            f"<td>{_e(event.get('sender_name') or event.get('sender_number') or '-')}</td>"
            f"<td>{_e(event.get('text') or '-')}</td>"
            f"<td>{_e(event.get('decision'))}</td>"
            f"<td>{_e(event.get('command') or '-')}</td>"
            f'<td><a class="btn btn-ghost" href="/events/detail?id={_e(event.get("_id"))}">'
            "Details</a></td></tr>"
        )
    body = "".join(rows) or '<tr><td colspan="7" class="muted">Keine Ereignisse gefunden.</td></tr>'
    options = "".join(
        f'<option value="{value}"{" selected" if filters.get("decision") == value else ""}>'
        f"{_e(label)}</option>"
        for value, label in (("", "alle"), ("allowed", "erlaubt"), ("blocked", "blockiert"))
    )
    command_options = "".join(
        f'<option value="{value}"{" selected" if filters.get("command") == value else ""}>'
        f"{_e(label)}</option>"
        for value, label in (("", "alle"), ("on", "an"), ("off", "aus"), ("status", "Status"))
    )
    prev_link = (
        f'<a class="btn btn-ghost" href="/events?{_query(filters, page - 1)}">Zurueck</a>'
        if page > 1
        else ""
    )
    next_link = (
        f'<a class="btn btn-ghost" href="/events?{_query(filters, page + 1)}">Weiter</a>'
        if page < total_pages
        else ""
    )
    content = (
        '<section class="panel"><h2>Filter</h2>'
        '<form class="grid-form" method="get" action="/events">'
        f'<label>Suche<input name="q" value="{_e(filters.get("q", ""))}"></label>'
        f'<label>Entscheidung<select name="decision">{options}</select></label>'
        f'<label>Kommando<select name="command">{command_options}</select></label>'
        f'<label>Von<input type="date" name="from" value="{_e(filters.get("from", ""))}"></label>'
        f'<label>Bis<input type="date" name="to" value="{_e(filters.get("to", ""))}"></label>'
        '<button class="btn btn-primary" type="submit">Anwenden</button></form></section>'
        f'<section class="panel"><h2>Ereignisse ({total})</h2>'
        '<form id="delete-form" method="post" action="/events/delete" '
        "onsubmit=\"return confirm('Ausgewaehlte Ereignisse wirklich loeschen?');\">"
        f'<input type="hidden" name="csrf" value="{_e(csrf)}">'
        '<button class="btn btn-danger" type="submit">Ausgewaehlte loeschen</button></form>'
        "<table><thead><tr><th></th><th>Zeit</th><th>Absender</th><th>Text</th>"
        "<th>Entscheidung</th><th>Kommando</th><th></th></tr></thead>"
        f"<tbody>{body}</tbody></table>"
        f'<div class="pager">{prev_link}<span>Seite {page} von {total_pages}</span>'
        f"{next_link}</div></section>"
    )
    return layout("Ereignislog", "events", content, user, csrf, flash, error)


def _query(filters: dict[str, str], page: int) -> str:
    from urllib.parse import urlencode

    params = {key: value for key, value in filters.items() if value}
    params["page"] = str(page)
    return urlencode(params)


def event_detail_page(
    event: dict[str, Any],
    user: str,
    csrf: str,
    flash: str | None = None,
    error: bool = False,
) -> str:
    fields = (
        ("Zeit", event.get("ts")),
        ("Absender-Name", event.get("sender_name")),
        ("Absender-Nummer", event.get("sender_number")),
        ("Absender-UUID", event.get("sender_uuid")),
        ("Text", event.get("text")),
        ("Anhaenge", event.get("attachments")),
        ("Entscheidung", event.get("decision")),
        ("Grund", event.get("reason")),
        ("Treffer", event.get("matched_label")),
        ("Kommando", event.get("command")),
        ("Aktion", event.get("action")),
        ("Antwort", event.get("reply")),
    )
    rows = "".join(
        f"<tr><th>{_e(label)}</th><td>{_e(value)}</td></tr>" for label, value in fields
    )
    content = (
        '<section class="panel"><h2>Ereignis</h2>'
        f"<table class=\"detail\"><tbody>{rows}</tbody></table>"
        '<form method="post" action="/events/delete" '
        "onsubmit=\"return confirm('Ereignis wirklich loeschen?');\">"
        f'<input type="hidden" name="csrf" value="{_e(csrf)}">'
        f'<input type="hidden" name="ids" value="{_e(event.get("_id"))}">'
        '<button class="btn btn-danger" type="submit">Ereignis loeschen</button></form>'
        '<p><a class="btn btn-ghost" href="/events">Zurueck zum Log</a></p></section>'
    )
    return layout("Ereignis-Detail", "events", content, user, csrf, flash, error)


def audit_page(
    entries: list[dict[str, Any]],
    chain_ok: bool,
    bad_id: int | None,
    user: str,
    csrf: str,
) -> str:
    rows = "".join(
        f"<tr><td>{_e(entry.get('id'))}</td><td>{_e(entry.get('ts'))}</td>"
        f"<td>{_e(entry.get('actor'))}</td><td>{_e(entry.get('action'))}</td>"
        f"<td>{_e(entry.get('target'))}</td><td>{_e(entry.get('detail'))}</td>"
        f'<td class="mono">{_e(str(entry.get("entry_hash"))[:12])}</td></tr>'
        for entry in entries
    ) or '<tr><td colspan="7" class="muted">Noch keine Eintraege.</td></tr>'
    if chain_ok:
        chain = _badge(True, "Kette unversehrt", "")
    else:
        chain = _badge(False, "", f"Kette gebrochen ab Eintrag {bad_id}")
    content = (
        f'<section class="panel"><h2>Integritaet</h2><p>{chain}</p></section>'
        '<section class="panel"><h2>Audit-Log</h2><table class="audit"><thead><tr>'
        "<th>ID</th><th>Zeit</th><th>Akteur</th><th>Aktion</th><th>Ziel</th>"
        f"<th>Detail</th><th>Hash</th></tr></thead><tbody>{rows}</tbody></table></section>"
    )
    return layout("Audit-Log", "audit", content, user, csrf)


def status_page(
    statuses: list[tuple[str, dict[str, Any]]],
    errors: list[dict[str, Any]],
    user: str,
    csrf: str,
) -> str:
    status_rows = "".join(
        f"<tr><td>{_e(name)}</td><td>{_badge(bool(item.get('ok')), 'OK', 'Fehler')}</td>"
        f"<td>{_e(item.get('detail'))}</td></tr>"
        for name, item in statuses
    )
    error_rows = "".join(
        f"<tr><td>{_e(event.get('ts'))}</td>"
        f"<td>{_e(event.get('sender_name') or event.get('sender_number') or '-')}</td>"
        f"<td>{_e(event.get('command') or '-')}</td>"
        f"<td>{_e(event.get('action'))}</td><td>{_e(event.get('reply'))}</td></tr>"
        for event in errors
    ) or '<tr><td colspan="5" class="muted">Keine Fehler.</td></tr>'
    content = (
        '<section class="panel"><h2>Verbindungen</h2><table><thead><tr>'
        "<th>Dienst</th><th>Status</th><th>Detail</th></tr></thead>"
        f"<tbody>{status_rows}</tbody></table></section>"
        '<section class="panel"><h2>Letzte Verarbeitungsfehler</h2><table><thead><tr>'
        "<th>Zeit</th><th>Absender</th><th>Kommando</th><th>Aktion</th><th>Antwort</th>"
        f"</tr></thead><tbody>{error_rows}</tbody></table></section>"
    )
    return layout("Status", "status", content, user, csrf)


def settings_page(
    config: dict[str, Any],
    user: str,
    csrf: str,
    flash: str | None = None,
    error: bool = False,
) -> str:
    retention = config.get("retention_days", 30)
    content = (
        '<section class="panel"><h2>Aufbewahrung</h2>'
        '<form class="grid-form" method="post" action="/settings/retention">'
        f'<input type="hidden" name="csrf" value="{_e(csrf)}">'
        f'<label>Tage<input type="number" name="days" min="1" value="{_e(retention)}" required>'
        "</label>"
        '<button class="btn btn-primary" type="submit">Speichern</button></form>'
        '<form method="post" action="/settings/cleanup" class="inline-form">'
        f'<input type="hidden" name="csrf" value="{_e(csrf)}">'
        '<button class="btn" type="submit">Bereinigung jetzt ausfuehren</button></form></section>'
        '<section class="panel"><h2>Sicherung</h2>'
        '<p><a class="btn" href="/backup">Konfiguration herunterladen</a></p>'
        '<form class="grid-form" method="post" action="/restore">'
        f'<input type="hidden" name="csrf" value="{_e(csrf)}">'
        '<label>Backup-JSON<textarea name="backup" rows="8" required></textarea></label>'
        '<button class="btn btn-danger" type="submit">Wiederherstellen</button></form></section>'
    )
    return layout("Einstellungen", "settings", content, user, csrf, flash, error)


def error_page(message: str, user: str | None = None, csrf: str = "") -> str:
    content = f'<section class="panel"><p class="muted">{_e(message)}</p></section>'
    return layout("Fehler", "", content, user, csrf, message, True)
