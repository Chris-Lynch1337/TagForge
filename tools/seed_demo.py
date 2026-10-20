"""Load the fictional demonstration project used in the walkthrough.

Every tag is written through services.create_tag(), so seeding exercises the same
validation and the same write path the application uses — if a rule would reject
a record, it is rejected here too.

    python -m tools.seed_demo            load it
    python -m tools.seed_demo --reset    remove it and load it again
    python -m tools.seed_demo --db X     use a database other than tagforge.db

The data is invented. It carries no customer names, network details or anything
from a live system.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tagforge import services                      # noqa: E402
from tagforge.db import repository as repo         # noqa: E402

PROJECT = 'Line 3 Reclaim Skid'
AREAS = ['Feed & Transfer', 'Heating', 'Separation', 'Utilities']
CONTROLLERS = [
    ('CC-01 MAIN',  'AutomationDirect', 'P2-622'),
    ('CC-31 STILL', 'AutomationDirect', 'P2-550'),
    ('HMI-01',      'AVEVA',            'Edge'),
]

# (controller, area, tag_name, description, address, type, units, eu_min, eu_max,
#  alarm_lo, alarm_hi, priority)
TAGS = [
    ('CC-01 MAIN', 'Feed & Transfer', 'FEED_PUMP_AMPS',  'Feed pump motor current',       'N7:20',  'REAL', 'A',    0.0, 60.0,   None, 52.0,  'High'),
    ('CC-01 MAIN', 'Feed & Transfer', 'FEED_PUMP_RUN',   'Feed pump run command',         'B3:0/4', 'BOOL', None,  None, None,   None, None,  None),
    ('CC-01 MAIN', 'Feed & Transfer', 'FEED_TANK_LEVEL', 'Feed tank level transmitter',   'N7:12',  'REAL', 'in',   0.0, 120.0,   6.0, 108.0, 'High'),
    ('CC-01 MAIN', 'Feed & Transfer', 'XFER_VALVE_CMD',  'Transfer valve open command',   'B3:1/2', 'BOOL', None,  None, None,   None, None,  None),
    ('CC-01 MAIN', 'Feed & Transfer', 'XFER_VALVE_FB',   'Transfer valve open feedback',  'B3:1/3', 'BOOL', None,  None, None,   None, None,  None),
    ('CC-01 MAIN', 'Heating',         'HTR_MASTER_EN',   'Heater master enable',          'B3:2/0', 'BOOL', None,  None, None,   None, None,  None),
    ('CC-01 MAIN', 'Heating',         'HTR_ZONE1_PV',    'Heater zone 1 process value',   'N7:40',  'REAL', 'degF', 0.0, 600.0,  40.0, 575.0, 'High'),
    ('CC-01 MAIN', 'Heating',         'HTR_ZONE1_SP',    'Heater zone 1 setpoint',        'N7:41',  'REAL', 'degF', 0.0, 600.0,  None, None,  None),
    ('CC-01 MAIN', 'Heating',         'HTR_ZONE2_PV',    'Heater zone 2 process value',   'N7:42',  'REAL', 'degF', 0.0, 600.0,  40.0, 575.0, 'High'),
    ('CC-01 MAIN', 'Heating',         'HTR_ZONE2_SP',    'Heater zone 2 setpoint',        'N7:43',  'REAL', 'degF', 0.0, 600.0,  None, None,  None),
    ('CC-01 MAIN', 'Separation',      'SEP_BOWL_TEMP',   'Separator bowl temperature',    'N7:57',  'REAL', 'degF', 0.0, 300.0,  None, 240.0, 'Medium'),
    ('CC-01 MAIN', 'Separation',      'SEP_DISCHARGE_P', 'Separator discharge pressure',  'N7:55',  'REAL', 'psi',  0.0, 150.0,  None, 135.0, 'High'),
    ('CC-01 MAIN', 'Separation',      'SEP_SPEED_FB',    'Separator speed feedback',      'N7:56',  'DINT', 'rpm',  0.0, 7500.0, None, None,  None),
    ('CC-01 MAIN', 'Utilities',       'SYS_E_STOP_OK',   'Safety circuit healthy',        'B3:0/0', 'BOOL', None,  None, None,   None, None,  None),
    ('CC-01 MAIN', 'Utilities',       'SYS_RUN_HOURS',   'Accumulated run hours',         'N7:90',  'DINT', 'h',    0.0, 99999.0, None, None, None),
    ('CC-01 MAIN', 'Utilities',       'SYS_UPS_OK',      'Control power UPS healthy',     'B3:0/1', 'BOOL', None,  None, None,   None, None,  'Medium'),
    ('CC-31 STILL', 'Heating',        'STILL_FEED_TEMP', 'Still feed temperature',        'N7:10',  'REAL', 'degF', 0.0, 400.0,  None, 360.0, 'High'),
    ('CC-31 STILL', 'Separation',     'STILL_LEVEL',     'Still sump level',              'N7:14',  'REAL', 'in',   0.0, 96.0,    4.0, 88.0,  'High'),
    ('CC-31 STILL', 'Separation',     'STILL_VAC_PRESS', 'Still vacuum pressure',         'N7:16',  'REAL', 'inHg', 0.0, 30.0,   None, 28.0,  'Medium'),
]


def existing_project(conn):
    return next((p for p in repo.list_projects(conn)
                 if p['project_name'] == PROJECT), None)


def _db_path():
    if '--db' in sys.argv:
        return Path(sys.argv[sys.argv.index('--db') + 1])
    return repo.DB_PATH


def main() -> int:
    conn = repo.open_database(_db_path())
    found = existing_project(conn)

    if found and '--reset' in sys.argv:
        with conn:
            conn.execute('DELETE FROM Project WHERE project_id = ?',
                         (found['project_id'],))
        print(f'removed the existing "{PROJECT}" (controllers, areas and tags cascade)')
        found = None

    if found:
        print(f'"{PROJECT}" is already loaded — {found["tag_count"]} tags.')
        print('Run with --reset to rebuild it.')
        conn.close()
        return 0

    project_id = repo.create_project(conn, PROJECT, 'Fictional demo site',
                                     'Demonstration data for the course walkthrough.')
    areas = {name: repo.create_area(conn, project_id, name) for name in AREAS}
    controllers = {name: repo.create_controller(conn, project_id, name, make, model)
                   for name, make, model in CONTROLLERS}

    written = rejected = 0
    for (ctrl, area, name, desc, addr, dtype, units,
         eu_lo, eu_hi, a_lo, a_hi, priority) in TAGS:
        record = {
            'controller_id': controllers[ctrl], 'area_id': areas[area],
            'tag_name': name, 'description': desc, 'address_path': addr,
            'data_type': dtype, 'eng_units': units,
            'eu_min': eu_lo, 'eu_max': eu_hi,
            'alarm_enabled': a_lo is not None or a_hi is not None,
            'alarm_lo': a_lo, 'alarm_hi': a_hi, 'alarm_priority': priority,
        }
        try:
            services.create_tag(conn, record)
            written += 1
        except services.ValidationError as exc:
            rejected += 1
            print(f'  rejected {name}: '
                  + '; '.join(f.rule for f in exc.failures))

    state = repo.status(conn)
    conn.close()
    print(f'\n{PROJECT}')
    print(f'  controllers      {state["counts"]["Controller"]}')
    print(f'  equipment areas  {state["counts"]["EquipmentArea"]}')
    print(f'  tags written     {written}'
          + (f'   rejected {rejected}' if rejected else ''))
    print(f'\n  {_db_path()}')
    return 1 if rejected else 0


if __name__ == '__main__':
    raise SystemExit(main())
