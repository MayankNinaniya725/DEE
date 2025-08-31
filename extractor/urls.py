# extractor/urls.py
from django.urls import path
from extractor import views

urlpatterns = [
    path("", views.upload_pdf, name="upload_pdf"),
    path("dashboard/", views.dashboard, name="dashboard"),

    # API endpoints
    path("api/task-status/<str:task_id>/", views.task_status, name="task_status"),
    path("api/clear-task-id/", views.clear_task_id, name="clear_task_id"),
    path("download/excel/", views.download_excel, name="download_excel"),
]
