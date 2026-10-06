"""Tag Editor — design doc Figure 3.

Read-only at week 3. The form loads a record from the API and re-runs the shared
rule set on every change, so the field validation table and the rule trace are
live; Save stays disabled because the editor is not wired to the write path yet.
The API create endpoint does work — see tools/smoke_create.py — so the gap is
here in the UI, not in the back end.

Side:  Configure Tag Register (the record)
Main:  3 tiles, Field validation, Validation trace
"""
from nicegui import ui

from tagforge.ui import api_client as api
from tagforge.ui.components import Panel, StatusTile, empty_state, field_label, tile_row
from tagforge.ui.layout import frame, workspace

FAILURE_COLUMNS = [
    {'name': 'field',    'label': 'Field',           'field': 'field',    'align': 'left'},
    {'name': 'value',    'label': 'Submitted value', 'field': 'value',    'align': 'left'},
    {'name': 'rule',     'label': 'Rule',            'field': 'rule',     'align': 'left'},
    {'name': 'severity', 'label': 'Severity',        'field': 'severity', 'align': 'left'},
    {'name': 'message',  'label': 'Message',         'field': 'message',  'align': 'left'},
]

TRACE_COLUMNS = [
    {'name': 'rule',        'label': 'Rule',   'field': 'rule',        'align': 'left'},
    {'name': 'description', 'label': 'Checks', 'field': 'description', 'align': 'left'},
    {'name': 'state',       'label': 'Result', 'field': 'state',       'align': 'left'},
]


@ui.page('/editor')
def editor_page(tag_id: int | None = None) -> None:
    with frame('/editor'):
        side, main = workspace()
        fields: dict = {}

        with side:
            panel = Panel('Configure Tag Register', badge='READ-ONLY')
            with panel.body:
                field_label('Tag name')
                fields['tag_name'] = ui.input(placeholder='TAG_NAME') \
                    .props('outlined dense dark').classes('w-full tf-mono')
                ui.label('A-Z, 0-9 and underscore. Unique within its controller.') \
                    .classes('tf-caption')

                with ui.row().classes('w-full no-wrap gap-3'):
                    with ui.column().classes('flex-1 gap-1'):
                        field_label('PLC address')
                        fields['address_path'] = ui.input(placeholder='N7:0') \
                            .props('outlined dense dark').classes('w-full tf-mono')
                    with ui.column().classes('flex-1 gap-1'):
                        field_label('Data type')
                        fields['data_type'] = ui.select({}, value=None) \
                            .props('outlined dense dark').classes('w-full')

                field_label('Description')
                fields['description'] = ui.input(placeholder='What this tag represents') \
                    .props('outlined dense dark').classes('w-full')

                with ui.row().classes('w-full no-wrap gap-3'):
                    with ui.column().classes('flex-1 gap-1'):
                        field_label('Controller')
                        fields['controller_id'] = ui.select({}, value=None) \
                            .props('outlined dense dark').classes('w-full')
                    with ui.column().classes('flex-1 gap-1'):
                        field_label('Equipment area')
                        fields['area_id'] = ui.select({None: '(none)'}, value=None) \
                            .props('outlined dense dark').classes('w-full')

                with ui.row().classes('w-full no-wrap gap-3'):
                    with ui.column().classes('flex-1 gap-1'):
                        field_label('Eng. units')
                        fields['eng_units'] = ui.input(placeholder='°F, psi, rpm') \
                            .props('outlined dense dark').classes('w-full')
                    with ui.column().classes('flex-1 gap-1'):
                        field_label('Alarm priority')
                        fields['alarm_priority'] = ui.input(placeholder='High') \
                            .props('outlined dense dark').classes('w-full')

                for left, right in (('eu_min', 'eu_max'), ('alarm_lo', 'alarm_hi')):
                    with ui.row().classes('w-full no-wrap gap-3'):
                        for name in (left, right):
                            with ui.column().classes('flex-1 gap-1'):
                                field_label(name.replace('_', ' ').upper())
                                fields[name] = ui.number(format='%g') \
                                    .props('outlined dense dark').classes('w-full tf-mono')

                fields['alarm_enabled'] = ui.switch('Alarm enabled').props('dark')

                with ui.row().classes('gap-2 w-full'):
                    save = ui.button('Save tag').props('no-caps')
                    save.disable()
                    save.tooltip('Week 4 — the editor is not wired to the write path yet')
                    ui.button('Re-check', on_click=lambda: revalidate()).props('outline no-caps')
                ui.label('Read-only this week. The API write path is open and '
                         'covered by tools/smoke_create.py.').classes('tf-caption')

        with main:
            with tile_row():
                state_tile = StatusTile('Record state', 'Nothing submitted yet')
                rules_tile = StatusTile('Rules evaluated', 'Of 8 in the rule set')
                blocking_tile = StatusTile('Blocking failures', 'Nothing written yet')

            failures_panel = Panel('Field validation')
            with failures_panel.body:
                failures_table = ui.table(columns=FAILURE_COLUMNS, rows=[], row_key='field') \
                    .classes('w-full').props('flat dark')
                with failures_table.add_slot('no-data'):
                    empty_state('No problems to report',
                                'Failures appear here as one row per rule, '
                                'with the value that caused them.')

            trace_panel = Panel('Validation trace', badge='UI · API · IMPORT · AUDIT')
            with trace_panel.body:
                trace_table = ui.table(columns=TRACE_COLUMNS, rows=[], row_key='rule') \
                    .classes('w-full').props('flat dark')

        # ---------------- behaviour ----------------
        def record() -> dict:
            out = {name: el.value for name, el in fields.items()}
            out['alarm_enabled'] = bool(out.get('alarm_enabled'))
            if tag_id:
                out['tag_id'] = tag_id
            return out

        def revalidate() -> None:
            """Ask the API to run the rules. Same module the import will call."""
            try:
                result = api.check(record())
            except api.ApiError as exc:
                ui.notify(str(exc), type='negative')
                return

            failures_table.rows = result['failures']
            failures_table.update()
            trace_table.rows = result['trace']
            trace_table.update()

            blockers = result['blocking_count']
            state_tile.set('VALID' if result['valid'] else 'INVALID',
                           'Ready to write' if result['valid']
                           else f"{blockers} rule{'' if blockers == 1 else 's'} failed",
                           state='ok' if result['valid'] else 'fail')
            rules_tile.set(len(result['trace']), 'Shared validation module')
            blocking_tile.set(blockers or 0,
                              'Nothing written yet',
                              state='fail' if blockers else None)

        def load_lookups() -> None:
            try:
                types = api.data_types()
                controllers = api.controllers()
                areas = api.areas()
            except api.ApiError as exc:
                ui.notify(str(exc), type='negative')
                return
            fields['data_type'].set_options(
                {t['type_name']: t['type_name'] for t in types})
            fields['controller_id'].set_options(
                {c['controller_id']: c['controller_name'] for c in controllers})
            fields['area_id'].set_options(
                {None: '(none)', **{a['area_id']: a['area_name'] for a in areas}})

        def load_tag() -> None:
            if not tag_id:
                return
            try:
                row = api.tag(int(tag_id))
            except api.ApiError as exc:
                ui.notify(str(exc), type='negative')
                return
            panel.set_badge(f"TAG {tag_id} · READ-ONLY")
            for name, el in fields.items():
                if name in row:
                    el.value = row[name]

        load_lookups()
        load_tag()
        for element in fields.values():
            element.on_value_change(lambda _: revalidate())
        revalidate()
