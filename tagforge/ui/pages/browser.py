"""Tag Browser (home screen) — design doc Figure 2.

Side:  Project Explorer, Filters
Main:  3 status tiles, Tag Register table

Every number on this page comes from the API, free-text search included: the box
sends a search parameter to GET /api/tags and the table and all three tiles
repaint from the one response. That closes the last M2 acceptance criterion.
"""
from nicegui import ui

from tagforge.ui import api_client as api
from tagforge.ui.components import Panel, StatusTile, empty_state, field_label, tile_row
from tagforge.ui.layout import frame, workspace

DASH = '—'

REGISTER_COLUMNS = [
    {'name': 'tag_name',     'label': 'Tag name',    'field': 'tag_name',     'align': 'left', 'sortable': True},
    {'name': 'address_path', 'label': 'PLC address', 'field': 'address_path', 'align': 'left'},
    {'name': 'data_type',    'label': 'Type',        'field': 'data_type',    'align': 'left', 'sortable': True},
    {'name': 'eng_units',    'label': 'Units',       'field': 'eng_units',    'align': 'left'},
    {'name': 'eu_span',      'label': 'EU span',     'field': 'eu_span',      'align': 'left'},
    {'name': 'area_name',    'label': 'Area',        'field': 'area_name',    'align': 'left', 'sortable': True},
    {'name': 'alarm',        'label': 'Alarm',       'field': 'alarm',        'align': 'left'},
    {'name': 'updated_utc',  'label': 'Updated',     'field': 'updated_utc',  'align': 'left', 'sortable': True},
]


def _span(row) -> str:
    """Engineering span as one column. An em dash means the type stores no span —
    it does not mean zero. TF-R01 carries the same convention."""
    lo, hi = row.get('eu_min'), row.get('eu_max')
    if lo is None or hi is None:
        return DASH
    return f'{lo:g} – {hi:g}'


def _alarm(row) -> str:
    if not row.get('alarm_enabled'):
        return DASH
    marks = [m for m, v in (('LO', row.get('alarm_lo')), ('HI', row.get('alarm_hi')))
             if v is not None]
    return '/'.join(marks) or 'ON'


def _display(row) -> dict:
    out = dict(row)
    out['eu_span'] = _span(row)
    out['alarm'] = _alarm(row)
    out['address_path'] = row.get('address_path') or DASH
    out['eng_units'] = row.get('eng_units') or DASH
    out['area_name'] = row.get('area_name') or DASH
    out['updated_utc'] = (row.get('updated_utc') or '')[:10]
    return out


@ui.page('/')
def browser_page() -> None:
    with frame('/'):
        side, main = workspace()

        # State the whole page reads from. Plain dict so the callbacks can mutate it.
        state = {'project_id': None, 'controller_id': None}

        # ---------------- side column ----------------
        with side:
            explorer = Panel('Project Explorer', badge='0')
            with explorer.body:
                explorer_body = ui.column().classes('w-full gap-2')
                with ui.row().classes('gap-2'):
                    ui.button('New project').props('outline no-caps') \
                        .tooltip('Not written yet — project maintenance screen')
                    ui.button('Open database').props('outline no-caps') \
                        .tooltip('Not written yet — maintenance screen')

            filters = Panel('Filters')
            with filters.body:
                field_label('Search name / description')
                # debounce keeps one keystroke from becoming one HTTP request.
                search = ui.input(placeholder='Tag name, description or address',
                                  on_change=lambda: refresh()) \
                    .props('outlined dense dark clearable debounce=350') \
                    .classes('w-full')
                ui.label('Matches tag name, description or PLC address.') \
                    .classes('tf-caption')

                field_label('Equipment area')
                area_select = ui.select({None: 'All areas'}, value=None) \
                    .props('outlined dense dark').classes('w-full')

                with ui.row().classes('w-full no-wrap gap-3'):
                    with ui.column().classes('flex-1 gap-1'):
                        field_label('Data type')
                        type_select = ui.select({None: 'All types'}, value=None) \
                            .props('outlined dense dark').classes('w-full')
                    with ui.column().classes('flex-1 gap-1'):
                        field_label('Alarmed only')
                        alarm_select = ui.select({False: 'No', True: 'Yes'}, value=False) \
                            .props('outlined dense dark').classes('w-full')

                with ui.row().classes('gap-2 w-full'):
                    ui.button('Apply filters', on_click=lambda: refresh()).props('no-caps')
                    ui.button('Clear', on_click=lambda: clear_filters()).props('outline no-caps')

        # ---------------- main column ----------------
        with main:
            with tile_row():
                tags_tile = StatusTile('Tags in project', 'No project selected')
                match_tile = StatusTile('Matching filter', 'No filter applied')
                flags_tile = StatusTile('Validation flags', 'Nothing to audit yet')

            register = Panel('Tag Register', badge='No controller')
            with register.body:
                # selection='single' is what makes table.selected work for Edit.
                table = ui.table(columns=REGISTER_COLUMNS, rows=[], row_key='tag_id',
                                 selection='single') \
                          .classes('w-full').props('flat dark')
                with table.add_slot('no-data'):
                    empty_state('No tags to show',
                                'Select a controller in the project explorer, '
                                'add a tag, or import a CSV file.')
                with ui.row().classes('w-full items-center'):
                    row_count = ui.label('No rows').classes('tf-caption')
                    ui.space()
                    ui.button('New tag', on_click=lambda: ui.navigate.to('/editor')).props('no-caps')
                    ui.button('Edit', on_click=lambda: open_selected()).props('outline no-caps')
                    ui.button('Delete').props('outline no-caps') \
                        .tooltip('Not written yet — the delete endpoint is the next work package')
                    ui.button('Export CSV').props('outline no-caps') \
                        .tooltip('Not written yet — CSV export')

        # ---------------- behaviour ----------------
        def open_selected() -> None:
            if table.selected:
                ui.navigate.to(f"/editor?tag_id={table.selected[0]['tag_id']}")
            else:
                ui.notify('Select a row first', type='warning')

        def clear_filters() -> None:
            search.value = ''
            area_select.value = None
            type_select.value = None
            alarm_select.value = False
            refresh()

        def select_controller(controller_id, name) -> None:
            state['controller_id'] = controller_id
            register.set_badge(name)
            refresh()

        def load_lookups() -> None:
            """Project tree and the two lookup selects. Runs once on page load."""
            try:
                projects = api.projects()
                types = api.data_types()
                areas = api.areas(state['project_id'])
            except api.ApiError as exc:
                explorer_body.clear()
                with explorer_body:
                    empty_state('API unavailable', str(exc))
                return

            explorer.set_badge(str(len(projects)))
            explorer_body.clear()
            with explorer_body:
                if not projects:
                    empty_state('No projects yet',
                                'A project holds controllers, equipment areas and tags.')
                for project in projects:
                    ui.label(project['project_name']).classes('font-semibold')
                    for controller in api.controllers(project['project_id']):
                        ui.button(f"{controller['controller_name']}  ({controller['tag_count']})",
                                  on_click=lambda c=controller: select_controller(
                                      c['controller_id'], c['controller_name'])) \
                            .props('flat dense no-caps align=left').classes('w-full')

            type_select.set_options({None: 'All types',
                                     **{t['type_name']: t['type_name'] for t in types}})
            area_select.set_options({None: 'All areas',
                                     **{a['area_id']: a['area_name'] for a in areas}})

        def refresh() -> None:
            """Pull rows and tile counts from the API and repaint."""
            try:
                data = api.tags(controller_id=state['controller_id'],
                                project_id=state['project_id'],
                                area_id=area_select.value,
                                data_type=type_select.value,
                                alarmed_only='1' if alarm_select.value else None,
                                search=search.value)
            except api.ApiError as exc:
                ui.notify(str(exc), type='negative')
                return

            rows = [_display(r) for r in data['rows']]
            table.rows = rows
            table.update()

            row_count.set_text(f"{len(rows)} row{'' if len(rows) == 1 else 's'}"
                               if rows else 'No rows')
            tags_tile.set(data['tags_in_project'] or None,
                          'In the selected project' if data['tags_in_project']
                          else 'No project selected')
            searching = bool((search.value or '').strip())
            match_tile.set(len(rows) or None,
                           f"of {data['tags_in_project']} in project" if rows
                           else ('No match for that search' if searching
                                 else 'No rows match'))
            flagged = data['flagged']
            flags_tile.set(flagged if flagged else None,
                           'Tags failing a rule today' if flagged else 'Nothing flagged',
                           state='fail' if flagged else None)

        load_lookups()
        refresh()
