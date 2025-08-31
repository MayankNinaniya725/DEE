# project urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from extractor import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.dashboard, name='dashboard'),  # Home page
    path('upload/', views.upload_pdf, name='upload_pdf'),
    path('dashboard/', views.dashboard, name='dashboard'),

    # NEW: expose api + download at project level as well
    path('api/task-status/<str:task_id>/', views.task_status, name='task_status'),
    path('download/excel/', views.download_excel, name='download_excel'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
