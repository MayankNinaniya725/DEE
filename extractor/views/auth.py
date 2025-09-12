from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from ..forms import CustomLoginForm, CustomUserCreationForm
from ..models.user import CustomUser

def login_view(request):
    if request.method == 'POST':
        form = CustomLoginForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('admin:index')  # Redirect to admin panel after login
    else:
        form = CustomLoginForm()
    return render(request, 'auth/login.html', {'form': form})

@login_required
def logout_view(request):
    """
    Handle logout - accepts both GET and POST requests
    for compatibility with both custom and admin logout
    """
    logout(request)
    return redirect('login')

def is_admin(user):
    # Handle anonymous users
    if not user or user.is_anonymous:
        return False
    return user.is_admin

from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import datetime, timedelta
from ..models import UploadedPDF, ExtractedData, Vendor

@user_passes_test(is_admin, login_url='login')
@login_required(login_url='login')
def admin_dashboard(request):
    # Users
    users = CustomUser.objects.all().order_by('-date_joined')
    active_users = CustomUser.objects.filter(is_active=True).count()
    admin_users = CustomUser.objects.filter(is_admin=True).count()

    # PDFs and Extractions
    total_pdfs = UploadedPDF.objects.count()
    total_extractions = ExtractedData.objects.count()
    total_vendors = Vendor.objects.count()
    
    # Recent Activity
    recent_pdfs = UploadedPDF.objects.all().order_by('-uploaded_at')[:5]
    recent_extractions = ExtractedData.objects.all().order_by('-created_at')[:5]
    
    # Vendor Statistics
    vendor_stats = Vendor.objects.annotate(
        pdf_count=Count('pdfs'),
        extraction_count=Count('pdfs__extracted_data'),
        pending_pdfs=Count('pdfs', filter=Q(pdfs__status='PENDING')),
        processing_pdfs=Count('pdfs', filter=Q(pdfs__status='PROCESSING')),
        completed_pdfs=Count('pdfs', filter=Q(pdfs__status='COMPLETED')),
        error_pdfs=Count('pdfs', filter=Q(pdfs__status='ERROR'))
    ).order_by('-pdf_count')

    # Time-based Statistics
    today = timezone.now()
    last_week = today - timedelta(days=7)
    last_month = today - timedelta(days=30)

    pdfs_today = UploadedPDF.objects.filter(uploaded_at__date=today.date()).count()
    pdfs_week = UploadedPDF.objects.filter(uploaded_at__gte=last_week).count()
    pdfs_month = UploadedPDF.objects.filter(uploaded_at__gte=last_month).count()

    extractions_today = ExtractedData.objects.filter(created_at__date=today.date()).count()
    extractions_week = ExtractedData.objects.filter(created_at__gte=last_week).count()
    extractions_month = ExtractedData.objects.filter(created_at__gte=last_month).count()

    # Error Tracking
    error_pdfs = UploadedPDF.objects.filter(status='ERROR').count()
    pending_pdfs = UploadedPDF.objects.filter(status='PENDING').count()
    
    context = {
        # User Statistics
        'users': users,
        'total_users': users.count(),
        'active_users': active_users,
        'admin_users': admin_users,
        
        # PDF Statistics
        'total_pdfs': total_pdfs,
        'total_extractions': total_extractions,
        'total_vendors': total_vendors,
        'error_pdfs': error_pdfs,
        'pending_pdfs': pending_pdfs,
        
        # Recent Activity
        'recent_pdfs': recent_pdfs,
        'recent_extractions': recent_extractions,
        
        # Vendor Statistics
        'vendor_stats': vendor_stats,
        
        # Time-based Statistics
        'pdfs_today': pdfs_today,
        'pdfs_week': pdfs_week,
        'pdfs_month': pdfs_month,
        'extractions_today': extractions_today,
        'extractions_week': extractions_week,
        'extractions_month': extractions_month,
    }
    
    return render(request, 'auth/admin_dashboard.html', context)

@user_passes_test(is_admin, login_url='login')
@login_required(login_url='login')
def create_user(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'User {user.username} was created successfully')
            return redirect('admin_dashboard')
    else:
        form = CustomUserCreationForm()
    return render(request, 'auth/create_user.html', {'form': form})
