"""Page frame shared by every screen: header, nav, DB status pill, and the
side-column / main-column workspace.

Usage in a page module:

    @ui.page('/editor')
    def editor_page():
        with frame('/editor'):
            side, main = workspace()
            with side:
                ...
            with main:
                ...
"""
from contextlib import contextmanager
from pathlib import Path

from nicegui import ui

from tagforge import __version__
from tagforge.ui import api_client
from tagforge.ui.theme import apply_theme

# (route, label) — order here is the order in the header.
NAV = [
    ('/',                   'Tag Browser'),
    ('/editor',             'Tag Editor'),
    ('/import',             'CSV Import'),
    ('/reports/tag-list',   'Tag List Report'),
    ('/reports/validation', 'Validation Report'),
    ('/maintenance',        'Maintenance'),
]


def db_status_pill() -> None:
    """Right side of the header: real schema state, read from the API.

    If the pill says NOT INITIALIZED while the app is running, the API thread did
    not come up — that is the first thing to check when a screen is empty.
    """
    try:
        state = api_client.status()
        ready = state['schema_version'] == state['expected_schema_version']
        label = f"DB: READY  v{state['schema_version']}" if ready else 'DB: SCHEMA MISMATCH'
        detail = Path(state['db_path']).name
    except api_client.ApiError:
        ready, label, detail = False, 'DB: API UNREACHABLE', 'tagforge.db'

    with ui.row().classes('tf-db-pill'):
        ui.element('div').classes('tf-db-dot' + (' ok' if ready else ''))
        ui.label(label).classes('font-bold')
        ui.label(detail).classes('tf-mono tf-caption')


@contextmanager
def frame(active_route: str):
    """Wrap a page in the TagForge header. `active_route` highlights the nav link."""
    apply_theme()
    title = next((label for route, label in NAV if route == active_route), '')
    ui.page_title(f'{title} · TagForge' if title else 'TagForge')

    with ui.header().classes('tf-header'):
        with ui.row().classes('items-center no-wrap gap-3'):
            ui.icon('grid_view').classes('tf-logo')
            ui.label('TagForge').classes('tf-brand')
            ui.label(f'v{__version__} MVP').classes('tf-version')

        with ui.row().classes('tf-nav no-wrap'):
            for route, label in NAV:
                cls = 'tf-nav-link' + (' active' if route == active_route else '')
                ui.link(label, route).classes(cls)

        ui.space()
        db_status_pill()

    with ui.column().classes('tf-page'):
        yield


def workspace() -> tuple[ui.column, ui.column]:
    """Create the two-column grid and return (side, main) containers to fill."""
    with ui.element('div').classes('tf-workspace'):
        side = ui.column().classes('tf-side')
        main = ui.column().classes('tf-main')
    return side, main
