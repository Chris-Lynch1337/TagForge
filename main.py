"""TagForge entry point.

Starts the Flask API on a background thread, then runs the NiceGUI front end in
the foreground. The UI reaches the database only through the API, so both have to
be up for a screen to show anything.

    python main.py        ->  UI  http://127.0.0.1:8001
                              API http://127.0.0.1:8002/api
"""
from nicegui import ui

from tagforge.api import API_BASE, start_background
from tagforge.db import repository as repo
import tagforge.ui.pages  # noqa: F401  (registers every @ui.page route)

if __name__ in {'__main__', '__mp_main__'}:
    
    conn = repo.open_database()
    state = repo.status(conn)
    conn.close()
    print(f"database : {state['db_path']}  (schema v{state['schema_version']})")
    print(f"api      : {API_BASE}")

    start_background()
    # reload=False: the reloader re-executes this module, which would start a
    # second API thread on the same port.
    ui.run(title='TagForge', host='127.0.0.1', port=8001, dark=True, reload=False)
