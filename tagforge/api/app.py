"""Flask application factory and the background thread that serves it.

The API binds to 127.0.0.1 only. It is a local application, not a service, and
nothing outside this machine should be able to reach the database through it.
"""
from __future__ import annotations

import threading

from flask import Flask

API_HOST = '127.0.0.1'
API_PORT = 8002
API_BASE = f'http://{API_HOST}:{API_PORT}/api'


def create_app(db_path=None) -> Flask:
    app = Flask(__name__)
    app.config['DB_PATH'] = db_path
    app.config['JSON_SORT_KEYS'] = False

    from .routes import bp
    app.register_blueprint(bp, url_prefix='/api')
    return app


def start_background(db_path=None) -> threading.Thread:
    """Serve the API on a daemon thread so main.py can run the UI in the foreground.

    Werkzeug's dev server is fine here: one local user, one process. A production
    deployment would put this behind a real WSGI server, which is a week 12 concern.
    """
    app = create_app(db_path)

    def run():
        app.run(host=API_HOST, port=API_PORT, debug=False,
                use_reloader=False, threaded=True)

    thread = threading.Thread(target=run, name='tagforge-api', daemon=True)
    thread.start()
    return thread
