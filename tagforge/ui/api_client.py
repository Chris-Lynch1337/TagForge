"""Thin wrapper over the REST API.

The UI imports this and nothing else from the back end. If a screen ever needs a
new piece of data, it gets a new endpoint here rather than a database call — that
separation is what makes the API the single enforcement point for the rules.

httpx ships with NiceGUI, so this adds no dependency.
"""
from __future__ import annotations

import httpx

from tagforge.api import API_BASE

TIMEOUT = 5.0


class ApiError(Exception):
    """The API could not be reached, or answered with something unexpected."""


def _get(path: str, **params):
    clean = {k: v for k, v in params.items() if v not in (None, '')}
    try:
        r = httpx.get(f'{API_BASE}{path}', params=clean, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPError as exc:
        raise ApiError(f'GET {path} failed: {exc}') from exc


def _post(path: str, payload: dict):
    try:
        r = httpx.post(f'{API_BASE}{path}', json=payload, timeout=TIMEOUT)
        return r.status_code, r.json()
    except httpx.HTTPError as exc:
        raise ApiError(f'POST {path} failed: {exc}') from exc


# --------------------------------------------------------------- reads

def status() -> dict:
    return _get('/status')


def projects() -> list[dict]:
    return _get('/projects')


def controllers(project_id=None) -> list[dict]:
    return _get('/controllers', project_id=project_id)


def areas(project_id=None) -> list[dict]:
    return _get('/areas', project_id=project_id)


def data_types() -> list[dict]:
    return _get('/data-types')


def tags(**filters) -> dict:
    """Returns {'rows': [...], 'tags_in_project': n, 'matching': n, 'flagged': n}."""
    return _get('/tags', **filters)


def tag(tag_id: int) -> dict:
    return _get(f'/tags/{tag_id}')


# --------------------------------------------------------------- writes

def check(record: dict) -> dict:
    """Validate without writing. Returns {'valid', 'failures', 'trace', ...}."""
    _, body = _post('/tags/check', record)
    return body


def create_tag(record: dict) -> tuple[int, dict]:
    """The write path. 201 with the stored tag, or 422 with the failures."""
    return _post('/tags', record)
