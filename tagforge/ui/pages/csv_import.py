"""CSV Import — design doc Figure 4.

TODO: build this screen. Use browser.py as the pattern:
  frame() → workspace() → Panels in side, tile_row() + Panels in main.
"""
from nicegui import ui

from tagforge.ui.components import Panel, StatusTile, empty_state, tile_row
from tagforge.ui.layout import frame, workspace


@ui.page('/import')
def csv_import_page() -> None:
    with frame('/import'):
        side, main = workspace()

        with side:
            panel = Panel('Import')
            with panel.body:
                ui.label('TODO').classes('tf-caption')

        with main:
            with tile_row():
                StatusTile('Rows read')
                StatusTile('Accepted')
                StatusTile('Rejected')

            body = Panel('Validation review')
            with body.body:
                empty_state('Not built yet')
