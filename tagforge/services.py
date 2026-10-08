"""Business rules. Sits between the API routes and the repository.

Routes do HTTP. The repository does SQL. This layer decides what a request means:
it gathers the lookups a rule set needs, runs validation, and only then asks the
repository to write. Nothing here builds SQL and nothing here knows about HTTP,
so the CSV import in week 7 can call the same functions the API calls.
"""
from __future__ import annotations

from typing import Any, Mapping

from tagforge.db import repository as repo
from tagforge.validation import Lookups, RuleFailure, blocking, trace, validate_tag


class ValidationError(Exception):
    """Raised when a record breaks at least one blocking rule.

    Carries the failures so the caller can render them: the API turns them into
    a 422 body, the editor into table rows, the import into rejected rows.
    """

    def __init__(self, failures: list[RuleFailure]):
        self.failures = failures
        super().__init__(f'{len(failures)} rule(s) failed')

    def as_dict(self) -> dict:
        return {'error': 'validation_failed',
                'failures': [f.as_dict() for f in self.failures]}


def _lookups_for(conn, controller_id, exclude_tag_id=None) -> Lookups:
    """Collect what validate_tag() needs, scoped to the record's own project."""
    project_id = None
    if controller_id is not None:
        row = conn.execute('SELECT project_id FROM Controller WHERE controller_id = ?',
                           (controller_id,)).fetchone()
        project_id = row['project_id'] if row else None

    return Lookups(
        data_types={d['type_name']: d['is_numeric'] for d in repo.list_data_types(conn)},
        controller_ids=[c['controller_id'] for c in repo.list_controllers(conn)],
        # Areas belong to a project, so a tag may only use its own project's areas.
        area_ids=[a['area_id'] for a in repo.list_areas(conn, project_id)],
        existing_names=(repo.tag_names_on_controller(conn, controller_id, exclude_tag_id)
                        if controller_id is not None else []),
    )


def check_tag(conn, record: Mapping[str, Any], exclude_tag_id=None) -> list[RuleFailure]:
    """Run the rules without writing anything. The editor calls this on every edit."""
    controller_id = record.get('controller_id')
    controller_id = int(controller_id) if controller_id not in (None, '') else None
    return validate_tag(record, _lookups_for(conn, controller_id, exclude_tag_id))


def check_tag_trace(conn, record: Mapping[str, Any], exclude_tag_id=None) -> dict:
    """Failures plus the full pass/fail list of every rule, for the editor panel."""
    failures = check_tag(conn, record, exclude_tag_id)
    blockers = blocking(failures)
    return {
        'valid': not blockers,
        'blocking_count': len(blockers),
        'failures': [f.as_dict() for f in failures],
        'trace': trace(failures),
    }


def create_tag(conn, record: Mapping[str, Any]) -> dict:
    """Validate, then write. Returns the stored tag as the browser would show it.

    This is the write path the week 3 status report refers to: a tag goes in
    through the service layer, is committed, and can be read back.
    """
    failures = check_tag(conn, record)
    if blocking(failures):
        raise ValidationError(blocking(failures))

    type_row = conn.execute('SELECT data_type_id FROM DataType WHERE type_name = ?',
                            (record['data_type'],)).fetchone()

    row = dict(record)
    row['data_type_id'] = type_row['data_type_id']
    row['alarm_enabled'] = 1 if record.get('alarm_enabled') else 0
    for key in ('area_id', 'controller_id'):
        if row.get(key) in ('', None):
            row[key] = None
        else:
            row[key] = int(row[key])

    tag_id = repo.create_tag(conn, row)
    return repo.get_tag(conn, tag_id)


def browse(conn, **filters) -> dict:
    """Everything the Tag Browser needs for one render: rows plus the tile counts."""
    rows = repo.list_tags(conn, **filters)

    project_id = filters.get('project_id')
    if project_id is None and filters.get('controller_id') is not None:
        row = conn.execute('SELECT project_id FROM Controller WHERE controller_id = ?',
                           (filters['controller_id'],)).fetchone()
        project_id = row['project_id'] if row else None

    in_project = len(repo.list_tags(conn, project_id=project_id)) if project_id else len(
        repo.list_tags(conn))

    return {'rows': rows, 'tags_in_project': in_project, 'matching': len(rows),
            'flagged': audit_count(conn, project_id)}


def audit_count(conn, project_id=None) -> int:
    """How many stored tags would fail validation today.

    Records can go bad without being edited — an area is renamed, a rule is
    tightened. The browser's third tile reports this.
    """
    bad = 0
    for row in repo.list_tags(conn, project_id=project_id):
        if blocking(check_tag(conn, row, exclude_tag_id=row['tag_id'])):
            bad += 1
    return bad
