"""Controller Tag List (TF-R01) — design doc Figure 5.

TODO: build this screen. Use browser.py as the pattern:
  frame() → workspace() → Panels in side, tile_row() + Panels in main.
"""
from nicegui import ui

from tagforge.ui.components import Panel, StatusTile, empty_state, tile_row
from tagforge.ui.layout import frame, workspace


@ui.page('/reports/tag-list')
def tag_list_report_page() -> None:
    with frame('/reports/tag-list'):
        side, main = workspace()

        with side:
            panel = Panel('Report source')
            with panel.body:
                ui.label('TODO').classes('tf-caption')

        with main:
            with tile_row():
                StatusTile('Tags listed')
                StatusTile('Equipment areas')
                StatusTile('Active filter')

            body = Panel('Controller Tag List')
            with body.body:
                empty_state('Not built yet')
