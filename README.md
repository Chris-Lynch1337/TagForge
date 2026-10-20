# TagForge

A local-first database utility for creating, validating, organizing and retrieving
industrial automation tag information.

On a typical controls project the tag list is spread across the PLC program, the
HMI or SCADA application, a commissioning spreadsheet and a set of field notes.
Each copy is edited by a different person at a different time and none of them is
authoritative. TagForge gives that list one home, validates it on the way in, and
exports it back out in a documented format.

Course project for **SDEV-435 Applied Software Practice I**, Champlain College.
All sample data in this repository is fictional.

## Running it

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
python main.py
```

| Service | Address |
| --- | --- |
| NiceGUI front end | http://127.0.0.1:8001 |
| Flask REST API | http://127.0.0.1:8002/api |

The database is created on first run. Both services bind to `127.0.0.1` only.

## Architecture

Three layers, with one rule about who may talk to whom:

```
NiceGUI pages ──HTTP──▶ Flask routes ──▶ services ──▶ repository ──▶ SQLite
 tagforge/ui            tagforge/api     services.py   db/repository.py
```

The UI never touches SQLite. Only `db/repository.py` builds SQL — the service
layer asks it for lookups rather than running queries of its own. Business rules
live in `services.py`, so the CSV import can call the same functions the API calls.

### Validation

`tagforge/validation.py` is the single rule set. The NiceGUI editor, the REST API,
the CSV import and the stored-record audit all call `validate_tag()`, and the rule
code is the message key — so the wording a user sees is identical no matter which
caller fired it.

| Rule | Checks | Database backstop |
| --- | --- | --- |
| `REQUIRED` | required fields carry a value | `NOT NULL` |
| `NAME_PATTERN` | tag name is `A-Z`, `0-9`, `_` only | `CHECK` |
| `DUPLICATE` | tag name unique within its controller | `UNIQUE` |
| `TYPE_UNKNOWN` | data type exists in the lookup | `FOREIGN KEY` |
| `FK_MISSING` | controller and area resolve | `FOREIGN KEY` |
| `SCALE_ORDER` | `eu_max` greater than `eu_min` | `CHECK` |
| `ALARM_RANGE` | alarm limits inside the engineering span | — |
| `LENGTH` | text fields within their stored width | — |

The two rules with no database backstop rest entirely on application code. That is
deliberate and is reported in the TF-R02 validation report.

### Data model

Seven tables in three groups: `Project`, `Controller` and `Tag` as the core
records; `DataType` and `EquipmentArea` as lookups; `ImportBatch` and
`ImportError` as the audit trail behind the import report. Uniqueness is scoped
rather than global — a tag name is unique within its controller, not across the
database, because the same name legitimately appears on more than one controller.

## Project status

| Work package | Budget | Status |
| --- | --- | --- |
| Requirements, scope and planning | 8 h | Complete |
| Domain model and SQLite database | 12 h | Complete |
| Flask API and service layer | 18 h | Reads, search and the create path |
| NiceGUI user interface | 20 h | Browser with live search; editor read-only |
| Validation and CSV import/export | 16 h | Rule set done; import not started |
| Testing, integration, defect correction | 14 h | Not started |
| Deployment, documentation, walkthrough | 12 h | Not started |

Not yet built: update and delete endpoints, the editor write path, CSV
import/export, and the two report views.

## Checks

```bash
python -m tools.smoke_create
```

Builds a schema in a throwaway database, creates a tag through the service layer,
reopens the file and reads it back, fires each of the eight rules, confirms
nothing was written by the rejected records, and exercises free-text search
against tag name, description and PLC address including wildcard escaping.

```bash
python -m tools.demo_shared_rules
```

Sends one deliberately broken record through the service layer and through the
REST API and asserts both callers get byte-identical messages from the shared
rule set.
