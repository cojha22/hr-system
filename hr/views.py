import json
import re
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import DatabaseError, connection
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .models import Department, Employee, EmployeeAudit, SalaryHistory

FIELDS = ("name", "email", "department_id", "salary", "hire_date", "is_active")
CLIENT_ERRORS = (DatabaseError, ArithmeticError, ValueError, ValidationError)


def index(request):
    return render(request, "index.html")


def error(exc, status=400):
    """Return only the first line of the DB error (the RAISE EXCEPTION text from a trigger/procedure)."""
    if isinstance(exc, ValidationError):
        msg = "; ".join(exc.messages)
    else:
        msg = str(exc).strip().split("\n")[0] or exc.__class__.__name__
    return JsonResponse({"error": msg}, status=status)


def query(sql, params=None):
    """Run raw SQL and return a list of dicts."""
    with connection.cursor() as cur:
        cur.execute(sql, params or [])
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def body(request):
    return json.loads(request.body or "{}")


def serialize(e):
    return {
        "id": e.id, "name": e.name, "email": e.email,
        "department_id": e.department_id, "department": e.department.name,
        "salary": e.salary, "hire_date": e.hire_date, "is_active": e.is_active,
        "created_at": e.created_at, "updated_at": e.updated_at,
    }


def apply(emp, data):
    for f in FIELDS:
        if f in data:
            v = data[f]
            if f == "salary":
                v = Decimal(str(v))
            setattr(emp, f, v)


# ============================================================== CRUD
@require_http_methods(["GET"])
def departments(request):
    return JsonResponse(list(Department.objects.order_by("name").values("id", "name")), safe=False)


@require_http_methods(["GET", "POST"])
def employees(request):
    if request.method == "GET":                                   # READ (list + search)
        qs = Employee.objects.select_related("department").order_by(
            "id" if request.GET.get("order") == "asc" else "-id")
        q = request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(email__icontains=q))
        limit = min(int(request.GET.get("limit", 50)), 500)
        return JsonResponse({"total": qs.count(), "employees": [serialize(e) for e in qs[:limit]]})

    try:                                                          # CREATE
        emp = Employee()
        apply(emp, body(request))
        emp.save()
        emp.refresh_from_db()
        return JsonResponse(serialize(emp), status=201)
    except CLIENT_ERRORS as exc:
        return error(exc)


@require_http_methods(["GET", "PUT", "PATCH", "DELETE"])
def employee_detail(request, pk):
    try:
        emp = Employee.objects.select_related("department").get(pk=pk)
    except Employee.DoesNotExist:
        return JsonResponse({"error": "Employee not found"}, status=404)

    try:
        if request.method == "GET":                               # READ (one)
            return JsonResponse(serialize(emp))
        if request.method == "DELETE":                            # DELETE
            emp.delete()
            return JsonResponse({"deleted": pk})
        apply(emp, body(request))                                 # UPDATE (PUT or partial PATCH)
        emp.save()
        emp.refresh_from_db()
        return JsonResponse(serialize(emp))
    except CLIENT_ERRORS as exc:
        return error(exc)


# ============================================================== TRIGGERS
@require_GET
def audit_log(request):
    rows = EmployeeAudit.objects.order_by("-id")[:60].values(
        "id", "employee_id", "action", "old_data", "new_data", "changed_at")
    return JsonResponse(list(rows), safe=False)


# ============================================================== VIEWS
@require_GET
def view_department_summary(request):
    return JsonResponse(query("SELECT * FROM v_department_summary ORDER BY department"), safe=False)


@require_GET
def view_employee_details(request):
    return JsonResponse(query("SELECT * FROM v_employee_details ORDER BY id DESC LIMIT 50"), safe=False)


# ============================================================== STORED PROCEDURE
@require_POST
def give_raise(request):
    try:
        data = body(request)
        with connection.cursor() as cur:
            cur.execute("CALL sp_give_raise(%s::int, %s::numeric, 0)",
                        [int(data["department_id"]), Decimal(str(data["percent"]))])
            updated = cur.fetchone()[0]                           # INOUT parameter comes back as a row
        return JsonResponse({"updated": updated})
    except (KeyError, *CLIENT_ERRORS) as exc:
        return error(exc)


# ============================================================== INDEXING
@require_GET
def index_explain(request):
    lo = Decimal(request.GET.get("min", "90000"))
    hi = Decimal(request.GET.get("max", "90100"))
    with connection.cursor() as cur:
        cur.execute("EXPLAIN ANALYZE SELECT id, name, salary FROM employee WHERE salary BETWEEN %s AND %s", [lo, hi])
        plan = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT COUNT(*) FROM employee")
        total = cur.fetchone()[0]
    text = "\n".join(plan)
    m = re.search(r"Execution Time: ([\d.]+) ms", text)
    return JsonResponse({
        "plan": plan,
        "uses_index": "Index" in text or "Bitmap" in text,
        "execution_ms": float(m.group(1)) if m else None,
        "total_rows": total,
        "indexes": query("SELECT indexname, indexdef FROM pg_indexes "
                         "WHERE tablename IN ('employee','salary_history') ORDER BY indexname"),
    })


@require_POST
def index_toggle(request):
    action = body(request).get("action")
    with connection.cursor() as cur:
        if action == "create":
            cur.execute("CREATE INDEX IF NOT EXISTS idx_employee_salary ON employee (salary)")
            cur.execute("ANALYZE employee")
        elif action == "drop":
            cur.execute("DROP INDEX IF EXISTS idx_employee_salary")
            cur.execute("ANALYZE employee")
        else:
            return JsonResponse({"error": "action must be 'create' or 'drop'"}, status=400)
    return JsonResponse({"ok": True, "action": action})


# ============================================================== TEMPORAL DATA
@require_GET
def salary_history(request, pk):
    rows = SalaryHistory.objects.filter(employee_id=pk).order_by("valid_from").values(
        "id", "salary", "valid_from", "valid_to")
    return JsonResponse(list(rows), safe=False)


@require_GET
def salary_as_of(request, pk):
    ts = request.GET.get("ts", "")
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT fn_salary_as_of(%s, %s::timestamptz)", [pk, ts])
            salary = cur.fetchone()[0]
        return JsonResponse({"employee_id": pk, "as_of": ts, "salary": salary})
    except DatabaseError as exc:
        return error(exc)
