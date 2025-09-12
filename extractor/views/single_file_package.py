import os
import io
import zipfile
import logging
import tempfile
from datetime import datetime

from django.http import HttpResponse, FileResponse
from django.shortcuts import get_object_or_404, redirect
from django.conf import settings
from django.contrib import messages

from extractor.models import UploadedPDF, ExtractedData
import pandas as pd

logger = logging.getLogger(__name__)

def create_single_file_package(pdf_id):
    """
    Creates a ZIP archive containing only the extracted PDFs and Excel data for a specific uploaded PDF.
    
    Args:
        pdf_id: The ID of the UploadedPDF record to package
        
    Returns:
        tuple: (success, result) where result is either the file buffer or an error message.
    """
    # Track success/failure stats
    stats = {
        'excel_included': False,
        'pdf_count': 0,
        'errors': []
    }
    
    try:
        # Get the PDF record
        try:
            pdf = get_object_or_404(UploadedPDF, id=pdf_id)
        except Exception as e:
            logger.error(f"Could not find PDF with ID {pdf_id}: {str(e)}")
            return False, f"PDF not found with ID {pdf_id}"
        
        # Get extracted data for this PDF
        extracted_data = ExtractedData.objects.filter(pdf=pdf).order_by('field_key')
        if not extracted_data.exists():
            return False, f"No extracted data found for PDF {pdf.file.name}"
        
        # Create timestamp for unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        pdf_name_without_ext = os.path.splitext(os.path.basename(pdf.file.name))[0]
        zip_filename = f"{pdf_name_without_ext}_package_{timestamp}.zip"
        
        # Create in-memory buffer for the ZIP file
        buffer = io.BytesIO()
        
        # Define paths
        media_root = os.path.abspath(settings.MEDIA_ROOT)
        base_dir = os.path.abspath(settings.BASE_DIR)
        
        logger.info(f"Creating ZIP package for PDF ID {pdf_id}: {pdf.file.name}")
        
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            # Add the original PDF if it exists
            if hasattr(pdf, 'file') and pdf.file:
                try:
                    pdf_path = pdf.file.path
                    if os.path.exists(pdf_path):
                        # Add to ZIP with a clean arcname
                        pdf_filename = os.path.basename(pdf.file.name)
                        zip_file.write(pdf_path, arcname=f"original/{pdf_filename}")
                        logger.info(f"Added original PDF to package: {pdf_filename}")
                    else:
                        error_msg = f"Original PDF file not found at: {pdf_path}"
                        stats['errors'].append(error_msg)
                        logger.warning(error_msg)
                except Exception as e:
                    error_msg = f"Error adding original PDF: {str(e)}"
                    stats['errors'].append(error_msg)
                    logger.error(error_msg)
            
            # Create Excel file with extraction data
            try:
                excel_buffer = io.BytesIO()
                
                # Summary sheet
                summary_data = {
                    'Information': [
                        'File Name', 'Vendor', 'Upload Date', 'Total Fields',
                        'Total Pages', 'Status'
                    ],
                    'Value': [
                        os.path.basename(pdf.file.name),
                        pdf.vendor.name if hasattr(pdf, 'vendor') and pdf.vendor else 'Unknown',
                        pdf.uploaded_at.strftime("%Y-%m-%d %H:%M:%S") if hasattr(pdf, 'uploaded_at') else 'Unknown',
                        extracted_data.count(),
                        len(set(item.page_number for item in extracted_data if item.page_number)),
                        'Extraction Complete'
                    ]
                }
                
                # Create Excel with extraction data
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
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
                
                # Reset buffer position and add to ZIP
                excel_buffer.seek(0)
                zip_file.writestr(f"{pdf_name_without_ext}_extraction.xlsx", excel_buffer.getvalue())
                stats['excel_included'] = True
                logger.info(f"Added extraction Excel file to package")
                
            except Exception as e:
                error_msg = f"Error creating Excel file: {str(e)}"
                stats['errors'].append(error_msg)
                logger.error(error_msg)
            
            # Add extracted PDFs
            extracted_dir = os.path.join(media_root, "extracted")
            if os.path.exists(extracted_dir) and os.path.isdir(extracted_dir):
                pdf_count = 0
                
                # Look for all extracted PDFs that match this file's name
                for root, dirs, files in os.walk(extracted_dir):
                    for filename in files:
                        # Check if the filename starts with this PDF's name and ends with .pdf
                        if (filename.startswith(pdf_name_without_ext) or 
                            f"_{pdf_name_without_ext}_" in filename) and filename.endswith('.pdf'):
                            pdf_path = os.path.join(root, filename)
                            try:
                                # Add to ZIP with proper arcname
                                zip_file.write(pdf_path, arcname=f"extracted_pdfs/{filename}")
                                pdf_count += 1
                            except Exception as e:
                                error_msg = f"Error adding extracted PDF {filename}: {str(e)}"
                                stats['errors'].append(error_msg)
                                logger.error(error_msg)
                
                stats['pdf_count'] = pdf_count
                logger.info(f"Added {pdf_count} extracted PDFs to package")
            else:
                error_msg = f"Extracted PDFs directory not found at: {extracted_dir}"
                stats['errors'].append(error_msg)
                logger.warning(error_msg)
            
            # Create README file
            readme_content = f"""Extraction Package for {pdf.file.name}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Contents:
- original/ : Contains the original uploaded PDF
- extracted_pdfs/ : Contains all extracted pages from this PDF
- {pdf_name_without_ext}_extraction.xlsx : Excel file with extraction data

Summary:
- Vendor: {pdf.vendor.name if hasattr(pdf, 'vendor') and pdf.vendor else 'Unknown'}
- Upload Date: {pdf.uploaded_at.strftime("%Y-%m-%d %H:%M:%S") if hasattr(pdf, 'uploaded_at') else 'Unknown'}
- Extracted Fields: {extracted_data.count()}
- Extracted Pages: {stats['pdf_count']}

Notes:
This package contains only the files related to the selected PDF.
"""
            zip_file.writestr("README.txt", readme_content)
        
        # Check if we included any files
        if stats['pdf_count'] == 0 and not stats['excel_included']:
            logger.error(f"No files were added to the ZIP package for PDF {pdf_id}")
            return False, "No files found to include in the package."
        
        # Prepare buffer for response
        buffer.seek(0)
        
        # Log success
        logger.info(f"ZIP package created successfully for PDF {pdf_id} with {stats['pdf_count']} PDFs and Excel: {stats['excel_included']}")
        
        return True, (buffer, zip_filename, stats)
        
    except Exception as e:
        logger.exception(f"Error creating single file package: {str(e)}")
        return False, f"Error creating package: {str(e)}. Please contact support."


def download_single_file_package(request, pdf_id):
    """
    Downloads a ZIP package containing extracted PDFs and Excel data for a specific uploaded PDF.
    """
    try:
        success, result = create_single_file_package(pdf_id)
        
        if not success:
            # Show error message and redirect
            messages.error(request, result)
            return redirect('dashboard')
        
        # Unpack the result
        buffer, zip_filename, stats = result
        
        # Create response
        response = FileResponse(
            buffer,
            as_attachment=True,
            filename=zip_filename
        )
        
        # Set additional headers for better browser compatibility
        response['Content-Type'] = 'application/zip'
        response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
        response['Content-Length'] = buffer.getbuffer().nbytes
        
        return response
        
    except Exception as e:
        logger.exception(f"Error creating single file package response: {str(e)}")
        messages.error(request, f"Error creating package: {str(e)}")
        return redirect('dashboard')
