import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Department",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, unique=True)),
            ],
            options={"db_table": "department"},
        ),
        migrations.CreateModel(
            name="Employee",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("email", models.EmailField(max_length=254, unique=True)),
                ("salary", models.DecimalField(decimal_places=2, max_digits=10)),
                ("hire_date", models.DateField()),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("department", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                                 related_name="employees", to="hr.department")),
            ],
            options={
                "db_table": "employee",
                "indexes": [models.Index(fields=["department", "salary"], name="idx_employee_dept_salary")],
            },
        ),
        migrations.CreateModel(
            name="SalaryHistory",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("salary", models.DecimalField(decimal_places=2, max_digits=10)),
                ("valid_from", models.DateTimeField()),
                ("valid_to", models.DateTimeField(blank=True, null=True)),
                ("employee", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                               related_name="salary_history", to="hr.employee")),
            ],
            options={
                "db_table": "salary_history",
                "indexes": [models.Index(fields=["employee", "valid_from"], name="idx_hist_emp_from")],
            },
        ),
        migrations.CreateModel(
            name="EmployeeAudit",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("employee_id", models.IntegerField(db_index=True)),
                ("action", models.CharField(max_length=10)),
                ("old_data", models.JSONField(blank=True, null=True)),
                ("new_data", models.JSONField(blank=True, null=True)),
                ("changed_at", models.DateTimeField(default=django.utils.timezone.now)),
            ],
            options={"db_table": "employee_audit"},
        ),
    ]
