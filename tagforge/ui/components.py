"""Reusable building blocks that every screen is made from.

    Panel      – bordered card with a title row, optional badge, action slot, body
    StatusTile – one of the three tiles across the top of a screen
    tile_row   – grid container that lays tiles out three across
    empty_state, field_label – small helpers
"""
from nicegui import ui

DASH = '—'


class Panel:
    """Card with a header row.

        p = Panel('Filters')
        with p.body:
            ui.input(...)
        with p.actions:            # right side of the header row
            ui.button('Re-check')
    """

    def __init__(self, title: str, badge: str | None = None) -> None:
        with ui.column().classes('tf-panel gap-0') as self.root:
            with ui.row().classes('tf-panel-head no-wrap'):
                ui.label(title).classes('tf-panel-title')
                self.badge = ui.label(badge or '').classes('tf-badge')
                self.badge.set_visibility(bool(badge))
                ui.space()
                self.actions = ui.row().classes('items-center gap-2 no-wrap')
            self.body = ui.column().classes('tf-panel-body')

    def set_badge(self, text: str | None) -> None:
        self.badge.set_text(text or '')
        self.badge.set_visibility(bool(text))


class StatusTile:
    """Label / big value / caption. Call .set() when data changes.

    state: None, 'ok', 'warn', or 'fail' — colors the value.
    """

    def __init__(self, label: str, caption: str = '', value: str = DASH) -> None:
        with ui.column().classes('tf-tile') as self.root:
            ui.label(label).classes('tf-label')
            self.value = ui.label(value).classes('tf-tile-value')
            self.caption = ui.label(caption).classes('tf-caption')

    def set(self, value, caption: str | None = None, state: str | None = None) -> None:
        self.value.set_text(DASH if value is None else str(value))
        if caption is not None:
            self.caption.set_text(caption)
        self.value.classes(remove='ok warn fail')
        if state:
            self.value.classes(add=state)


def tile_row() -> ui.element:
    """Grid that holds three StatusTiles side by side. Use as a context manager."""
    return ui.element('div').classes('tf-tiles')


def empty_state(title: str, hint: str = '') -> ui.column:
    with ui.column().classes('tf-empty') as col:
        ui.label(title).classes('tf-empty-title')
        if hint:
            ui.label(hint).classes('tf-caption')
    return col


def field_label(text: str) -> ui.label:
    return ui.label(text).classes('tf-label')
