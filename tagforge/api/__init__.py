"""Local REST API. The NiceGUI front end talks to this, never to SQLite."""
from .app import API_BASE, API_HOST, API_PORT, create_app, start_background

__all__ = ['create_app', 'start_background', 'API_BASE', 'API_HOST', 'API_PORT']
