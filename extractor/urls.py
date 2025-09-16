from django.urls import path
from django.contrib.auth.decorators import login_required
from django.views.generic import RedirectView
from . import views
from .views.core import process_pdf, dashboard, upload_pdf, task_progress
from .views.auth import login_view, logout_view
from .views.downloads import download_all_pdfs_package
from .views.download_views import download_package, download_large_package
from .views.single_file_package import download_single_file_package, download_individual_pdf


urlpatterns = [
    # Redirect root to dashboard
    path('', RedirectView.as_view(url='/dashboard/'), name='root'),
    
    # Auth URLs
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    
    # PDF processing URLs
    path('process-pdf/', process_pdf, name='process_pdf'),
    
    # Core URLs - dashboard and upload are public
    path('dashboard/', dashboard, name='dashboard'),
    path('upload/', upload_pdf, name='upload_pdf'),

    # API endpoints that still require login
    path('task-status/<str:task_id>/', login_required(views.task_status), name='task_status'),
    path('progress/<str:task_id>/', login_required(task_progress), name='task_progress'),
    path('download/single-file-package/<str:pdf_id>/', login_required(download_single_file_package), name='download_single_file_package'),
    path('download/individual-pdf/<str:pdf_id>/', login_required(download_individual_pdf), name='download_individual_pdf'),
    path('download/excel/', login_required(views.download_excel), name='download_excel'),
    path('download/pdfs-with-excel/', login_required(views.download_pdfs_with_excel), name='download_pdfs_with_excel'),
    path('download/all-pdfs-package/', login_required(download_all_pdfs_package), name='download_all_pdfs_package'),
    path('download/package/', login_required(download_package), name='download_package'),
    path('download/large-package/', login_required(download_large_package), name='download_large_package'),
    path('regenerate-excel/', login_required(views.regenerate_excel), name='regenerate_excel'),
]
