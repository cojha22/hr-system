from django.db import models
from django.utils import timezone


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = "department"

    def __str__(self):
        return self.name


class Employee(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)                      # unique B-tree index
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="employees")
    salary = models.DecimalField(max_digits=10, decimal_places=2)
    hire_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)     # maintained by a DB trigger

    class Meta:
        db_table = "employee"
        indexes = [models.Index(fields=["department", "salary"], name="idx_employee_dept_salary")]


class SalaryHistory(models.Model):
    """Temporal table: each row is valid during [valid_from, valid_to). valid_to NULL = current."""
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="salary_history")
    salary = models.DecimalField(max_digits=10, decimal_places=2)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "salary_history"
        indexes = [models.Index(fields=["employee", "valid_from"], name="idx_hist_emp_from")]


class EmployeeAudit(models.Model):
    """Filled exclusively by a database trigger, never by application code."""
    employee_id = models.IntegerField(db_index=True)
    action = models.CharField(max_length=10)
    old_data = models.JSONField(null=True, blank=True)
    new_data = models.JSONField(null=True, blank=True)
    changed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "employee_audit"
