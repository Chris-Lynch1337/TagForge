"""Smoke check for the write path, the rule set and free-text search.

A tag goes in through the service layer, is committed, and can be read back;
every validation rule is made to fire; and search is exercised against name,
description and PLC address, including the LIKE wildcard escaping. Runs against
a scratch database and touches nothing in tagforge.db.

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

    # ---- free-text search (M2's fifth acceptance criterion) -------------
    # Three more records so a search can succeed on one and exclude the others.
    for name, desc, addr in (
            ('HTR_ZONE2_PV', 'Heater zone 2 process value', 'N7:41'),
            ('CW_SUPPLY_TMP', 'Cooling water supply temperature', 'N7:60'),
            ('LT_100_PCT',    'Level transmitter 100 percent span', 'N7:61')):
        services.create_tag(conn, {**good, 'tag_name': name,
                                   'description': desc, 'address_path': addr})

    def names(**filters):
        return sorted(r['tag_name'] for r in repo.list_tags(conn, **filters))

    check('search matches the tag name',
          names(search='HTR_ZONE') == ['HTR_ZONE1_PV', 'HTR_ZONE2_PV'],
          ','.join(names(search='HTR_ZONE')))
    check('search is case-insensitive',
          names(search='htr_zone') == names(search='HTR_ZONE'))
    check('search matches the description',
          names(search='cooling water') == ['CW_SUPPLY_TMP'])
    check('search matches the PLC address',
          names(search='N7:60') == ['CW_SUPPLY_TMP'])
    check('search misses cleanly', names(search='no such tag') == [])
    check('blank search is not a filter',
          names(search='   ') == names(), f'{len(names())} rows')

    # A bare % or _ would match everything if the wildcards were not escaped.
    check('percent is escaped, not a wildcard', names(search='%') == [])
    check('underscore is escaped, not a wildcard',
          names(search='LT_100') == ['LT_100_PCT'],
          ','.join(names(search='LT_100')))

    check('search combines with the other filters',
          names(search='ZONE', data_type='REAL') == ['HTR_ZONE1_PV', 'HTR_ZONE2_PV'])
    check('search combines with a non-matching filter',
          names(search='ZONE', data_type='BOOL') == [])

    # ---- the service layer no longer writes its own SQL -----------------
    check('repository resolves a controller to its project',
          repo.project_id_for_controller(conn, controller_id) == project_id)
    check('unknown controller resolves to None',
          repo.project_id_for_controller(conn, 9999) is None)
    check('repository resolves a type name to its id',
          repo.data_type_id(conn, 'REAL') is not None)
    check('unknown type name resolves to None',
          repo.data_type_id(conn, 'FLOAT32') is None)

    # browse() is what the API calls, so check search survives that layer too.
    browsed = services.browse(conn, search='HTR_ZONE')
    check('browse() passes search through to the repository',
          browsed['matching'] == 2 and len(browsed['rows']) == 2,
          f"matching={browsed['matching']}")

    conn.close()
    print(f'\n{"all checks passed" if not failed else str(failed) + " check(s) failed"}'
          f'   scratch db: {tmp}')
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
