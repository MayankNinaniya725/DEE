# extractor/urls.py
from django.urls import path
from extractor import views


urlpatterns = [
    path("", views.upload_pdf, name="upload_pdf"),
    path("dashboard/", views.dashboard, name="dashboard"),
]
