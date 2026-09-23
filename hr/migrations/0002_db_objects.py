"""
Raw PostgreSQL objects: triggers, views, stored procedure/function, extra index.
Each statement is a separate list item so Django runs it verbatim (no SQL splitting).
"""
from django.db import migrations

FORWARD = [
    # ------------------------------------------------------------------ TRIGGERS
    # 1) BEFORE trigger: validation (can reject the write)
    """
    CREATE OR REPLACE FUNCTION fn_employee_validate() RETURNS trigger AS $$
    BEGIN
        IF NEW.salary <= 0 THEN
            RAISE EXCEPTION 'salary must be greater than zero (got %)', NEW.salary;
        END IF;
        IF TG_OP = 'UPDATE' AND NEW.salary < OLD.salary * 0.5 THEN
            RAISE EXCEPTION 'salary cut of more than 50%% is not allowed (% -> %)', OLD.salary, NEW.salary;
        END IF;
        RETURN NEW;
    END; $$ LANGUAGE plpgsql;
    """,
    """CREATE TRIGGER trg_employee_validate BEFORE INSERT OR UPDATE ON employee
       FOR EACH ROW EXECUTE FUNCTION fn_employee_validate();""",

    # 2) BEFORE trigger: auto-maintain updated_at
    """
    CREATE OR REPLACE FUNCTION fn_employee_touch() RETURNS trigger AS $$
    BEGIN
        NEW.updated_at := clock_timestamp();
        RETURN NEW;
    END; $$ LANGUAGE plpgsql;
    """,
    """CREATE TRIGGER trg_employee_touch BEFORE UPDATE ON employee
       FOR EACH ROW EXECUTE FUNCTION fn_employee_touch();""",

    # 3) AFTER trigger: audit log of every INSERT / UPDATE / DELETE
    """
    CREATE OR REPLACE FUNCTION fn_employee_audit() RETURNS trigger AS $$
    BEGIN
        IF TG_OP = 'INSERT' THEN
            INSERT INTO employee_audit(employee_id, action, old_data, new_data, changed_at)
            VALUES (NEW.id, 'INSERT', NULL, to_jsonb(NEW), clock_timestamp());
            RETURN NEW;
        ELSIF TG_OP = 'UPDATE' THEN
            INSERT INTO employee_audit(employee_id, action, old_data, new_data, changed_at)
            VALUES (NEW.id, 'UPDATE', to_jsonb(OLD), to_jsonb(NEW), clock_timestamp());
            RETURN NEW;
        ELSE
            INSERT INTO employee_audit(employee_id, action, old_data, new_data, changed_at)
            VALUES (OLD.id, 'DELETE', to_jsonb(OLD), NULL, clock_timestamp());
            RETURN OLD;
        END IF;
    END; $$ LANGUAGE plpgsql;
    """,
    """CREATE TRIGGER trg_employee_audit AFTER INSERT OR UPDATE OR DELETE ON employee
       FOR EACH ROW EXECUTE FUNCTION fn_employee_audit();""",

    # 4) AFTER trigger: temporal versioning of salary
    """
    CREATE OR REPLACE FUNCTION fn_salary_history() RETURNS trigger AS $$
    BEGIN
        IF TG_OP = 'INSERT' THEN
            INSERT INTO salary_history(employee_id, salary, valid_from, valid_to)
            VALUES (NEW.id, NEW.salary, clock_timestamp(), NULL);
        ELSIF NEW.salary IS DISTINCT FROM OLD.salary THEN
            UPDATE salary_history SET valid_to = clock_timestamp()
             WHERE employee_id = NEW.id AND valid_to IS NULL;
            INSERT INTO salary_history(employee_id, salary, valid_from, valid_to)
            VALUES (NEW.id, NEW.salary, clock_timestamp(), NULL);
        END IF;
        RETURN NEW;
    END; $$ LANGUAGE plpgsql;
    """,
    """CREATE TRIGGER trg_salary_history AFTER INSERT OR UPDATE ON employee
       FOR EACH ROW EXECUTE FUNCTION fn_salary_history();""",

    # ------------------------------------------------------------------ VIEWS
    """
    CREATE VIEW v_department_summary AS
    SELECT d.id, d.name AS department,
           COUNT(e.id)                          AS headcount,
           COALESCE(ROUND(AVG(e.salary), 2), 0) AS avg_salary,
           COALESCE(MAX(e.salary), 0)           AS max_salary,
           COALESCE(SUM(e.salary), 0)           AS payroll
    FROM department d
    LEFT JOIN employee e ON e.department_id = d.id AND e.is_active
    GROUP BY d.id, d.name;
    """,
    """
    CREATE VIEW v_employee_details AS
    SELECT e.id, e.name, e.email, d.name AS department, e.salary, e.hire_date,
           date_part('year', age(current_date, e.hire_date))::int AS years_of_service,
           CASE WHEN e.salary >= 100000 THEN 'Senior band'
                WHEN e.salary >= 60000  THEN 'Mid band'
                ELSE 'Junior band' END AS salary_band
    FROM employee e JOIN department d ON d.id = e.department_id
    WHERE e.is_active;
    """,

    # ------------------------------------------------------------------ STORED PROCEDURE / FUNCTION
    """
    CREATE OR REPLACE PROCEDURE sp_give_raise(p_dept_id int, p_percent numeric, INOUT p_updated int DEFAULT 0)
    LANGUAGE plpgsql AS $$
    BEGIN
        IF p_percent <= 0 OR p_percent > 50 THEN
            RAISE EXCEPTION 'raise percent must be between 0 and 50 (got %)', p_percent;
        END IF;
        UPDATE employee
           SET salary = ROUND(salary * (1 + p_percent / 100), 2)
         WHERE department_id = p_dept_id AND is_active;
        GET DIAGNOSTICS p_updated = ROW_COUNT;      -- the triggers above fire for every row touched
    END; $$;
    """,
    """
    CREATE OR REPLACE FUNCTION fn_salary_as_of(p_emp int, p_ts timestamptz) RETURNS numeric
    LANGUAGE sql STABLE AS $$
        SELECT salary FROM salary_history
         WHERE employee_id = p_emp AND valid_from <= p_ts AND (valid_to IS NULL OR valid_to > p_ts)
         ORDER BY valid_from DESC LIMIT 1
    $$;
    """,

    # ------------------------------------------------------------------ INDEX (toggled from the UI)
    "CREATE INDEX idx_employee_salary ON employee (salary);",
]

BACKWARD = [
    "DROP INDEX IF EXISTS idx_employee_salary;",
    "DROP FUNCTION IF EXISTS fn_salary_as_of(int, timestamptz);",
    "DROP PROCEDURE IF EXISTS sp_give_raise(int, numeric, int);",
    "DROP VIEW IF EXISTS v_employee_details;",
    "DROP VIEW IF EXISTS v_department_summary;",
    "DROP TRIGGER IF EXISTS trg_salary_history ON employee;",
    "DROP TRIGGER IF EXISTS trg_employee_audit ON employee;",
    "DROP TRIGGER IF EXISTS trg_employee_touch ON employee;",
    "DROP TRIGGER IF EXISTS trg_employee_validate ON employee;",
    "DROP FUNCTION IF EXISTS fn_salary_history();",
    "DROP FUNCTION IF EXISTS fn_employee_audit();",
    "DROP FUNCTION IF EXISTS fn_employee_touch();",
    "DROP FUNCTION IF EXISTS fn_employee_validate();",
]


class Migration(migrations.Migration):
    dependencies = [("hr", "0001_initial")]
    operations = [migrations.RunSQL(sql=FORWARD, reverse_sql=BACKWARD)]
