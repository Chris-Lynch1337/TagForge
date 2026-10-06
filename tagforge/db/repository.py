"""The only module that reads or writes SQLite.

Everything above this layer — services, the API, the UI — works with plain dicts
and never builds SQL. That keeps the persistence choice replaceable and makes this
the single place to test transactions, parameter binding and constraint handling.

Week 3 scope: reads, plus the create path. Update and delete are week 4.
"""
from __future__ import annotations

import sqlite3
from typing import Any, Mapping

from .connection import get_connection, DB_PATH
from .sqlite import init_schema, SCHEMA_VERSION


def _rows(cur) -> list[dict]:
    return [dict(r) for r in cur.fetchall()]


# --------------------------------------------------------------- status

def status(conn: sqlite3.Connection) -> dict:
    """What the header pill and the maintenance diagnostics panel need."""
    counts = {}
    for table in ('Project', 'Controller', 'Tag', 'DataType',
                  'EquipmentArea', 'ImportBatch'):
        counts[table] = conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
    return {
        'db_path': str(DB_PATH),
        'schema_version': conn.execute('PRAGMA user_version').fetchone()[0],
        'expected_schema_version': SCHEMA_VERSION,
        'foreign_keys': bool(conn.execute('PRAGMA foreign_keys').fetchone()[0]),
        'counts': counts,
    }


# --------------------------------------------------------------- lookups

def list_data_types(conn) -> list[dict]:
    return _rows(conn.execute(
        'SELECT data_type_id, type_name, category, is_numeric '
        'FROM DataType ORDER BY data_type_id'))


def list_projects(conn) -> list[dict]:
    return _rows(conn.execute("""
        SELECT p.project_id, p.project_name, p.site_label, p.description,
               (SELECT COUNT(*) FROM Controller c
                 WHERE c.project_id = p.project_id)            AS controller_count,
               (SELECT COUNT(*) FROM Tag t
                  JOIN Controller c2 ON c2.controller_id = t.controller_id
                 WHERE c2.project_id = p.project_id)           AS tag_count
          FROM Project p
      ORDER BY p.project_name"""))


def list_controllers(conn, project_id: int | None = None) -> list[dict]:
    sql = """
        SELECT c.controller_id, c.project_id, c.controller_name, c.make, c.model,
               (SELECT COUNT(*) FROM Tag t
                 WHERE t.controller_id = c.controller_id) AS tag_count
          FROM Controller c"""
    args: list[Any] = []
    if project_id is not None:
        sql += ' WHERE c.project_id = ?'
        args.append(project_id)
    return _rows(conn.execute(sql + ' ORDER BY c.controller_name', args))


def list_areas(conn, project_id: int | None = None) -> list[dict]:
    sql = 'SELECT area_id, project_id, area_name, description FROM EquipmentArea'
    args: list[Any] = []
    if project_id is not None:
        sql += ' WHERE project_id = ?'
        args.append(project_id)
    return _rows(conn.execute(sql + ' ORDER BY area_name', args))


# --------------------------------------------------------------- tags

# Joined so the browser gets display names, not ids, in one round trip.
TAG_SELECT = """
    SELECT t.tag_id, t.controller_id, t.tag_name, t.description, t.address_path,
           t.eng_units, t.raw_min, t.raw_max, t.eu_min, t.eu_max,
           t.alarm_enabled, t.alarm_lo, t.alarm_hi, t.alarm_priority, t.notes,
           t.created_utc, t.updated_utc,
           d.type_name  AS data_type, d.is_numeric,
           t.area_id, a.area_name,
           c.controller_name, c.project_id
      FROM Tag t
      JOIN Controller c ON c.controller_id = t.controller_id
      JOIN DataType   d ON d.data_type_id  = t.data_type_id
 LEFT JOIN EquipmentArea a ON a.area_id    = t.area_id"""


def list_tags(conn, *, controller_id=None, project_id=None, area_id=None,
              data_type=None, alarmed_only=False) -> list[dict]:
    """Filtered tag list. Every filter is optional and they combine with AND.

    Free-text search is deliberately absent: it is not wired to the API yet
    (week 3 status report, M2 slip risk).
    """
    where, args = [], []
    if controller_id is not None:
        where.append('t.controller_id = ?'); args.append(controller_id)
    if project_id is not None:
        where.append('c.project_id = ?'); args.append(project_id)
    if area_id is not None:
        where.append('t.area_id = ?'); args.append(area_id)
    if data_type:
        where.append('d.type_name = ?'); args.append(data_type)
    if alarmed_only:
        where.append('t.alarm_enabled = 1')

    sql = TAG_SELECT + (' WHERE ' + ' AND '.join(where) if where else '')
    return _rows(conn.execute(sql + ' ORDER BY t.tag_name', args))


def get_tag(conn, tag_id: int) -> dict | None:
    row = conn.execute(TAG_SELECT + ' WHERE t.tag_id = ?', (tag_id,)).fetchone()
    return dict(row) if row else None


def tag_names_on_controller(conn, controller_id: int, exclude_tag_id=None) -> list[str]:
    """Feeds the DUPLICATE rule. exclude_tag_id lets a record keep its own name."""
    sql = 'SELECT tag_name FROM Tag WHERE controller_id = ?'
    args: list[Any] = [controller_id]
    if exclude_tag_id is not None:
        sql += ' AND tag_id <> ?'
        args.append(exclude_tag_id)
    return [r['tag_name'] for r in conn.execute(sql, args).fetchall()]


INSERT_COLUMNS = ('controller_id', 'data_type_id', 'area_id', 'tag_name',
                  'description', 'address_path', 'eng_units',
                  'raw_min', 'raw_max', 'eu_min', 'eu_max',
                  'alarm_enabled', 'alarm_lo', 'alarm_hi', 'alarm_priority', 'notes')


def create_tag(conn, record: Mapping[str, Any]) -> int:
    """Insert one tag and return its id. Commits, or rolls back and re-raises.

    The record arrives already validated; the database constraints behind this
    are the backstop, not the first line of defense.
    """
    values = [record.get(c) for c in INSERT_COLUMNS]
    placeholders = ', '.join('?' * len(INSERT_COLUMNS))
    with conn:
        cur = conn.execute(
            f'INSERT INTO Tag ({", ".join(INSERT_COLUMNS)}) VALUES ({placeholders})',
            values)
    return cur.lastrowid


# --------------------------------------------------------------- project setup

def create_project(conn, name: str, site_label=None, description=None) -> int:
    with conn:
        cur = conn.execute(
            'INSERT INTO Project (project_name, site_label, description) VALUES (?, ?, ?)',
            (name, site_label, description))
    return cur.lastrowid


def create_controller(conn, project_id: int, name: str, make=None, model=None) -> int:
    with conn:
        cur = conn.execute(
            'INSERT INTO Controller (project_id, controller_name, make, model) '
            'VALUES (?, ?, ?, ?)', (project_id, name, make, model))
    return cur.lastrowid


def create_area(conn, project_id: int, name: str, description=None) -> int:
    with conn:
        cur = conn.execute(
            'INSERT INTO EquipmentArea (project_id, area_name, description) '
            'VALUES (?, ?, ?)', (project_id, name, description))
    return cur.lastrowid


def open_database(db_path=DB_PATH) -> sqlite3.Connection:
    """Open (creating if needed), apply the schema, and hand back the connection."""
    conn = get_connection(db_path)
    init_schema(conn)
    return conn
