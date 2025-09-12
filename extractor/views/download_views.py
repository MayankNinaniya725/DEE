from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
from django.views.decorators.http import require_GET
from extractor.utils.zip_utils import create_package_response, create_large_package_response

@require_GET
def download_package(request):
    """
    Download a ZIP package containing the master Excel file and all extracted PDFs.
    Uses memory buffer for smaller packages.
    """
    try:
        return create_package_response(request)
    except Exception as e:
        messages.error(request, f"Error creating package: {str(e)}")
        return redirect('dashboard')

@require_GET
def download_large_package(request):
    """
    Download a ZIP package containing the master Excel file and all extracted PDFs.
    Uses temporary file for larger packages to avoid memory issues.
    """
    try:
        return create_large_package_response(request)
    except Exception as e:
        messages.error(request, f"Error creating package: {str(e)}")
        return redirect('dashboard')
