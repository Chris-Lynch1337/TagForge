"""REST endpoints.

Week 3 scope, matching the status report: reads, plus POST /api/tags as the write
path. Update and delete are not written yet, and free-text search is not wired —
both are week 4 work and both are named in the week 3 risk section.

A route's whole job is HTTP: parse the request, call a service, shape the response.
No SQL and no business rules live here.
"""
from __future__ import annotations

import sqlite3

from flask import Blueprint, current_app, g, jsonify, request

from tagforge import services
from tagforge.db import repository as repo

bp = Blueprint('api', __name__)


def db():
    """One connection per request, closed on teardown."""
    if 'conn' not in g:
        g.conn = repo.open_database(current_app.config.get('DB_PATH')
                                    or repo.DB_PATH)
    return g.conn


@bp.teardown_request
def _close(exc):
    conn = g.pop('conn', None)
    if conn is not None:
        conn.close()


def _int(name):
    value = request.args.get(name)
    return int(value) if value not in (None, '') else None


# --------------------------------------------------------------- status

@bp.get('/status')
def get_status():
    return jsonify(repo.status(db()))


# --------------------------------------------------------------- lookups

@bp.get('/projects')
def get_projects():
    return jsonify(repo.list_projects(db()))


@bp.get('/controllers')
def get_controllers():
    return jsonify(repo.list_controllers(db(), _int('project_id')))


@bp.get('/areas')
def get_areas():
    return jsonify(repo.list_areas(db(), _int('project_id')))


@bp.get('/data-types')
def get_data_types():
    return jsonify(repo.list_data_types(db()))


# --------------------------------------------------------------- tags

@bp.get('/tags')
def get_tags():
    """Filtered tag list plus the browser's tile counts.

    Filters: project_id, controller_id, area_id, data_type, alarmed_only.
    """
    return jsonify(services.browse(
        db(),
        project_id=_int('project_id'),
        controller_id=_int('controller_id'),
        area_id=_int('area_id'),
        data_type=request.args.get('data_type') or None,
        alarmed_only=request.args.get('alarmed_only') in ('1', 'true', 'True'),
    ))


@bp.get('/tags/<int:tag_id>')
def get_one_tag(tag_id):
    tag = repo.get_tag(db(), tag_id)
    if tag is None:
        return jsonify({'error': 'not_found', 'tag_id': tag_id}), 404
    return jsonify(tag)


@bp.post('/tags/check')
def post_check():
    """Run the rules without writing. The editor calls this as fields change."""
    record = request.get_json(silent=True) or {}
    exclude = record.pop('tag_id', None)
    return jsonify(services.check_tag_trace(db(), record, exclude))


@bp.post('/tags')
def post_tag():
    """The write path: validate, insert, return the stored record."""
    record = request.get_json(silent=True) or {}
    try:
        return jsonify(services.create_tag(db(), record)), 201
    except services.ValidationError as exc:
        return jsonify(exc.as_dict()), 422
    except sqlite3.IntegrityError as exc:
        # The database caught something validation did not. That is a bug in the
        # rule set rather than user error, so it is reported separately.
        return jsonify({'error': 'constraint_failed', 'detail': str(exc)}), 409
