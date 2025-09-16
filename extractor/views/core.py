"""Core functionality views"""
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, FileResponse
from django.utils import timezone
from django.conf import settings
from django.db.models import Count
from celery.result import AsyncResult
import pandas as pd
import os
import io
import json
import logging
import tempfile
import shutil
import zipfile
from datetime import datetime
from ..models import ExtractedData, Vendor, UploadedPDF
from ..utils.extractor import extract_pdf_fields
from ..utils.config_loader import load_vendor_config
from ..utils.excel_helper import create_template_if_not_exists, apply_formatting, write_dataframe_to_sheet
from ..tasks import process_pdf_file

logger = logging.getLogger('extractor')

def dashboard(request):
    """Dashboard view showing summary of uploaded PDFs and extraction status"""
    recent_pdfs = UploadedPDF.objects.all().order_by('-uploaded_at')[:10]
    vendors = Vendor.objects.annotate(pdf_count=Count('pdfs'))
    
    # Get extraction data for display
    data = []
    for pdf in recent_pdfs:
        extracted_data = ExtractedData.objects.filter(pdf=pdf)
        data.append({
            'pdf': pdf,
            'pdf_id': pdf.id,  # Include PDF ID explicitly
            'extracted_count': extracted_data.count(),
            'last_extracted': extracted_data.order_by('-created_at').first(),
            'key_fields': {
                field: next((item.field_value for item in extracted_data if item.field_key == field), '')
                for field in ['PLATE_NO', 'HEAT_NO', 'TEST_CERT_NO']
            },
            'PLATE_NO': next((item.field_value for item in extracted_data if item.field_key == 'PLATE_NO'), ''),
            'HEAT_NO': next((item.field_value for item in extracted_data if item.field_key == 'HEAT_NO'), ''),
            'TEST_CERT_NO': next((item.field_value for item in extracted_data if item.field_key == 'TEST_CERT_NO'), ''),
            'Vendor': pdf.vendor.name if hasattr(pdf, 'vendor') and pdf.vendor else 'Unknown',
            'Source PDF': pdf.file.name,
            'Created': pdf.uploaded_at.strftime("%Y-%m-%d %H:%M:%S") if hasattr(pdf, 'uploaded_at') else 'Unknown',
            'Filename': os.path.basename(pdf.file.name),
            'Remarks': '',
            'Page': ''
        })
    
    # Calculate totals for the dashboard
    total_pdfs = UploadedPDF.objects.count()
    total_extracted = ExtractedData.objects.values('pdf').distinct().count()
    total_rows = ExtractedData.objects.count()
    
    # Add debug info for static files if in debug mode
    static_debug = None
    if settings.DEBUG:
        static_debug = {
            'STATIC_URL': settings.STATIC_URL,
            'STATIC_ROOT': str(settings.STATIC_ROOT),
            'STATICFILES_DIRS': [str(path) for path in settings.STATICFILES_DIRS]
        }
    
    # Get recent extractions for the table
    recent_extractions = ExtractedData.objects.select_related('pdf', 'vendor').order_by('-created_at')[:20]
    
    context = {
        'recent_pdfs': recent_pdfs,
        'vendors': vendors,
        'data': data,
        'total_pdfs': total_pdfs,
        'total_extracted': total_extracted,
        'total_rows': total_rows,
        'static_debug': json.dumps(static_debug) if static_debug else None,
        'now': timezone.now(),
        'recent_extractions': recent_extractions,
    }
    return render(request, 'extractor/dashboard.html', context)

def upload_pdf(request):
    """Handle PDF upload view"""
    vendors = Vendor.objects.all()
    return render(request, 'extractor/upload.html', {'vendors': vendors})

def create_extraction_excel(excel_path, pdf_obj, extracted_data):
    """Creates a detailed Excel file with multiple sheets for extracted data"""
    import pandas as pd
    import openpyxl
    from openpyxl.utils import get_column_letter
    
    pdf_filename = os.path.basename(pdf_obj.file.name)
    
    # Ensure we have a template
    template_path = create_template_if_not_exists()
    
    # For file-like objects (BytesIO), we need to create a copy of the template
    if hasattr(excel_path, 'write'):
        # This is a file-like object (BytesIO)
        with open(template_path, 'rb') as template_file:
            template_content = template_file.read()
            # We need to write the template content to the BytesIO object
            excel_path.write(template_content)
            excel_path.seek(0)  # Reset position for reading
            
        # Load the workbook from the BytesIO object
        workbook = openpyxl.load_workbook(excel_path)
        
        # Prepare DataFrames
        summary_data = pd.DataFrame({
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
        })
        
        main_data = pd.DataFrame([{
            'Field Type': item.field_key,
            'Extracted Value': item.field_value,
            'Page Number': item.page_number,
            'PDF Location': f'extracted_pdfs/page_{item.page_number}.pdf' if item.page_number else 'N/A',
            'Extracted At': item.created_at.strftime("%Y-%m-%d %H:%M:%S")
        } for item in extracted_data]) if extracted_data.exists() else pd.DataFrame()
        
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
        
        key_data_df = pd.DataFrame(key_data) if key_data else pd.DataFrame()
        
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
        
        page_data_df = pd.DataFrame(page_data) if page_data else pd.DataFrame()
        
        # Write data to sheets
        write_dataframe_to_sheet(workbook, 'Summary', summary_data)
        
        if not main_data.empty:
            write_dataframe_to_sheet(workbook, 'Extracted Data', main_data)
        
        if not key_data_df.empty:
            write_dataframe_to_sheet(workbook, 'Key Fields', key_data_df)
        
        if not page_data_df.empty:
            write_dataframe_to_sheet(workbook, 'Page Summary', page_data_df)
        
        # Apply consistent formatting
        apply_formatting(workbook)
        
        # Clear the BytesIO object and save the workbook to it
        excel_path.seek(0)
        excel_path.truncate(0)
        workbook.save(excel_path)
        excel_path.seek(0)  # Reset position for reading
        
    else:
        # This is a file path
        import shutil
        # Copy the template to the destination
        shutil.copy2(template_path, excel_path)
        
        # Then use pandas to write to it
        with pd.ExcelWriter(excel_path, engine='openpyxl', mode='a') as writer:
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
            
            # Main extraction sheet
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
            
            # Load the workbook to apply formatting
            writer.book = apply_formatting(writer.book)

def download_excel(request):
    """Download extraction results as Excel file"""
    pdf_id = request.GET.get('pdf_id')
    # Get the referring page to redirect back if there's an error
    referer = request.META.get('HTTP_REFERER', '/dashboard/')
    
    # If no PDF ID is provided, serve the master Excel file
    if not pdf_id:
        from django.conf import settings
        master_path = os.path.join(settings.MEDIA_ROOT, "backups", "master.xlsx")
        
        if os.path.exists(master_path):
            try:
                response = FileResponse(
                    open(master_path, "rb"),
                    as_attachment=True,
                    filename="Master_Extracted_Data_ReadOnly.xlsx"
                )
                response['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                return response
            except Exception as e:
                messages.error(request, f"Could not serve Excel file: {str(e)}")
                return redirect('dashboard')
        else:
            messages.error(request, "Master Excel file not found")
            return redirect('dashboard')
    
    try:
        pdf = UploadedPDF.objects.get(id=pdf_id)
        extracted_data = ExtractedData.objects.filter(pdf=pdf).order_by('field_key')
        
        if not extracted_data.exists():
            messages.warning(request, "No extracted data found for this PDF")
            return redirect(referer)
            
        # Create Excel file
        excel_buffer = io.BytesIO()
        create_extraction_excel(excel_buffer, pdf, extracted_data)
        
        # Prepare response
        excel_buffer.seek(0)
        response = FileResponse(
            excel_buffer,
            as_attachment=True,
            filename=f"{os.path.splitext(pdf.file.name)[0]}_extraction.xlsx"
        )
        return response
        
    except UploadedPDF.DoesNotExist:
        messages.error(request, "PDF file not found")
        return redirect(referer)
    except Exception as e:
        logger.error(f"Error creating Excel file: {str(e)}", exc_info=True)
        messages.error(request, "Could not create Excel file")
        return redirect(referer)

def task_status(request, task_id):
    """Get the status of an async task"""
    task = AsyncResult(task_id)
    data = {
        'state': task.state,
    }
    if task.state == 'SUCCESS':
        data['result'] = task.get()
    return JsonResponse(data)

def regenerate_excel(request):
    """Regenerates the Excel file for all extracted data."""
    # Get the referring page to redirect back if there's an error
    referer = request.META.get('HTTP_REFERER', '/dashboard/')
    
    try:
        pdf_id = request.GET.get('pdf_id')
        if pdf_id:
            # Regenerate single PDF
            pdf = UploadedPDF.objects.get(id=pdf_id)
            extracted_data = ExtractedData.objects.filter(pdf=pdf).order_by('field_key')
            
            if not extracted_data.exists():
                messages.warning(request, "No extracted data found for this PDF")
                return redirect(referer)
                
            # Create Excel file
            excel_buffer = io.BytesIO()
            create_extraction_excel(excel_buffer, pdf, extracted_data)
            
            # Prepare response
            excel_buffer.seek(0)
            response = FileResponse(
                excel_buffer,
                as_attachment=True,
                filename=f"{os.path.splitext(pdf.file.name)[0]}_extraction_regenerated.xlsx"
            )
            messages.success(request, "Excel file regenerated successfully")
            return response
            
        else:
            # No PDF ID provided - redirect back
            messages.error(request, "No PDF ID provided")
            return redirect(referer)
            
    except UploadedPDF.DoesNotExist:
        messages.error(request, "PDF not found")
        return redirect(referer)
    except Exception as e:
        logger.error(f"Error regenerating Excel file: {str(e)}", exc_info=True)
        messages.error(request, "Could not regenerate Excel file")
        return redirect(referer)

def download_pdfs_with_excel(request):
    """
    Creates a ZIP file containing:
    1. Original PDF file
    2. All extracted PDF pages
    3. Detailed Excel file with extraction data
    4. README file explaining the contents
    """
    pdf_id = request.GET.get('pdf_id')
    source_pdf = request.GET.get('source')
    # Get the referring page to redirect back if there's an error
    referer = request.META.get('HTTP_REFERER', '/dashboard/')
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            if pdf_id or source_pdf:
                try:
                    # Get the PDF file
                    if pdf_id:
                        pdf = UploadedPDF.objects.get(id=pdf_id)
                    else:
                        pdf_filename = os.path.basename(source_pdf)
                        pdf = UploadedPDF.objects.filter(file__contains=pdf_filename).first()
                        if not pdf:
                            messages.warning(request, f"No PDF found with filename: {pdf_filename}")
                            return redirect(referer)
                    
                    # Get extracted data
                    extracted_data = ExtractedData.objects.filter(pdf=pdf).order_by('field_key')
                    if not extracted_data.exists():
                        messages.warning(request, "No extracted data found for this PDF")
                        return redirect(referer)
                    
                    # Set up directory structure
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
                    
                    # Create Excel file
                    excel_path = os.path.join(pdf_dir, 'extraction_summary.xlsx')
                    create_extraction_excel(excel_path, pdf, extracted_data)
                    
                    # Create ZIP file
                    zip_filename = f"{pdf_name_without_ext}_extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
                    zip_buffer = io.BytesIO()
                    
                    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        # Add all files maintaining directory structure
                        for root, _, files in os.walk(pdf_dir):
                            for file in files:
                                file_path = os.path.join(root, file)
                                arcname = os.path.relpath(file_path, pdf_dir)
                                zipf.write(file_path, arcname=arcname)
                        
                        # Add README
                        readme_content = f"""Extraction Summary

PDF: {pdf_filename}
Vendor: {pdf.vendor.name}
Uploaded: {pdf.uploaded_at.strftime('%Y-%m-%d %H:%M:%S')}
Extracted Fields: {extracted_data.count()}

Directory Structure:
- original/           : Original uploaded PDF
- extracted_pdfs/     : Individual extracted pages
- extraction_summary.xlsx : Detailed Excel file with:
  * Summary          : Overview and statistics
  * Extracted Data   : All extracted fields
  * Key Fields       : Certificate data (PLATE_NO, HEAT_NO, etc.)
  * Page Summary     : Page-by-page breakdown

Extracted Files:
{chr(10).join(f"- {file}" for file in extracted_files)}
"""
                        zipf.writestr("README.txt", readme_content)
                    
                except UploadedPDF.DoesNotExist:
                    messages.error(request, "PDF file not found")
                    return redirect("dashboard")
                    
            else:
                # Get all PDFs that have extracted data
                pdfs_with_data = UploadedPDF.objects.filter(extracted_data__isnull=False).distinct()
                
                if not pdfs_with_data.exists():
                    messages.warning(request, "No PDFs with extracted data found")
                    return redirect("dashboard")
                
                # Set up base directory for package
                package_dir = os.path.join(temp_dir, 'package')
                os.makedirs(package_dir, exist_ok=True)
                
                # Process PDFs and create summary
                all_data = []
                for pdf in pdfs_with_data:
                    # Create individual PDF directory
                    pdf_dir = os.path.join(package_dir, pdf_name_without_ext)
                    orig_dir = os.path.join(pdf_dir, 'original')
                    extracted_dir = os.path.join(pdf_dir, 'extracted_pdfs')
                    os.makedirs(orig_dir, exist_ok=True)
                    os.makedirs(extracted_dir, exist_ok=True)
                    
                    # Copy original PDF
                    if os.path.exists(pdf.file.path):
                        shutil.copy2(pdf.file.path, os.path.join(orig_dir, pdf_filename))
                    
                    # Find and copy extracted PDFs
                    base_extracted_dir = os.path.join(settings.MEDIA_ROOT, 'extracted')
                    if os.path.exists(base_extracted_dir):
                        extracted_count = 0
                        for root, _, files in os.walk(base_extracted_dir):
                            for file in files:
                                if file.startswith(pdf_name_without_ext) and file.endswith('.pdf'):
                                    src_path = os.path.join(root, file)
                                    dest_path = os.path.join(extracted_dir, file)
                                    shutil.copy2(src_path, dest_path)
                                    extracted_count += 1
                    
                    # Add to summary data
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
                
                # Create Excel summary
                excel_path = os.path.join(package_dir, 'extraction_summary.xlsx')
                df = pd.DataFrame(all_data)
                df.to_excel(excel_path, index=False)
                
                # Create ZIP file
                zip_filename = f"all_extractions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
                zip_buffer = io.BytesIO()
                
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    # Add all files maintaining directory structure
                    for root, _, files in os.walk(package_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, package_dir)
                            zipf.write(file_path, arcname=arcname)
                    
                    # Add README
                    readme_content = """Extraction Summary

This archive contains:
1. Original PDFs and their extracted pages
2. Excel summary of all extracted data

Directory Structure:
- extraction_summary.xlsx : Master Excel file with all extracted data
- <pdf_name>/
  - original/           : Contains the original uploaded PDF
  - extracted_pdfs/     : Contains individual extracted PDFs

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
            
            # Reset buffer position and return response
            zip_buffer.seek(0)
            response = FileResponse(
                zip_buffer,
                as_attachment=True,
                filename=zip_filename
            )
            return response
            
    except Exception as e:
        logger.error(f"Error creating ZIP archive: {str(e)}", exc_info=True)
        messages.error(request, "Could not create ZIP archive of PDFs and Excel data")
        return redirect(referer)

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from ..models import UploadedPDF, Vendor
from ..tasks import process_pdf_file
import hashlib

@csrf_exempt
def process_pdf(request):
    if request.method == 'POST':
        vendor_id = request.POST.get('vendor')
        vendor = Vendor.objects.filter(id=vendor_id).first()
        pdf_file = request.FILES.get('pdf')
        
        if not vendor or not pdf_file:
            messages.error(request, "Missing vendor or PDF file.")
            logger.error("Missing vendor or PDF file in request")
            return JsonResponse({'error': 'Missing vendor or PDF file.', 'redirect': '/dashboard/'}, status=400)

        # Verify file is a PDF
        if not pdf_file.name.lower().endswith('.pdf'):
            messages.error(request, "Uploaded file must be a PDF")
            logger.error(f"File {pdf_file.name} is not a PDF")
            return JsonResponse({'error': 'Uploaded file must be a PDF', 'redirect': '/dashboard/'}, status=400)

        # Check for duplicate files - read PDF content and calculate hash
        file_hash = hashlib.sha256(pdf_file.read()).hexdigest()
        pdf_file.seek(0)  # Reset file pointer after reading
        
        # Debug print for duplicate check
        logger.info(f"[DEBUG] Checking for duplicate file with hash: {file_hash}")
        
        # Check if this PDF was already uploaded
        existing_pdf = UploadedPDF.objects.filter(file_hash=file_hash).first()
        if existing_pdf:
            # Debug print for duplicate match
            logger.info(f"[DEBUG] Duplicate file detected! Original vendor: {existing_pdf.vendor.name}, Chosen vendor: {vendor.name}")
            
            # If vendor mismatch, redirect with error
            if existing_pdf.vendor.id != vendor.id:
                messages.error(request, f"Choose correct vendor for the PDF file. This PDF was previously uploaded for vendor '{existing_pdf.vendor.name}'")
                logger.warning(f"Vendor mismatch for PDF {pdf_file.name}. Expected: {existing_pdf.vendor.name}, Got: {vendor.name}")
                return JsonResponse({'error': 'Vendor mismatch', 'redirect': '/upload/'}, status=200)
            
            # If duplicate with same vendor, show warning
            messages.warning(request, f"Duplicate file detected. This PDF was already processed on {existing_pdf.uploaded_at.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.warning(f"Duplicate PDF detected: {pdf_file.name}")
            return JsonResponse({'redirect': '/dashboard/'}, status=200)
        
        # Save PDF file
        file_path = default_storage.save(f"uploads/{pdf_file.name}", ContentFile(pdf_file.read()))
        pdf_file.seek(0)
        
        # Create UploadedPDF entry with PENDING status to avoid NOT NULL constraint
        uploaded_pdf = UploadedPDF.objects.create(
            vendor=vendor,
            file=file_path,
            file_hash=file_hash,
            file_size=pdf_file.size,
            status='PENDING'  # Always set a valid status
        )
        
        # Debug print for extraction start
        logger.info(f"[DEBUG] Starting extraction for PDF: {pdf_file.name}, Vendor: {vendor.name}")
        
        # Load vendor config - try multiple locations
        from extractor.utils.config_loader import find_vendor_config
        vendor_config, config_path = find_vendor_config(vendor, settings)
        
        if not vendor_config:
            uploaded_pdf.status = 'ERROR'
            uploaded_pdf.save()
            messages.error(request, f"Error loading vendor config for {vendor.name}")
            logger.error(f"Config for vendor '{vendor.name}' not found")
            return JsonResponse({'error': 'Error loading vendor config', 'redirect': '/dashboard/'}, status=500)
        
        # Trigger extraction via Celery
        task = process_pdf_file.delay(uploaded_pdf.id, vendor_config)
        
        # Debug print for task creation
        logger.info(f"[DEBUG] Extraction task created with ID: {task.id}")
        
        # Set success message
        messages.success(request, "Extraction started")
        
        # Return success response with task ID
        return JsonResponse({
            'status': 'success', 
            'pdf_id': uploaded_pdf.id, 
            'task_id': task.id,
            'redirect': '/dashboard/'
        })
    return JsonResponse({'error': 'Invalid request'}, status=400)


def task_progress(request, task_id):
    """Get progress percentage for a Celery task"""
    from celery.result import AsyncResult
    
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
