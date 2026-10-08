"""The one place tag rules live.

Every entry path calls validate_tag(): the NiceGUI editor, the REST API, the CSV
import (week 7) and the stored-record audit. The rule code is the message key, so
the wording a user sees is identical no matter which caller fired it. Nothing here
touches SQLite — the caller supplies the lookups it already has.

Rule codes (design doc, TF-R02 enforcement map):

    REQUIRED      a required field is missing or blank
    NAME_PATTERN  tag_name uses only A-Z, 0-9 and underscore
    DUPLICATE     tag_name already used on that controller
    TYPE_UNKNOWN  data type is not in the DataType lookup
    FK_MISSING    controller or area does not resolve to a record
    SCALE_ORDER   eu_max must be greater than eu_min
    ALARM_RANGE   alarm limits must fall inside the engineering span
    LENGTH        a text field is longer than the column stores
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

NAME_RE = re.compile(r'^[A-Z0-9_]+$')

# Longest value each text column will accept. The schema itself does not limit
# TEXT length, so LENGTH is an application-only rule — that is why it shows no
# database constraint in the TF-R02 enforcement map.
MAX_LEN = {
    'tag_name': 60,
    'description': 120,
    'address_path': 60,
    'eng_units': 16,
    'alarm_priority': 16,
    'notes': 500,
}

REQUIRED_FIELDS = ('tag_name', 'controller_id', 'data_type')

# Shown in the editor's rule trace, in order, whether or not they fired.
RULE_ORDER = ('REQUIRED', 'NAME_PATTERN', 'DUPLICATE', 'TYPE_UNKNOWN',
              'FK_MISSING', 'SCALE_ORDER', 'ALARM_RANGE', 'LENGTH')

RULE_DESCRIPTIONS = {
    'REQUIRED':     'Every required field carries a value',
    'NAME_PATTERN': 'Tag name uses only A-Z, 0-9 and underscore',
    'DUPLICATE':    'Tag name is unique within its controller',
    'TYPE_UNKNOWN': 'Data type exists in the lookup table',
    'FK_MISSING':   'Controller and area resolve to real records',
    'SCALE_ORDER':  'EU max is greater than EU min',
    'ALARM_RANGE':  'Alarm limits fall inside the engineering span',
    'LENGTH':       'Text fields are within their stored width',
}

BLOCK, NOTE = 'BLOCK', 'NOTE'


@dataclass(frozen=True)
class RuleFailure:
    """One rule firing on one field. Renders as a row in the editor's field
    validation table and in TF-R02's rejected-row table."""
    rule: str
    field: str
    value: Any
    message: str
    severity: str = BLOCK

    def as_dict(self) -> dict:
        return {'rule': self.rule, 'field': self.field,
                'value': '(empty)' if self.value in (None, '') else str(self.value),
                'message': self.message, 'severity': self.severity}


@dataclass
class Lookups:
    """What the caller already knows, so validation needs no database of its own.

    data_types     type_name -> is_numeric (1/0)
    controller_ids ids that exist
    area_ids       ids that exist
    existing_names tag names already on the target controller, uppercased
    """
    data_types: Mapping[str, int] = field(default_factory=dict)
    controller_ids: Iterable[int] = ()
    area_ids: Iterable[int] = ()
    existing_names: Iterable[str] = ()


def _num(value):
    """Return value as float, or None if it is blank or not a number."""
    if value is None or value == '':
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def validate_tag(record: Mapping[str, Any], lookups: Lookups) -> list[RuleFailure]:
    """Check one tag record. Returns every failure found, never raises.

    The caller decides what a failure means: the editor disables Save, the API
    returns 422, the import rejects the row, the audit lists it.
    """
    out: list[RuleFailure] = []
    g = record.get

    # ---- REQUIRED -------------------------------------------------------
    for name in REQUIRED_FIELDS:
        if g(name) in (None, ''):
            out.append(RuleFailure(
                'REQUIRED', name, g(name),
                f'{name} is required.'))

    # ---- NAME_PATTERN ---------------------------------------------------
    tag_name = g('tag_name')
    if tag_name and not NAME_RE.match(str(tag_name)):
        out.append(RuleFailure(
            'NAME_PATTERN', 'tag_name', tag_name,
            'Tag name may contain only A-Z, 0-9 and underscore. '
            'Spaces and lowercase are not permitted.'))

    # ---- DUPLICATE ------------------------------------------------------
    if tag_name:
        taken = {str(n).upper() for n in lookups.existing_names}
        if str(tag_name).upper() in taken:
            out.append(RuleFailure(
                'DUPLICATE', 'tag_name', tag_name,
                'A tag with that name already exists on this controller.'))

    # ---- TYPE_UNKNOWN ---------------------------------------------------
    data_type = g('data_type')
    is_numeric = False
    if data_type:
        if data_type not in lookups.data_types:
            allowed = ', '.join(sorted(lookups.data_types)) or 'none loaded'
            out.append(RuleFailure(
                'TYPE_UNKNOWN', 'data_type', data_type,
                f'Data type is not in the lookup list. Allowed: {allowed}.'))
        else:
            is_numeric = bool(lookups.data_types[data_type])

    # ---- FK_MISSING -----------------------------------------------------
    controller_id = g('controller_id')
    if controller_id not in (None, '') and int(controller_id) not in set(lookups.controller_ids):
        out.append(RuleFailure(
            'FK_MISSING', 'controller_id', controller_id,
            'No controller with that id exists in this project.'))

    area_id = g('area_id')
    if area_id not in (None, '') and int(area_id) not in set(lookups.area_ids):
        out.append(RuleFailure(
            'FK_MISSING', 'area_id', area_id,
            'No equipment area with that id exists in this project.'))

    # ---- SCALE_ORDER ----------------------------------------------------
    eu_min, eu_max = _num(g('eu_min')), _num(g('eu_max'))
    if eu_min is not None and eu_max is not None and eu_min >= eu_max:
        out.append(RuleFailure(
            'SCALE_ORDER', 'eu_max', g('eu_max'),
            f'EU max must be greater than EU min ({eu_min:g}).'))

    raw_min, raw_max = _num(g('raw_min')), _num(g('raw_max'))
    if raw_min is not None and raw_max is not None and raw_min >= raw_max:
        out.append(RuleFailure(
            'SCALE_ORDER', 'raw_max', g('raw_max'),
            f'Raw max must be greater than raw min ({raw_min:g}).'))

    # A numeric tag with no engineering span cannot be scaled or alarmed.
    if is_numeric and (eu_min is None or eu_max is None):
        out.append(RuleFailure(
            'REQUIRED', 'eu_min' if eu_min is None else 'eu_max', None,
            'An engineering span is required when the data type is numeric.'))

    # ---- ALARM_RANGE ----------------------------------------------------
    alarm_lo, alarm_hi = _num(g('alarm_lo')), _num(g('alarm_hi'))
    if alarm_lo is not None and alarm_hi is not None and alarm_lo >= alarm_hi:
        out.append(RuleFailure(
            'ALARM_RANGE', 'alarm_hi', g('alarm_hi'),
            f'Alarm high must be greater than alarm low ({alarm_lo:g}).'))

    if eu_min is not None and eu_max is not None:
        span = f'{eu_min:g} - {eu_max:g}'
        for name, value in (('alarm_lo', alarm_lo), ('alarm_hi', alarm_hi)):
            if value is not None and not (eu_min <= value <= eu_max):
                out.append(RuleFailure(
                    'ALARM_RANGE', name, g(name),
                    f'Alarm limit must fall inside the engineering span {span}.'))

    if not is_numeric and data_type and data_type in lookups.data_types:
        for name in ('eu_min', 'eu_max', 'alarm_lo', 'alarm_hi'):
            if _num(g(name)) is not None:
                out.append(RuleFailure(
                    'ALARM_RANGE', name, g(name),
                    f'{data_type} is not a numeric type, so it stores no scaling '
                    f'or alarm limits.', NOTE))

    # ---- LENGTH ---------------------------------------------------------
    for name, limit in MAX_LEN.items():
        value = g(name)
        if value and len(str(value)) > limit:
            out.append(RuleFailure(
                'LENGTH', name, value,
                f'{len(str(value))} characters; {limit} is the stored width.'))

    return out


def blocking(failures: Iterable[RuleFailure]) -> list[RuleFailure]:
    """Only the failures that stop a record being written."""
    return [f for f in failures if f.severity == BLOCK]


def trace(failures: Iterable[RuleFailure]) -> list[dict]:
    """Every rule in the set with its result, for the editor's trace panel."""
    fired = {f.rule for f in failures}
    return [{'rule': code,
             'description': RULE_DESCRIPTIONS[code],
             'state': 'FAIL' if code in fired else 'PASS'}
            for code in RULE_ORDER]
