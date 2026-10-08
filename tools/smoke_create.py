"""Smoke check for the tag creation service.

a tag goes in through the service
layer, is committed, and can be read back. Touches nothing in tagforge.db.

    python -m tools.smoke_create
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tagforge import services                      # noqa: E402
from tagforge.db import repository as repo         # noqa: E402

PASS, FAIL = 'PASS', 'FAIL'


def main() -> int:
    tmp = Path(tempfile.mkdtemp()) / 'smoke.db'
    conn = repo.open_database(tmp)
    failed = 0

    def check(label, ok, detail=''):
        nonlocal failed
        if not ok:
            failed += 1
        print(f'{PASS if ok else FAIL}  {label}{"  " + detail if detail else ""}')

    # ---- schema builds from empty -------------------------------------
    state = repo.status(conn)
    check('schema builds from an empty file',
          state['schema_version'] == state['expected_schema_version'],
          f"v{state['schema_version']}")
    check('DataType lookup seeded', state['counts']['DataType'] == 7,
          f"{state['counts']['DataType']} types")
    check('foreign keys enforced', state['foreign_keys'])

    # ---- a project to hang records on ---------------------------------
    project_id = repo.create_project(conn, 'Smoke Project', 'fictional')
    controller_id = repo.create_controller(conn, project_id, 'CC-01 MAIN',
                                           'AutomationDirect', 'P2-622')
    area_id = repo.create_area(conn, project_id, 'Heating')

    # ---- the write path ------------------------------------------------
    good = {'controller_id': controller_id, 'area_id': area_id,
            'tag_name': 'HTR_ZONE1_PV', 'description': 'Heater zone 1 process value',
            'address_path': 'N7:40', 'data_type': 'REAL', 'eng_units': 'F',
            'eu_min': 0.0, 'eu_max': 600.0,
            'alarm_enabled': True, 'alarm_lo': 40.0, 'alarm_hi': 575.0}
    stored = services.create_tag(conn, good)
    check('create through the service layer', stored['tag_id'] is not None,
          f"tag_id={stored['tag_id']}")

    read_back = repo.get_tag(conn, stored['tag_id'])
    check('read back after commit',
          read_back and read_back['tag_name'] == 'HTR_ZONE1_PV')

    conn.close()
    conn = repo.open_database(tmp)          # survives a close/reopen
    check('survives a restart', repo.get_tag(conn, stored['tag_id']) is not None)

    # ---- the rules actually fire ---------------------------------------
    cases = [
        ('NAME_PATTERN', {**good, 'tag_name': 'Feed Pump Amps'}),
        ('DUPLICATE',    {**good}),
        ('TYPE_UNKNOWN', {**good, 'tag_name': 'T2', 'data_type': 'FLOAT32'}),
        ('SCALE_ORDER',  {**good, 'tag_name': 'T3', 'eu_min': 120.0, 'eu_max': 0.0}),
        ('ALARM_RANGE',  {**good, 'tag_name': 'T4', 'alarm_hi': 750.0}),
        ('REQUIRED',     {**good, 'tag_name': ''}),
        ('FK_MISSING',   {**good, 'tag_name': 'T5', 'controller_id': 9999}),
        ('LENGTH',       {**good, 'tag_name': 'T6', 'description': 'x' * 200}),
    ]
    for rule, record in cases:
        fired = {f.rule for f in services.check_tag(conn, record)}
        check(f'{rule} fires', rule in fired, ','.join(sorted(fired)) or 'nothing fired')

    # ---- nothing was written by the failures ---------------------------
    check('rejected records were not written',
          repo.status(conn)['counts']['Tag'] == 1)

    conn.close()
    print(f'\n{"all checks passed" if not failed else str(failed) + " check(s) failed"}'
          f'   scratch db: {tmp}')
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
