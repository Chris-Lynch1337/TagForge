"""One rule set, two entry paths — the walkthrough's reusable-code demonstration.

Sends the same broken tag record through the two callers that exist today:

    1. the service layer, which is what the NiceGUI editor calls
    2. the REST API over localhost, which is what an external caller uses

Both answers come from tagforge/validation.py. The rule codes and the message
text are identical because the rule code IS the message key — no caller writes
its own wording. The CSV import becomes the third caller and needs no
new rules.

Start the application first (python main.py), then:

    python -m tools.demo_shared_rules
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx                                       # noqa: E402

from tagforge import services                      # noqa: E402
from tagforge.api import API_BASE                  # noqa: E402
from tagforge.db import repository as repo         # noqa: E402

LINE = '-' * 72

# Three rules broken at once: a name with spaces and lowercase, an alarm limit
# above the top of the engineering span, and a description past its stored width.
BROKEN = {
    'tag_name': 'Feed Pump Amps',
    'description': 'deliberately invalid record — ' + 'x' * 160,
    'address_path': 'N7:20',
    'data_type': 'REAL',
    'eng_units': 'A',
    'eu_min': 0.0,
    'eu_max': 600.0,
    'alarm_enabled': True,
    'alarm_hi': 750.0,
}


def show(title, failures):
    print(f'\n{title}\n{LINE}')
    for f in sorted(failures, key=lambda x: (x['rule'], x['field'])):
        print(f"  {f['rule']:<14} {f['field']:<12} {f['message']}")
    return {(f['rule'], f['field'], f['message']) for f in failures}


def main() -> int:
    conn = repo.open_database()
    controller = next(iter(repo.list_controllers(conn)), None)
    if controller is None:
        print('No controllers yet. Run:  python -m tools.seed_demo')
        return 1
    record = {**BROKEN, 'controller_id': controller['controller_id']}

    # 1. what the editor calls
    direct = [f.as_dict() for f in services.check_tag(conn, record)]
    conn.close()
    a = show('1.  Service layer  —  tagforge/services.py  (the NiceGUI editor)', direct)

    # 2. what any external caller gets
    try:
        r = httpx.post(f'{API_BASE}/tags', json=record, timeout=5.0)
    except httpx.HTTPError:
        print(f'\nCould not reach {API_BASE}. Start the app first: python main.py')
        return 1
    b = show(f'2.  REST API  —  POST {API_BASE}/tags  ->  HTTP {r.status_code}',
             r.json().get('failures', []))

    print(f'\n{LINE}')
    same = a == b
    print(f'  identical rule codes, fields and wording from both callers: '
          f'{"YES" if same else "NO"}')
    print(f'  rules broken: {", ".join(sorted({x[0] for x in a}))}')
    print(f'  rows written to the database: 0  (the API answered {r.status_code},'
          f' not 201)')
    return 0 if same else 1


if __name__ == '__main__':
    raise SystemExit(main())
