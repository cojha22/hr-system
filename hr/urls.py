from django.urls import path
from . import views

urlpatterns = [
    path("", views.index),
    # CRUD
    path("api/departments/", views.departments),
    path("api/employees/", views.employees),
    path("api/employees/<int:pk>/", views.employee_detail),
    # triggers (audit table is written by the DB)
    path("api/audit/", views.audit_log),
    # views
    path("api/views/department-summary/", views.view_department_summary),
    path("api/views/employee-details/", views.view_employee_details),
    # stored procedure
    path("api/procedures/give-raise/", views.give_raise),
    # indexing
    path("api/index/explain/", views.index_explain),
    path("api/index/toggle/", views.index_toggle),
    # temporal data
    path("api/employees/<int:pk>/history/", views.salary_history),
    path("api/employees/<int:pk>/salary-as-of/", views.salary_as_of),
]
