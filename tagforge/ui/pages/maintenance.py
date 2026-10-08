"""Maintenance — design doc Maintenance Features section.

TODO: build this screen. Use browser.py as the pattern:
  frame() → workspace() → Panels in side, tile_row() + Panels in main.
"""
from nicegui import ui

from tagforge.ui.components import Panel, StatusTile, empty_state, tile_row
from tagforge.ui.layout import frame, workspace


@ui.page('/maintenance')
def maintenance_page() -> None:
    with frame('/maintenance'):
        side, main = workspace()

        with side:
            panel = Panel('Database')
            with panel.body:
                ui.label('TODO').classes('tf-caption')

        with main:
            with tile_row():
                StatusTile('Schema version')
                StatusTile('Database size')
                StatusTile('Last backup')

            body = Panel('Diagnostics')
            with body.body:
                empty_state('Not built yet')
