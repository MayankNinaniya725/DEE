import os
import io
import json
import logging
import tempfile
import shutil
import zipfile
import hashlib
from datetime import datetime

from django.shortcuts import render, redirect
from django.urls import reverse
from django.core.files.storage import FileSystemStorage
from django.contrib import messages
from django.contrib.auth import logout
from django.db.models import Count, Q
from django.core.exceptions import ValidationError
from django.conf import settings
from django.http import JsonResponse, HttpResponse, FileResponse
from django.utils import timezone
from celery.result import AsyncResult

import pandas as pd
from openpyxl import load_workbook

from .models import ExtractedData, Vendor, UploadedPDF
from .utils.extractor import extract_pdf_fields
from .utils.config_loader import load_vendor_config
from .tasks import process_pdf_file

# Configure logging
logger = logging.getLogger('extractor')


def store_dashboard_message(request, message, level='info', extra_data=None):
    """Store message in session for dashboard display using Django's messages framework"""
    # Map our level names to Django's message levels
    level_mapping = {
        'success': messages.SUCCESS,
        'error': messages.ERROR,
        'warning': messages.WARNING,
        'info': messages.INFO
    }
    django_level = level_mapping.get(level, messages.INFO)
    
    # Format the message if extra_data is provided and message is error
    if level == 'error' and extra_data:
        # Store the error details in the session for JS to access
        if 'error_details' not in request.session:
            request.session['error_details'] = {}
        
        error_id = hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:8]
        request.session['error_details'][error_id] = {
            'message': message,
            'details': extra_data,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        request.session.modified = True
        
        # Set a flag in the message to trigger JS error handling
        message = f"{message}||SHOW_DETAILS:{error_id}"
    
    # Add message to Django's messages framework
    messages.add_message(request, django_level, message)
    
    # For backward compatibility, also store in session
    if 'pdf_messages' not in request.session:
        request.session['pdf_messages'] = []
    
    request.session['pdf_messages'].append({
        'message': message,
        'level': level,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    request.session.modified = True
    if not request.session.get('pdf_messages'):
        request.session['pdf_messages'] = []
    request.session['pdf_messages'].append({
        'message': message,
        'level': level,
        'timestamp': timezone.now().isoformat(),
        'extra_data': extra_data or {}
    })
    request.session.modified = True


def create_extraction_excel(excel_path, pdf_obj, extracted_data):
    """Creates a detailed Excel file with multiple sheets for extracted data"""
    pdf_filename = os.path.basename(pdf_obj.file.name)
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        # Summary sheet
        summary_data = {
            'Information': [
                'File Name', 'Vendor', 'Upload Date', 'Total Fields',
                'Total Pages', 'Status'
            ],
            'Value': [
                pdf_filename,
                pdf_obj.vendor.name,
                pdf_obj.uploaded_at.strftime("%Y-%m-%d %H:%M:%S"),
                extracted_data.count(),
                len(set(item.page_number for item in extracted_data if item.page_number)),
                'Extraction Complete'
            ]
        }
        pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)

        # Extracted Data sheet
        main_data = [{
            'Field Type': item.field_key,
            'Extracted Value': item.field_value,
            'Page Number': item.page_number,
            'PDF Location': f'extracted_pdfs/page_{item.page_number}.pdf' if item.page_number else 'N/A',
            'Extracted At': item.created_at.strftime("%Y-%m-%d %H:%M:%S")
        } for item in extracted_data]
        if main_data:
            pd.DataFrame(main_data).to_excel(writer, sheet_name='Extracted Data', index=False)

        # Key Fields sheet
        key_fields = ['PLATE_NO', 'HEAT_NO', 'TEST_CERT_NO']
        key_data = []
        for field in key_fields:
            matches = [item for item in extracted_data if item.field_key == field]
            for match in matches:
                key_data.append({
                    'Field': field,
                    'Value': match.field_value,
                    'Page': match.page_number,
                    'PDF File': f'extracted_pdfs/page_{match.page_number}.pdf',
                    'Status': 'Verified' if match.field_value else 'Not Found'
                })
        if key_data:
            pd.DataFrame(key_data).to_excel(writer, sheet_name='Key Fields', index=False)

        # Page Summary sheet
        page_data = []
        for page in sorted(set(item.page_number for item in extracted_data if item.page_number)):
            page_fields = [item for item in extracted_data if item.page_number == page]
            key_fields_found = [
                f"{item.field_key}: {item.field_value}"
                for item in page_fields
                if item.field_key in key_fields and item.field_value
            ]
            page_data.append({
                'Page Number': page,
                'Fields Found': len(page_fields),
                'PDF File': f'extracted_pdfs/page_{page}.pdf',
                'Key Fields Found': ', '.join(key_fields_found) if key_fields_found else 'None'
            })
        if page_data:
            pd.DataFrame(page_data).to_excel(writer, sheet_name='Page Summary', index=False)


def process_pdf(request):
    """Handle PDF upload and processing with duplicate detection and vendor validation"""
    if request.method == 'POST' and request.FILES.get('pdf'):
        vendor_id = request.POST.get('vendor')
        pdf_file = request.FILES['pdf']

        if not vendor_id:
            return JsonResponse({'status': 'error', 'message': 'Vendor selection is required'}, status=400)

        if not pdf_file.name.lower().endswith('.pdf'):
            return JsonResponse({'status': 'error', 'message': 'Uploaded file must be a PDF'}, status=400)

        try:
            vendor = Vendor.objects.get(id=vendor_id)

            # Calculate file hash for duplicate detection
            file_content = pdf_file.read()
            file_hash = hashlib.md5(file_content).hexdigest()
            pdf_file.seek(0)

            # Save temporary file for vendor validation
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                temp_file.write(file_content)
                temp_file_path = temp_file.name
            
            try:
                # Perform vendor validation
                from .utils.vendor_detection import validate_vendor_selection
                validation_result = validate_vendor_selection(temp_file_path, vendor_id)
                
                # Clean up temporary file
                os.unlink(temp_file_path)
                
                # If vendor validation failed, save PDF with error status
                if not validation_result['is_valid']:
                    logger.warning(f"Vendor validation failed: {validation_result['message']}")
                    
                    # Reset file pointer for saving
                    pdf_file.seek(0)
                    
                    # Save PDF with error status so it appears on dashboard
                    error_pdf = UploadedPDF.objects.create(
                        file=pdf_file,
                        vendor=vendor,
                        file_hash=file_hash,
                        status='ERROR'
                    )
                    
                    logger.info(f"Saved PDF with vendor error: {error_pdf.file.name} (ID: {error_pdf.id})")
                    
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Vendor is not correct for the uploaded file.',
                        'details': validation_result['message'],
                        'detected_vendor': validation_result.get('detected_vendor'),
                        'confidence': validation_result.get('confidence', 0.0)
                    }, status=400)
                
                # Log successful validation
                if validation_result.get('detected_vendor'):
                    logger.info(f"Vendor validation successful: {validation_result['message']}")
                
            except Exception as validation_error:
                # Clean up temporary file on error
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
                logger.error(f"Vendor validation error: {str(validation_error)}")
                # Continue processing on validation error (graceful fallback)
            
            # Reset file pointer for further processing
            pdf_file.seek(0)

            existing_pdf = UploadedPDF.objects.filter(file_hash=file_hash).first()
            if existing_pdf:
                # If vendor mismatch, reject but save reference with new vendor as well
                if existing_pdf.vendor.id != vendor.id:
                    msg = f"PDF previously uploaded for vendor '{existing_pdf.vendor.name}'. Please select the correct vendor."
                    messages.warning(request, msg)
                    store_dashboard_message(request, msg, 'warning', {'original_vendor': existing_pdf.vendor.name, 'new_vendor': vendor.name})
                    
                    # Create a new record for this vendor with vendor mismatch error
                    # Reset file pointer for saving
                    pdf_file.seek(0)
                    
                    mismatch_pdf = UploadedPDF.objects.create(
                        file=pdf_file,
                        vendor=vendor,
                        file_hash=file_hash,
                        status='ERROR'
                    )
                    
                    logger.info(f"Saved vendor mismatch PDF: {mismatch_pdf.file.name} (ID: {mismatch_pdf.id})")
                    
                    return JsonResponse({
                        'status': 'error',
                        'message': msg,
                        'type': 'vendor_mismatch',
                        'original_vendor': existing_pdf.vendor.name,
                        'new_vendor': vendor.name
                    }, status=400)

                # If extraction incomplete, retry extraction
                if existing_pdf.status != 'COMPLETED':
                    try:
                        # Use the improved config loader
                        from .utils.config_loader import find_vendor_config
                        vendor_config, config_path = find_vendor_config(vendor, settings)
                        
                        if vendor_config:
                            task = process_pdf_file.delay(existing_pdf.id, vendor_config)
                            msg = "Retrying extraction for duplicate PDF"
                            messages.info(request, msg)
                            store_dashboard_message(request, msg, 'info')
                            return JsonResponse({
                                'status': 'processing',
                                'message': 'Duplicate PDF detected, retrying extraction.',
                                'task_id': task.id,
                                'type': 'duplicate'
                            })
                        else:
                            logger.error(f"Could not find vendor config for {vendor.name}")
                            msg = f"Missing vendor configuration for '{vendor.name}'"
                            messages.error(request, msg)
                            store_dashboard_message(request, msg, 'error')
                            return JsonResponse({
                                'status': 'error',
                                'message': msg,
                                'type': 'config_missing'
                            }, status=400)
                    except Exception as e:
                        logger.error(f"Error retrying extraction: {str(e)}", exc_info=True)
                        msg = f"Error retrying extraction: {str(e)}"
                        messages.error(request, msg)
                        store_dashboard_message(request, msg, 'error')
                        return JsonResponse({
                            'status': 'error',
                            'message': msg,
                            'type': 'extraction_error'
                        }, status=500)

                msg = f"This PDF was already processed on {existing_pdf.uploaded_at.strftime('%Y-%m-%d %H:%M:%S')}"
                messages.warning(request, msg)
                return JsonResponse({
                    'status': 'warning',
                    'message': msg,
                    'type': 'duplicate',
                    'processed_date': existing_pdf.uploaded_at.strftime('%Y-%m-%d %H:%M:%S')
                }, status=200)

            # Save new PDF entry
            pdf = UploadedPDF.objects.create(
                file=pdf_file,
                vendor=vendor,
                file_hash=file_hash,
                file_size=pdf_file.size,
                status='PROCESSING',
                user=request.user if not request.user.is_anonymous else None
            )

            # Validate vendor config
            from .utils.config_loader import find_vendor_config
            vendor_config, config_path = find_vendor_config(vendor, settings)
            
            if not vendor_config:
                pdf.status = 'ERROR'
                pdf.save()
                msg = f"Missing vendor configuration for '{vendor.name}'"
                messages.error(request, msg)
                store_dashboard_message(request, msg, 'error')
                return JsonResponse({
                    'status': 'error',
                    'message': msg,
                    'type': 'config_missing'
                }, status=400)

            # Start the Celery task for extraction
            # Start the task and store task ID
            task = process_pdf_file.delay(pdf.id, vendor_config)
            request.session['last_task_id'] = task.id
            request.session.modified = True
            
            msg = "PDF uploaded successfully. Starting extraction..."
            messages.success(request, msg)
            store_dashboard_message(request, msg, 'success')
            # Explicitly save session
            request.session.save()
            return JsonResponse({
                'status': 'processing',
                'task_id': task.id,
                'message': 'PDF uploaded successfully. Starting extraction...',
                'type': 'success'
            })

        except Vendor.DoesNotExist:
            msg = "Selected vendor not found"
            messages.error(request, msg)
            store_dashboard_message(request, msg, 'error')
            return JsonResponse({
                'status': 'error',
                'message': msg,
                'type': 'vendor_not_found'
            }, status=400)

        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}", exc_info=True)
            msg = f"Error processing PDF: {str(e)}"
            messages.error(request, msg)
            store_dashboard_message(request, msg, 'error')
            return JsonResponse({
                'status': 'error',
                'message': msg,
                'type': 'processing_error',
                'details': str(e)
            }, status=500)

    msg = "Invalid request"
    messages.error(request, msg)
    store_dashboard_message(request, msg, 'error')
    return JsonResponse({
        'status': 'error',
        'message': msg,
        'type': 'invalid_request'
    }, status=400)


def dashboard(request):
    """Dashboard view showing summary of uploaded PDFs and extraction status"""
    # Check if this is a request for error details (used by enhanced error handling)
    if 'get_error_details' in request.GET:
        error_id = request.GET.get('get_error_details')
        error_details = request.session.get('error_details', {}).get(error_id, {})
        
        # Clear this error from the session after retrieving it
        if error_id in request.session.get('error_details', {}):
            del request.session['error_details'][error_id]
            request.session.modified = True
            
        return JsonResponse({
            'success': True,
            'details': error_details.get('details', ''),
            'message': error_details.get('message', '')
        })
    
    # Regular dashboard view
    # Get PDFs from database using direct SQL to avoid status field issues
    from django.db import connection
    
    # Get recent PDFs
    with connection.cursor() as cursor:
        if request.user.is_superuser:
            cursor.execute('''
                SELECT up.id, up.file, datetime(up.uploaded_at) as uploaded_at, up.status, v.id, v.name
                FROM extractor_uploadedpdf up
                JOIN extractor_vendor v ON up.vendor_id = v.id
                ORDER BY up.uploaded_at DESC
                LIMIT 20
            ''')
        else:
            # For non-superusers, we would filter by user, but for now show all
            cursor.execute('''
                SELECT up.id, up.file, datetime(up.uploaded_at) as uploaded_at, up.status, v.id, v.name
                FROM extractor_uploadedpdf up
                JOIN extractor_vendor v ON up.vendor_id = v.id
                ORDER BY up.uploaded_at DESC
                LIMIT 20
            ''')
        
        rows = cursor.fetchall()
        
        # Convert to a list of dictionaries that mimics Django ORM objects
        recent_pdfs = []
        for row in rows:
            pdf_id, file_path, uploaded_at, status, vendor_id, vendor_name = row
            pdf = {
                'id': pdf_id,
                'file': {'name': file_path},
                'uploaded_at': uploaded_at,
                'status': status,
                'vendor': {'id': vendor_id, 'name': vendor_name}
            }
            recent_pdfs.append(pdf)
    
    # Get vendors
    vendors = Vendor.objects.annotate(pdf_count=Count('pdfs'))
    
    # Get status summary
    status_summary = {
        'pending': 0,
        'processing': 0,
        'completed': 0,
        'error': 0,
    }
    
    with connection.cursor() as cursor:
        cursor.execute('''
            SELECT status, COUNT(*) 
            FROM extractor_uploadedpdf 
            GROUP BY status
        ''')
        status_counts = cursor.fetchall()
        
        for status, count in status_counts:
            if status == 'PENDING':
                status_summary['pending'] = count
            elif status == 'PROCESSING':
                status_summary['processing'] = count
            elif status == 'COMPLETED':
                status_summary['completed'] = count
            elif status == 'ERROR':
                status_summary['error'] = count
    
    # Process legacy session messages, if any
    dashboard_messages = request.session.pop('pdf_messages', [])
    for msg in dashboard_messages:
        level_mapping = {
            'success': messages.SUCCESS,
            'error': messages.ERROR,
            'warning': messages.WARNING,
            'info': messages.INFO
        }
        level = level_mapping.get(msg['level'], messages.INFO)
        
        # Skip adding to messages framework if this message is already there
        # This prevents duplicate messages when using both the old and new approaches
        existing_messages = [str(message) for message in messages.get_messages(request)]
        if msg['message'] not in existing_messages:
            messages.add_message(request, level, msg['message'])
    
    # Get recent extractions
    extraction_filter = Q()
    if not request.user.is_superuser:
        extraction_filter &= Q(pdf__user=request.user)
    
    recent_extractions = ExtractedData.objects.select_related('pdf', 'vendor').filter(extraction_filter).order_by('-created_at')[:20]
    
    # Get unique certificates data for detailed view - one per PDF
    certificates = []
    seen_pdf_ids = set()
    
    # Get all completed PDFs ordered by upload time
    processed_pdfs = UploadedPDF.objects.filter(status='COMPLETED').order_by('-uploaded_at')
    
    for pdf in processed_pdfs:
        if pdf.id not in seen_pdf_ids:
            seen_pdf_ids.add(pdf.id)
            
            # Check if this PDF has any extracted data
            pdf_extractions = ExtractedData.objects.filter(pdf=pdf).order_by('field_key')
            
            if pdf_extractions.exists():
                # Get all fields for this certificate
                cert_data = {
                    'Vendor': pdf.vendor.name,
                    'Created': pdf.uploaded_at,
                    'pdf_id': pdf.id,
                    'Source PDF': pdf.file.name,
                    'Page': 'Multiple' if pdf_extractions.values('page_number').distinct().count() > 1 else str(pdf_extractions.first().page_number or 'N/A'),
                    'Filename': os.path.basename(pdf.file.name),
                    'Remarks': 'N/A'
                }
                
                # Get specific fields for this certificate
                for field in pdf_extractions:
                    cert_data[field.field_key] = field.field_value
                    
                certificates.append(cert_data)
                
                # Limit to a reasonable number of certificates
                if len(certificates) >= 50:  # Show last 50 certificates
                    break
    
    # Get current timestamp for the template
    from django.utils import timezone
    current_timestamp = timezone.now()
    
    context = {
        'recent_pdfs': recent_pdfs,
        'vendors': vendors,
        'status_summary': status_summary,
        'recent_extractions': recent_extractions,
        'task_id': request.session.get('last_task_id'),
        'now': current_timestamp,
        'data': certificates  # Add certificates data to context
    }
    return render(request, 'extractor/dashboard.html', context)


def task_status(request, task_id):
    """Get the status of a Celery async task"""
    res = AsyncResult(task_id)
    payload = {"state": res.state}

    if res.state == "PROGRESS":
        meta = res.info or {}
        payload.update({
            "current": meta.get("current", 0),
            "total": meta.get("total", 1),
            "phase": meta.get("phase", ""),
            "details": meta.get("details", ""),
            "stats": meta.get("stats", {})
        })
    elif res.state == "SUCCESS":
        result_data = res.result or {}
        payload.update(result_data)
        
        # Get message from result or generate one
        message = result_data.get('message', '')
        status = result_data.get('status', '')
        extracted = result_data.get('extracted', 0)
        
        if not message:  # If task didn't provide a message, create one
            if status == 'completed':
                message = f"Extraction completed successfully! {extracted} fields extracted."
            elif status == 'partial_success_ocr':
                message = f"Partial extraction: {extracted} fields extracted. Some pages required OCR fallback."
            elif status == 'failed_ocr':
                message = "Extraction failed. OCR fallback was needed but could not extract data."
            else:
                message = f"Process completed with status: {status}"
                
        # Add the message to the payload
        payload["user_message"] = message
                
        # Add to Django messages system too
        if status == 'completed':
            messages.success(request, message)
        elif status == 'partial_success_ocr':
            messages.warning(request, message)
        elif status == 'failed_ocr':
            messages.error(request, message)
        else:
            messages.info(request, message)
        
        if 'last_task_id' in request.session and request.session['last_task_id'] == task_id:
            del request.session['last_task_id']
            request.session.modified = True
    elif res.state == "FAILURE":
        error_msg = "Extraction failed. Please check logs for details."
        payload.update({
            "status": "failed", 
            "message": error_msg,
            "user_message": error_msg
        })
        messages.error(request, error_msg)
        if 'last_task_id' in request.session and request.session['last_task_id'] == task_id:
            del request.session['last_task_id']
            request.session.modified = True

    return JsonResponse(payload)


def clear_task_id(request):
    """Clear celery task ID from session"""
    if 'last_task_id' in request.session:
        del request.session['last_task_id']
        request.session.modified = True
    return JsonResponse({"success": True})


def task_progress(request, task_id):
    """Get progress percentage for a Celery task"""
    res = AsyncResult(task_id)
    
    # Calculate progress percentage based on task state
    if res.state == "PENDING":
        progress = 0
        message = "Task is queued..."
    elif res.state == "PROGRESS":
        meta = res.info or {}
        phase = meta.get("phase", "")
        current = meta.get("current", 0)
        total = meta.get("total", 4)
        
        # Calculate progress based on phase
        phase_progress = {
            "loading": 10,
            "extracting": 40,
            "saving": 80,
            "finalizing": 95
        }
        
        progress = phase_progress.get(phase, (current / total) * 100)
        message = f"Processing: {phase.title()}..."
        
    elif res.state == "SUCCESS":
        progress = 100
        result_data = res.result or {}
        status = result_data.get('status', 'completed')
        extracted = result_data.get('extracted', 0)
        
        if status == 'completed':
            message = f"✅ Extraction completed! {extracted} fields extracted."
        elif status == 'partial_success_ocr':
            message = f"⚠️ Partial extraction: {extracted} fields extracted."
        elif status == 'failed_ocr':
            message = "❌ Extraction failed - OCR fallback unsuccessful."
        else:
            message = "Processing completed."
            
    elif res.state == "FAILURE":
        progress = 100
        message = "❌ Extraction failed due to an error."
    else:
        progress = 0
        message = f"Task state: {res.state}"
    
    return JsonResponse({
        "progress": int(progress),
        "message": message,
        "state": res.state
    })


def download_excel(request):
    """Download the master Excel file that gets updated with each extraction"""
    try:
        # Path to the master Excel file that gets updated automatically
        master_path = os.path.join(settings.MEDIA_ROOT, "backups", "master.xlsx")
        
        # Check if the master Excel file exists
        if not os.path.exists(master_path):
            messages.error(request, "Master Excel file not found. Please ensure some PDFs have been processed.")
            return redirect("dashboard")
        
        # Generate a filename with timestamp for download
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        download_filename = f"Extracted_Data_{timestamp}.xlsx"
        
        # Serve the file for download
        response = FileResponse(
            open(master_path, 'rb'),
            as_attachment=True,
            filename=download_filename
        )
        response['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response['Content-Disposition'] = f'attachment; filename="{download_filename}"'
        
        logger.info(f"Downloaded master Excel file: {download_filename}")
        return response
        
    except Exception as e:
        logger.error(f"Error downloading Excel file: {str(e)}", exc_info=True)
        messages.error(request, f"Error downloading Excel file: {str(e)}")
        return redirect("dashboard")


def regenerate_excel(request):
    """Regenerate all Excel files for extracted PDFs"""
    try:
        pdfs = UploadedPDF.objects.all()
        regenerated_count = 0
        for pdf in pdfs:
            extracted_data = ExtractedData.objects.filter(pdf=pdf)
            if extracted_data.exists():
                # Create Excel file locally for admin purposes
                pdf_name = os.path.splitext(os.path.basename(pdf.file.name))[0]
                excel_path = os.path.join(settings.MEDIA_ROOT, 'excel', f"{pdf_name}_extraction.xlsx")
                os.makedirs(os.path.dirname(excel_path), exist_ok=True)
                create_extraction_excel(excel_path, pdf, extracted_data)
                regenerated_count += 1
                logger.info(f"Regenerated Excel for {pdf.file.name} at {excel_path}")
        
        messages.success(request, f"Excel files regenerated for {regenerated_count} PDFs")
    except Exception as e:
        logger.error(f"Error regenerating Excel files: {str(e)}", exc_info=True)
        messages.error(request, "Error regenerating Excel files")
    return redirect("dashboard")


def download_pdfs_with_excel(request):
    """
    Creates a ZIP file containing:
    - Original PDF file
    - All extracted PDF pages from the server
    - PDF-specific Excel file with filtered extraction data
    - README file explaining the contents and file organization
    
    The Excel file will only contain entries related to the specific PDF for better readability.
    """
    pdf_id = request.GET.get('pdf_id')
    source_pdf = request.GET.get('source')

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            if pdf_id or source_pdf:
                try:
                    if pdf_id:
                        pdf = UploadedPDF.objects.get(id=pdf_id)
                    else:
                        pdf_filename = os.path.basename(source_pdf)
                        pdf = UploadedPDF.objects.filter(file__contains=pdf_filename).first()
                    if not pdf:
                        messages.warning(request, f"No PDF found with filename: {pdf_filename}")
                        return redirect("dashboard")

                    extracted_data = ExtractedData.objects.filter(pdf=pdf).order_by('field_key')
                    if not extracted_data.exists():
                        messages.warning(request, "No extracted data found for this PDF")
                        return redirect("dashboard")

                    pdf_dir = os.path.join(temp_dir, 'package')
                    orig_dir = os.path.join(pdf_dir, 'original')
                    extracted_dir = os.path.join(pdf_dir, 'extracted_pdfs')
                    os.makedirs(orig_dir, exist_ok=True)
                    os.makedirs(extracted_dir, exist_ok=True)

                    # Copy original PDF
                    pdf_filename = os.path.basename(pdf.file.name)
                    orig_pdf_path = os.path.join(orig_dir, pdf_filename)
                    if os.path.exists(pdf.file.path):
                        shutil.copy2(pdf.file.path, orig_pdf_path)

                    # Copy extracted PDFs
                    base_extracted_dir = os.path.join(settings.MEDIA_ROOT, 'extracted')
                    pdf_name_without_ext = os.path.splitext(pdf_filename)[0]
                    extracted_files = []
                    if os.path.exists(base_extracted_dir):
                        for root, _, files in os.walk(base_extracted_dir):
                            for file in files:
                                if file.startswith(pdf_name_without_ext) and file.endswith('.pdf'):
                                    src_path = os.path.join(root, file)
                                    dest_path = os.path.join(extracted_dir, file)
                                    shutil.copy2(src_path, dest_path)
                                    extracted_files.append(file)

                    # Create PDF-specific Excel file with filtered data
                    excel_filename = f"{pdf_name_without_ext}_extraction.xlsx"
                    excel_path = os.path.join(pdf_dir, excel_filename)
                    
                    # Get all local extracted files for this PDF
                    local_extracted_dir = os.path.join(settings.MEDIA_ROOT, 'extracted')
                    local_files = []
                    if os.path.exists(local_extracted_dir):
                        for root, _, files in os.walk(local_extracted_dir):
                            for file in files:
                                if file.startswith(pdf_name_without_ext):
                                    local_files.append({
                                        'filename': file,
                                        'path': os.path.join(root, file)
                                    })
                    
                    # Create Excel with enhanced sheet organization
                    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                        # Summary sheet with file information
                        summary_data = {
                            'Information': [
                                'File Name',
                                'Vendor',
                                'Upload Date',
                                'Total Fields',
                                'Total Pages',
                                'Status',
                                'Original File Location',
                                'Extracted Files Count'
                            ],
                            'Value': [
                                pdf_filename,
                                pdf.vendor.name,
                                pdf.uploaded_at.strftime("%Y-%m-%d %H:%M:%S"),
                                extracted_data.count(),
                                len(set(item.page_number for item in extracted_data if item.page_number)),
                                'Extraction Complete',
                                f'original/{pdf_filename}',
                                len(local_files)
                            ]
                        }
                        pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
                        
                        # Extracted Data sheet with enhanced organization
                        data_by_page = {}
                        for item in extracted_data:
                            page = item.page_number or 'Unknown'
                            if page not in data_by_page:
                                data_by_page[page] = []
                            data_by_page[page].append({
                                'Field Type': item.field_key,
                                'Value': item.field_value,
                                'Source File': f'extracted_pdfs/page_{page}.pdf' if page != 'Unknown' else 'N/A',
                                'Extraction Time': item.created_at.strftime("%Y-%m-%d %H:%M:%S")
                            })
                        
                        # Create page-wise sheets for better organization
                        for page, data in data_by_page.items():
                            sheet_name = f'Page {page}' if page != 'Unknown' else 'Other Fields'
                            df = pd.DataFrame(data)
                            df.to_excel(writer, sheet_name=sheet_name, index=False)
                        
                        # Files Index sheet
                        files_data = [{
                            'File Name': f['filename'],
                            'Type': 'Original PDF' if f['filename'] == pdf_filename else 'Extracted Page',
                            'Location in Package': f"{'original' if f['filename'] == pdf_filename else 'extracted_pdfs'}/{f['filename']}"
                        } for f in local_files]
                        if files_data:
                            pd.DataFrame(files_data).to_excel(writer, sheet_name='Files Index', index=False)

                    # Create ZIP file with descriptive name
                    zip_filename = f"{pdf_name_without_ext}_complete_package_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        # Add all files from package directory including Excel
                        for root, _, files in os.walk(pdf_dir):
                            for file in files:
                                file_path = os.path.join(root, file)
                                arcname = os.path.relpath(file_path, pdf_dir)
                                zipf.write(file_path, arcname=arcname)

                        # Add README with enhanced organization details
                        readme_content = f"""Extraction Package for Certificate Analysis
================================================

PDF Information:
---------------
File Name: {pdf_filename}
Vendor: {pdf.vendor.name}
Upload Date: {pdf.uploaded_at.strftime('%Y-%m-%d %H:%M:%S')}
Total Fields Extracted: {extracted_data.count()}
Total Pages: {len(set(item.page_number for item in extracted_data if item.page_number))}

Package Contents:
---------------
1. Original PDF:
   - Located in: original/{pdf_filename}
   
2. Extracted Pages:
   - Located in: extracted_pdfs/
   - Contains individual PDF pages extracted from the original
   - Files are named based on their page numbers

3. Excel Analysis File ({pdf_name_without_ext}_extraction.xlsx):
   - Summary Sheet: Overview and file information
   - Page-specific Sheets: Detailed extraction data for each page
   - Files Index: Complete list of all files in this package
   
How to Use This Package:
----------------------
1. The Excel file is organized by pages for easier analysis
2. Each extracted page is saved separately in the extracted_pdfs folder
3. Cross-reference the Files Index sheet to locate specific files
4. Use the Summary sheet for a quick overview

Key Fields Found:
--------------
{chr(10).join(f"- {item.field_key}: {item.field_value}" for item in extracted_data if item.field_key in ['PLATE_NO', 'HEAT_NO', 'TEST_CERT_NO'])}

File Organization:
----------------
/original
    - Contains the original uploaded PDF
/extracted_pdfs
    - Contains all extracted pages and processed PDFs
{pdf_name_without_ext}_extraction.xlsx
    - Complete analysis and data extraction results
Extracted Files:
{chr(10).join(f"- {file}" for file in extracted_files)}
"""
                        zipf.writestr("README.txt", readme_content)
                    zip_buffer.seek(0)
                    response = FileResponse(zip_buffer, as_attachment=True, filename=zip_filename)
                    return response

                except UploadedPDF.DoesNotExist:
                    messages.error(request, "PDF file not found")
                    return redirect("dashboard")

            else:
                # Get all PDFs with extracted data
                pdfs_with_data = UploadedPDF.objects.filter(extracted_data__isnull=False).distinct()
                if not pdfs_with_data.exists():
                    messages.warning(request, "No PDFs with extracted data found")
                    return redirect("dashboard")

                package_dir = os.path.join(temp_dir, 'package')
                os.makedirs(package_dir, exist_ok=True)
                all_data = []

                for pdf in pdfs_with_data:
                    pdf_name_without_ext = os.path.splitext(os.path.basename(pdf.file.name))[0]
                    pdf_dir = os.path.join(package_dir, pdf_name_without_ext)
                    orig_dir = os.path.join(pdf_dir, 'original')
                    extracted_dir = os.path.join(pdf_dir, 'extracted_pdfs')
                    os.makedirs(orig_dir, exist_ok=True)
                    os.makedirs(extracted_dir, exist_ok=True)

                    if os.path.exists(pdf.file.path):
                        shutil.copy2(pdf.file.path, os.path.join(orig_dir, os.path.basename(pdf.file.name)))

                    base_extracted_dir = os.path.join(settings.MEDIA_ROOT, 'extracted')
                    extracted_count = 0
                    if os.path.exists(base_extracted_dir):
                        for root, _, files in os.walk(base_extracted_dir):
                            for file in files:
                                if file.startswith(pdf_name_without_ext) and file.endswith('.pdf'):
                                    src_path = os.path.join(root, file)
                                    dest_path = os.path.join(extracted_dir, file)
                                    shutil.copy2(src_path, dest_path)
                                    extracted_count += 1

                    extracted_data = ExtractedData.objects.filter(pdf=pdf).order_by('field_key')
                    key_data = {
                        field: next((item.field_value for item in extracted_data if item.field_key == field), '')
                        for field in ['PLATE_NO', 'HEAT_NO', 'TEST_CERT_NO']
                    }

                    all_data.append({
                        'PDF File': os.path.basename(pdf.file.name),
                        'Vendor': pdf.vendor.name,
                        'PLATE_NO': key_data['PLATE_NO'],
                        'HEAT_NO': key_data['HEAT_NO'],
                        'TEST_CERT_NO': key_data['TEST_CERT_NO'],
                        'Uploaded At': pdf.uploaded_at.strftime("%Y-%m-%d %H:%M:%S"),
                        'Fields Found': extracted_data.count(),
                        'Extracted Pages': extracted_count
                    })

                # Create Excel summary file locally
                excel_filename = 'extraction_summary.xlsx'
                excel_path = os.path.join(package_dir, excel_filename)
                df = pd.DataFrame(all_data)
                df.to_excel(excel_path, index=False, engine='openpyxl')

                # Create ZIP for all
                zip_filename = f"all_extractions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    
                    # Add other files from package directory
                    for root, _, files in os.walk(package_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, package_dir)
                            zipf.write(file_path, arcname=arcname)

                    readme_content = """Extraction Summary
This archive contains:
1. Original PDFs and their extracted pages
2. Excel summary of all extracted data
Directory Structure:
- extraction_summary.xlsx : Master Excel file with all extracted data
- /
- original/ : Contains the original uploaded PDF
- extracted_pdfs/ : Contains individual extracted PDFs
Summary:
"""
                    for item in all_data:
                        readme_content += f"\nPDF: {item['PDF File']}\n"
                        readme_content += f"- Vendor: {item['Vendor']}\n"
                        readme_content += f"- Uploaded: {item['Uploaded At']}\n"
                        readme_content += f"- Fields Found: {item['Fields Found']}\n"
                        readme_content += f"- Extracted Pages: {item['Extracted Pages']}\n"
                    readme_content += f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    zipf.writestr("README.txt", readme_content)

                zip_buffer.seek(0)
                response = FileResponse(zip_buffer, as_attachment=True, filename=zip_filename)
                return response

    except Exception as e:
        logger.error(f"Error creating ZIP archive: {str(e)}", exc_info=True)
        messages.error(request, "Could not create ZIP archive of PDFs and Excel data")
        return redirect("dashboard")


def download_all_pdfs_package(request):
    """
    Creates a comprehensive ZIP archive containing:
    - All processed PDF files
    - A single Excel file with all dashboard data
    
    This is different from download_pdfs_with_excel in that it creates a flatter structure
    and focuses on providing all PDFs with a single Excel summary file.
    """
    # Track any missing or unreadable files for error reporting
    missing_files = []
    unreadable_files = []
    
    try:
        # Import newly created file_utils
        from extractor.utils.file_utils import file_exists_and_readable, safe_copy_file, create_zip_from_directory
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Get all PDFs with extracted data
            pdfs_with_data = UploadedPDF.objects.filter(
                extracted_data__isnull=False,
                status='COMPLETED'
            ).distinct()
            
            if not pdfs_with_data.exists():
                messages.warning(request, "No processed PDFs found with extracted data")
                return redirect("dashboard")

            # Create directory structure
            package_dir = os.path.join(temp_dir, 'pdf_package')
            pdfs_dir = os.path.join(package_dir, 'pdfs')
            os.makedirs(pdfs_dir, exist_ok=True)
            
            # Prepare data for Excel
            all_extraction_data = []
            pdf_count = 0
            field_count = 0
            pdf_mapping = {}  # Track PDF numbering consistently
            
            # Process each PDF
            for pdf in pdfs_with_data:
                pdf_count += 1
                pdf_filename = os.path.basename(pdf.file.name)
                
                # Store in mapping dictionary
                safe_filename = f"{pdf_count:03d}_{pdf_filename}"
                pdf_mapping[pdf.id] = {
                    'original_filename': pdf_filename,
                    'safe_filename': safe_filename,
                    'pdf_number': pdf_count
                }
                
                # Validate and copy original PDF to package
                if hasattr(pdf, 'file') and pdf.file:
                    try:
                        pdf_path = pdf.file.path
                        exists, readable, error_msg = file_exists_and_readable(pdf_path)
                        
                        if not exists:
                            missing_files.append(f"{pdf_filename}: {error_msg}")
                            logger.warning(f"PDF file missing: {pdf_filename} - {error_msg}")
                            continue
                            
                        if not readable:
                            unreadable_files.append(f"{pdf_filename}: {error_msg}")
                            logger.warning(f"PDF file not readable: {pdf_filename} - {error_msg}")
                            continue
                            
                        # Safe copy to package directory
                        dest_path = os.path.join(pdfs_dir, safe_filename)
                        success, error = safe_copy_file(pdf_path, dest_path)
                        
                        if not success:
                            logger.error(f"Failed to copy PDF: {pdf_filename} - {error}")
                            unreadable_files.append(f"{pdf_filename}: Copy failed - {error}")
                            continue
                    except Exception as e:
                        logger.error(f"Error processing PDF {pdf_filename}: {str(e)}")
                        continue
                
                # Get extracted data for this PDF
                try:
                    extracted_data = ExtractedData.objects.filter(pdf=pdf).order_by('field_key')
                    field_count += extracted_data.count()
                    
                    # Get key fields for this PDF
                    for item in extracted_data:
                        all_extraction_data.append({
                            'Sr No': len(all_extraction_data) + 1,
                            'PDF File': pdf_filename,
                            'Vendor': pdf.vendor.name if hasattr(pdf, 'vendor') and pdf.vendor else 'Unknown',
                            'Field Key': item.field_key,
                            'Field Value': item.field_value,
                            'Page Number': item.page_number,
                            'Extracted At': item.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                            'PDF Path': f"pdfs/{safe_filename}"
                        })
                except Exception as e:
                    logger.error(f"Error processing extracted data for {pdf_filename}: {str(e)}")
                    continue
            
            # Check if we have any data after potential errors
            if not all_extraction_data:
                messages.error(request, "Could not create package: No valid PDF data available after filtering")
                return redirect("dashboard")
                
            # Create comprehensive Excel file with error handling
            try:
                excel_buffer = io.BytesIO()
                
                # Prepare summary data
                summary_data = {
                    'Information': [
                        'Total PDFs', 'Total Extracted Fields', 
                        'Generation Date', 'Package Type'
                    ],
                    'Value': [
                        pdf_count, field_count,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'Complete PDF Package'
                    ]
                }
                
                # Add error summary if applicable
                if missing_files or unreadable_files:
                    summary_data['Information'].append('Files With Issues')
                    summary_data['Value'].append(len(missing_files) + len(unreadable_files))
                
                # Create Excel with error handling for duplicate sheets
                try:
                    df_summary = pd.DataFrame(summary_data)
                    df_extracted = pd.DataFrame(all_extraction_data)
                    
                    # Process key fields data separately to avoid scope issues
                    key_fields_data = []
                    for pdf in pdfs_with_data:
                        if pdf.id not in pdf_mapping:
                            continue
                            
                        mapping = pdf_mapping[pdf.id]
                        pdf_filename = mapping['original_filename']
                        safe_filename = mapping['safe_filename']
                        
                        try:
                            extracted = ExtractedData.objects.filter(pdf=pdf)
                            
                            # Get values for key fields
                            field_values = {}
                            for field in ['PLATE_NO', 'HEAT_NO', 'TEST_CERT_NO']:
                                matches = [item for item in extracted if item.field_key == field]
                                field_values[field] = matches[0].field_value if matches else ''
                            
                            key_fields_data.append({
                                'PDF File': pdf_filename,
                                'Vendor': pdf.vendor.name if hasattr(pdf, 'vendor') and pdf.vendor else 'Unknown',
                                'PLATE_NO': field_values.get('PLATE_NO', ''),
                                'HEAT_NO': field_values.get('HEAT_NO', ''),
                                'TEST_CERT_NO': field_values.get('TEST_CERT_NO', ''),
                                'Fields Found': extracted.count(),
                                'Uploaded At': pdf.uploaded_at.strftime("%Y-%m-%d %H:%M:%S") if hasattr(pdf, 'uploaded_at') else 'Unknown',
                                'PDF Path': f"pdfs/{safe_filename}"
                            })
                        except Exception as e:
                            logger.error(f"Error processing key fields for {pdf_filename}: {str(e)}")
                            continue
                    
                    df_key_fields = pd.DataFrame(key_fields_data) if key_fields_data else None
                    
                    # Write to Excel with proper error handling for duplicate sheets
                    with pd.ExcelWriter(excel_buffer, engine='openpyxl', mode='w') as writer:
                        # Write each sheet with explicit error handling
                        df_summary.to_excel(writer, sheet_name='Summary', index=False)
                        
                        if not df_extracted.empty:
                            df_extracted.to_excel(writer, sheet_name='All Extracted Data', index=False)
                        
                        if df_key_fields is not None and not df_key_fields.empty:
                            df_key_fields.to_excel(writer, sheet_name='Key Fields Summary', index=False)
                            
                        # Add error details sheet if needed
                        if missing_files or unreadable_files:
                            error_data = {
                                'File': [],
                                'Error Type': [],
                                'Error Details': []
                            }
                            
                            for f in missing_files:
                                parts = f.split(':', 1)
                                error_data['File'].append(parts[0])
                                error_data['Error Type'].append('Missing')
                                error_data['Error Details'].append(parts[1] if len(parts) > 1 else '')
                                
                            for f in unreadable_files:
                                parts = f.split(':', 1)
                                error_data['File'].append(parts[0])
                                error_data['Error Type'].append('Unreadable')
                                error_data['Error Details'].append(parts[1] if len(parts) > 1 else '')
                                
                            df_errors = pd.DataFrame(error_data)
                            df_errors.to_excel(writer, sheet_name='File Issues', index=False)
                            
                except Exception as excel_err:
                    logger.error(f"Error creating Excel file: {str(excel_err)}", exc_info=True)
                    raise RuntimeError(f"Excel file creation failed: {str(excel_err)}")
            except Exception as e:
                logger.error(f"Excel processing error: {str(e)}", exc_info=True)
                messages.error(request, f"Could not create Excel file: {str(e)}")
                return redirect("dashboard")
            
            # Create README file with additional error information
            readme_content = f"""# PDF Extraction Package
## Summary
- Total PDFs: {pdf_count}
- Total Extracted Fields: {field_count}
- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Contents
This package contains:
1. All processed PDF files in the 'pdfs' folder
2. Excel file with all extracted data: 'all_extracted_data.xlsx'

## Excel File Structure
The Excel file contains the following sheets:
- Summary: Overview of this package
- All Extracted Data: Complete dataset with all extracted fields
- Key Fields Summary: Summary of important fields like PLATE_NO, HEAT_NO, TEST_CERT_NO
"""

            # Add file issue information if any
            if missing_files or unreadable_files:
                readme_content += f"""
## File Issues
There were issues with {len(missing_files) + len(unreadable_files)} files:
- Missing files: {len(missing_files)}
- Unreadable files: {len(unreadable_files)}
These issues are detailed in the 'File Issues' sheet in the Excel file.
"""

            readme_content += """
## PDF Files
The PDFs are numbered sequentially for easy reference. The original filenames are preserved
with a prefix (e.g., 001_filename.pdf, 002_filename.pdf).

## PDF to Excel Mapping
Each entry in the Excel file contains a 'PDF Path' column that shows the relative path 
to the corresponding PDF file in this package.
"""
            
            try:
                readme_path = os.path.join(package_dir, 'README.txt')
                with open(readme_path, 'w') as f:
                    f.write(readme_content)
            except Exception as e:
                logger.warning(f"Could not create README file: {str(e)}")
                # Continue without README if it fails
            
            # Create ZIP file with robust error handling
            try:
                zip_filename = f"complete_pdf_package_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
                zip_buffer = io.BytesIO()
                
                # Create ZIP manually to include Excel from buffer
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    # Add Excel file from buffer
                    excel_buffer.seek(0)
                    zipf.writestr('all_extracted_data.xlsx', excel_buffer.getvalue())
                    
                    # Add other files from package directory (excluding .xlsx files)
                    for root, _, files in os.walk(package_dir):
                        for file in files:
                            if not file.endswith('.xlsx'):  # Skip xlsx files since we're adding from buffer
                                file_path = os.path.join(root, file)
                                arcname = os.path.relpath(file_path, package_dir)
                                zipf.write(file_path, arcname=arcname)
                
                zip_buffer.seek(0)
                
                response = FileResponse(zip_buffer, as_attachment=True, filename=zip_filename)
                return response
            except Exception as zip_err:
                error_msg = f"Error creating ZIP archive: {str(zip_err)}"
                logger.error(error_msg, exc_info=True)
                store_dashboard_message(request, "Could not create ZIP archive", 'error', str(zip_err))
                return redirect("dashboard")
            
    except Exception as e:
        error_msg = f"Error creating complete PDF package: {str(e)}"
        logger.error(error_msg, exc_info=True)
        store_dashboard_message(request, "Could not create the complete PDF package", 'error', str(e))
        return redirect("dashboard")


def upload_pdf(request):
    """Handle PDF upload view"""
    vendors = Vendor.objects.all()
    return render(request, 'extractor/upload.html', {'vendors': vendors})


def logout_view(request):
    """Handle user logout"""
    logout(request)
    return redirect('login')






def custom_logout(request):
    """Custom logout view that redirects to admin login"""
    logout(request)
    return redirect('admin:login')

