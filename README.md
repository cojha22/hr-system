# Employee DB - Database Concepts Demo (Django + PostgreSQL)

A small web app that demonstrates **CRUD, triggers, views, stored procedures, indexing and temporal data**.

**Why Django, not MERN?** MongoDB has no SQL-style triggers or stored procedures (Atlas Triggers are cloud-only
and are not database-level procedures), so the full list can't be shown with MERN. PostgreSQL supports all of it.

## Setup
```bash
# 1. PostgreSQL running, then create the database
createdb hrdb            # or: psql -c "CREATE DATABASE hrdb;"

# 2. Python deps
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. (optional) DB credentials - defaults: user=postgres password=postgres host=localhost port=5432
export DB_NAME=hrdb DB_USER=postgres DB_PASSWORD=postgres

# 4. Build schema (tables + triggers + views + procedure + index) and load data
python manage.py migrate
python manage.py seed --bulk 50000     # 50k extra rows make the indexing demo obvious

# 5. Run
python manage.py runserver             # open http://127.0.0.1:8000
```

## Where each concept lives
| Concept | Database object | Code | UI tab |
|---|---|---|---|
| **CRUD** | `employee`, `department` | `hr/views.py` (`employees`, `employee_detail`) | 1. CRUD |
| **Triggers** | `trg_employee_validate`, `trg_employee_touch`, `trg_employee_audit`, `trg_salary_history` | `hr/migrations/0002_db_objects.py` | 2. Triggers |
| **Views** | `v_department_summary`, `v_employee_details` | `0002_db_objects.py`, `view_*` in `views.py` | 3. Views |
| **Stored procedure** | `sp_give_raise` (+ function `fn_salary_as_of`) | `0002_db_objects.py`, `give_raise` in `views.py` | 4. Stored procedure |
| **Indexing** | `idx_employee_salary`, `idx_employee_dept_salary`, unique email, ... | `0001`/`0002`, `index_explain`, `index_toggle` | 5. Indexing |
| **Temporal data** | `salary_history (valid_from, valid_to)` + `fn_salary_as_of` | `0002_db_objects.py`, `salary_history`, `salary_as_of` | 6. Temporal |

## Suggested demo script
1. **CRUD** - add, edit, delete an employee. Try salary `0` -> rejected by a **trigger**.
2. **Triggers** - open the audit tab; each action you did appears with a field-level diff. `updated_at` changes by itself.
3. **Views** - see department stats; go change data and refresh.
4. **Stored procedure** - give Engineering a 10% raise; check the audit log (one UPDATE per employee, fired by the trigger).
5. **Indexing** - Drop index -> Run (Seq Scan) -> Create index -> Run (Index scan, much faster on 50k rows).
6. **Temporal** - pick Alice Johnson, query "as of 2024-01-01" -> 70,000; change her salary and see a new version.

## Notes
- CSRF middleware is intentionally off to keep the demo API simple. Don't deploy as-is.
- To reset: `dropdb hrdb && createdb hrdb && python manage.py migrate && python manage.py seed`.
