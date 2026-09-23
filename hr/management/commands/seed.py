import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import connection

from hr.models import Department, Employee

PEOPLE = [
    ("Alice Johnson", "Engineering", 60000), ("Bob Smith", "Engineering", 85000),
    ("Carla Gomez", "Engineering", 120000), ("David Lee", "HR", 52000),
    ("Emma Wilson", "HR", 58000), ("Farhan Ali", "Sales", 47000),
    ("Grace Kim", "Sales", 63000), ("Hiro Tanaka", "Finance", 91000),
    ("Isha Patel", "Finance", 76000), ("Jonas Berg", "Marketing", 54000),
]


class Command(BaseCommand):
    help = "Seed demo data. Use --bulk N to add N extra rows so the indexing demo is meaningful."

    def add_arguments(self, parser):
        parser.add_argument("--bulk", type=int, default=0, help="extra random employees (e.g. 50000)")

    def handle(self, *args, **opts):
        depts = {n: Department.objects.get_or_create(name=n)[0]
                 for n in ["Engineering", "HR", "Sales", "Finance", "Marketing"]}

        for name, dept, salary in PEOPLE:
            email = name.lower().replace(" ", ".") + "@example.com"
            emp, created = Employee.objects.get_or_create(
                email=email,
                defaults=dict(name=name, department=depts[dept], salary=Decimal(salary),
                              hire_date=date.today() - timedelta(days=random.randint(200, 3000))))
            if created and name == "Alice Johnson":
                self.make_alice_temporal(emp)

        if opts["bulk"]:
            ids = list(Department.objects.values_list("id", flat=True))
            with connection.cursor() as cur:
                cur.execute("""
                    INSERT INTO employee(name, email, department_id, salary, hire_date, is_active, created_at, updated_at)
                    SELECT 'Employee ' || g, 'user' || g || '@bulk.example.com',
                           (%s::int[])[1 + mod(g, %s)],
                           round((30000 + random() * 120000)::numeric, 2),
                           current_date - (random() * 3650)::int, true, now(), now()
                    FROM generate_series(1, %s) g
                    ON CONFLICT (email) DO NOTHING
                """, [ids, len(ids), opts["bulk"]])
                cur.execute("ANALYZE employee")
        self.stdout.write(self.style.SUCCESS(f"Seeded. Employees in DB: {Employee.objects.count()}"))

    def make_alice_temporal(self, emp):
        """Give Alice a believable salary history, then backdate the rows so 'as of' queries are interesting."""
        for s in (70000, 80000):
            emp.salary = Decimal(s)
            emp.save()
        with connection.cursor() as cur:
            cur.execute("SELECT id FROM salary_history WHERE employee_id=%s ORDER BY id", [emp.id])
            ids = [r[0] for r in cur.fetchall()]
            spans = [("2022-01-01", "2023-06-01"), ("2023-06-01", "2025-01-01"), ("2025-01-01", None)]
            for hid, (a, b) in zip(ids, spans):
                cur.execute("UPDATE salary_history SET valid_from=%s, valid_to=%s WHERE id=%s", [a, b, hid])
