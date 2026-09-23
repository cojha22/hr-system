# Meridian HR — Database Concepts Demo (Django + PostgreSQL)

A small HR web app that demonstrates **CRUD, triggers, views, stored procedures, indexing and temporal data**.

**Why Django, not MERN?** MongoDB has no SQL-style triggers or stored procedures (Atlas Triggers are cloud-only
and are not database-level procedures), so the full list can't be shown with MERN. PostgreSQL supports all of it.

---

## Project structure
```
hr_system/
├── hr/                     # Django app
│   ├── models.py           # Department, Employee, SalaryHistory, EmployeeAudit
│   ├── views.py            # CRUD + trigger/view/procedure/index/temporal endpoints
│   ├── urls.py
│   ├── templates/index.html # single-page UI (Meridian HR)
│   ├── migrations/
│   │   ├── 0001_initial.py       # tables
│   │   └── 0002_db_objects.py    # triggers, views, stored procedure, index (raw SQL)
│   └── management/commands/seed.py
├── hrsys/                  # Django project (settings, urls, wsgi)
├── manage.py
├── requirements.txt
├── .gitignore
└── README.md
```

## Where each concept lives
| Concept | Database object | Code | UI page |
|---|---|---|---|
| **CRUD** | `employee`, `department` | `hr/views.py` (`employees`, `employee_detail`) | Employees |
| **Triggers** | `trg_employee_validate`, `trg_employee_touch`, `trg_employee_audit`, `trg_salary_history` | `hr/migrations/0002_db_objects.py` | Audit Trail |
| **Views** | `v_department_summary`, `v_employee_details` | `0002_db_objects.py`, `view_*` in `views.py` | Reports |
| **Stored procedure** | `sp_give_raise` (+ function `fn_salary_as_of`) | `0002_db_objects.py`, `give_raise` in `views.py` | Payroll |
| **Indexing** | `idx_employee_salary`, `idx_employee_dept_salary`, unique email, ... | `0001`/`0002`, `index_explain`, `index_toggle` | Query Performance |
| **Temporal data** | `salary_history (valid_from, valid_to)` + `fn_salary_as_of` | `0002_db_objects.py`, `salary_history`, `salary_as_of` | Salary History |

---

## Setup for a new clone (local machine)

Each person needs their **own** virtual environment and **own** local database — neither is stored in the repo.

```powershell
git clone https://github.com/YOUR_USERNAME/hr-system.git
cd hr-system

# 1. Virtual environment
python -m venv venv
venv\Scripts\activate          # Windows PowerShell
# source venv/bin/activate     # macOS / Linux

# 2. Dependencies
pip install -r requirements.txt

# 3. Create your own local database
psql -U postgres -c "CREATE DATABASE hrdb;"

# 4. Set your own credentials for this terminal session
$env:DB_NAME="hrdb"
$env:DB_USER="postgres"
$env:DB_PASSWORD="your_own_postgres_password"

# 5. Build the schema (tables, triggers, views, procedure, index) and load demo data
python manage.py migrate
python manage.py seed --bulk 20000     # extra rows make the indexing demo meaningful

# 6. Run
python manage.py runserver             # open http://127.0.0.1:8000
```

`$env:` variables only last for the current PowerShell window — set them again if you open a new one, or
set a permanent default in `hrsys/settings.py` for your own machine only (never commit a real password there).

### Common errors on a fresh clone
| Error | Cause |
|---|---|
| `ModuleNotFoundError: No module named 'django'` | `venv` not activated, or `pip install -r requirements.txt` not run |
| `password authentication failed for user "postgres"` | `$env:DB_PASSWORD` not set, or set to the wrong password |
| `database "hrdb" does not exist` | Step 3 skipped |
| Employee list / dashboard is empty | `python manage.py seed` not run |

---

## Deploying to Render (free tier)

See the full walkthrough in project chat history, or follow this summary:

1. Add `gunicorn` and `dj-database-url` to `requirements.txt`.
2. In `hrsys/settings.py`, read `SECRET_KEY`, `DEBUG`, and `DATABASE_URL` from environment variables (see
   **Security** below) instead of hardcoding them.
3. Push the repo to GitHub (see **Pushing to GitHub**).
4. On [render.com](https://render.com): create a **Free PostgreSQL** database, then a **Free Web Service**
   pointing at the GitHub repo, with:
   - Build Command: `pip install -r requirements.txt && python manage.py migrate && python manage.py seed --bulk 20000`
   - Start Command: `gunicorn hrsys.wsgi:application`
   - Environment variables: `DATABASE_URL` (from the Render database), `SECRET_KEY` (random string), `DEBUG=0`

**Free-tier limits to know:** the free PostgreSQL database expires 30 days after creation (14-day grace
period to upgrade before it's deleted), and the free web service spins down after 15 minutes idle, so the
first request after a while takes up to ~1 minute to wake up.

---

## Security — what changes before this leaves your laptop

This project ships with settings that are convenient for local development but **not safe to deploy as-is**.
Before pushing publicly or deploying anywhere, change:

| Setting | Current (dev) | Change to |
|---|---|---|
| `SECRET_KEY` in `settings.py` | hardcoded string | `os.environ.get("SECRET_KEY", "dev-only-key")` |
| `DEBUG` in `settings.py` | `True` | `os.environ.get("DEBUG", "1") == "1"`, set `DEBUG=0` in production |
| `ALLOWED_HOSTS` in `settings.py` | `["*"]` | explicit list, e.g. `["localhost", "127.0.0.1", "your-app.onrender.com"]` |
| `DB_PASSWORD` default in `settings.py` | may contain your real password if you typed it in for convenience | generic placeholder (`"postgres"`); real password only via environment variable |
| CSRF middleware | intentionally left out to keep the demo API simple | fine for coursework behind Render's free tier; re-enable with proper tokens before handling real user data |

`DEBUG=True` shows full stack traces (file paths, settings, sometimes SQL) to anyone who hits an error —
never leave it on in a deployed app. `ALLOWED_HOSTS=["*"]` lets the app answer requests claiming any hostname.

---

## What NOT to push to GitHub

A `.gitignore` in the project root already excludes these, but check `git status` before every commit:

```gitignore
venv/
__pycache__/
*.pyc
*.pyo
.env
.env.*
db.sqlite3
*.log
.vscode/
.idea/
*.zip
```

Also **never hardcode and commit**:
- Your real PostgreSQL password
- Your `SECRET_KEY` for a deployed instance
- Any `.env` file with real credentials

If a real password is ever committed and pushed, **change that password immediately** — removing it from
Git history afterwards (`git filter-repo`, or deleting and re-pushing the repo) does not undo the exposure.

## Pushing to GitHub (first time)

```powershell
cd E:\A_database\hr_system
git init
git add .
git status              # confirm venv/, __pycache__/, and secrets are NOT listed
git commit -m "Initial commit: HR database system"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/hr-system.git
git push -u origin main
```

## Collaborating with others

1. On GitHub: **Settings → Collaborators → Add people**, invite by username/email; they accept via email or
   GitHub notifications.
2. Each collaborator clones the repo and follows **Setup for a new clone** above (their own venv, their own DB).
3. Recommended day-to-day workflow:
```powershell
git pull origin main            # before starting work
git checkout -b feature-name    # work on a branch, not directly on main
# ... make changes ...
git add .
git commit -m "describe the change"
git push origin feature-name
# open a Pull Request on GitHub, merge into main after review
```
4. Always `git pull` before `git push` on a shared branch to avoid rejected pushes.
5. Merge conflicts show up as `<<<<<<<` / `=======` / `>>>>>>>` markers in the file — edit to keep the
   correct content, delete the markers, then `git add`, `git commit`, `git push` as normal.

---

## Suggested demo script
1. **CRUD (Employees)** — add, edit, delete an employee. Try salary `0` → rejected by a **trigger**.
2. **Audit Trail (Triggers)** — every action above appears with a field-level diff. `updated_at` changes by itself.
3. **Reports (Views)** — department stats and employee directory; change data and refresh to see it update live.
4. **Payroll (Stored procedure)** — give a department a raise; check Audit Trail (one UPDATE per employee) and Salary History (new versions).
5. **Query Performance (Indexing)** — drop the index → Analyse (full table scan) → create the index → Analyse (index scan, much faster on 20k+ rows).
6. **Salary History (Temporal)** — pick Alice Johnson, look up her salary "as of" a past date; change her salary and watch a new timeline entry appear.

## Resetting the local database
```powershell
dropdb hrdb
createdb hrdb
python manage.py migrate
python manage.py seed --bulk 20000
```
