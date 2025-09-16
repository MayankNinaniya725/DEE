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
                
                # Create Excel with extraction data in the same format as master_log.xlsx
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                    # Summary sheet - File information
                    pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
                    
                    # Group data by combinations for proper row structure
                    combinations = {}
                    sr_no = 1
                    
                    # Group extracted data by page and combination
                    for item in extracted_data:
                        page_key = f"page_{item.page_number}"
                        if page_key not in combinations:
                            combinations[page_key] = {
                                'Sr No': sr_no,
                                'Vendor': item.vendor.name if item.vendor else 'Unknown',
                                'PLATE_NO': '', 'HEAT_NO': '', 'TEST_CERT_NO': '',
                                'Page': item.page_number,
                                'Source PDF': os.path.basename(pdf.file.name),
                                'Created': item.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                                'Remarks': '',
                                'OCR_Used': False
                            }
                            sr_no += 1
                        
                        # Update the combination with field values
                        if item.field_key in ['PLATE_NO', 'HEAT_NO', 'TEST_CERT_NO']:
                            combinations[page_key][item.field_key] = item.field_value
                    
                    # Generate Filename for each combination based on key fields
                    for page_key, combo in combinations.items():
                        plate_no = combo.get('PLATE_NO', '').replace('/', '-')
                        heat_no = combo.get('HEAT_NO', '').replace('/', '-')
                        test_cert = combo.get('TEST_CERT_NO', '').replace('/', '-')
                        
                        if plate_no or heat_no or test_cert:
                            combo['Filename'] = f"{plate_no}_{heat_no}_{test_cert}.pdf"
                        else:
                            combo['Filename'] = f"page_{combo['Page']}.pdf"
                        
                        # Generate Hash (simplified version)
                        import hashlib
                        hash_key = f"{combo['Vendor']}|{plate_no}|{heat_no}|{test_cert}"
                        combo['Hash'] = hashlib.md5(hash_key.encode('utf-8')).hexdigest()
                    
                    # Extracted Data sheet - matches master_log.xlsx format
                    extracted_data_list = list(combinations.values())
                    if extracted_data_list:
                        extracted_df = pd.DataFrame(extracted_data_list)
                        # Reorder columns to match master_log.xlsx
                        column_order = ['Sr No', 'Vendor', 'PLATE_NO', 'HEAT_NO', 'TEST_CERT_NO', 
                                       'Filename', 'Page', 'Source PDF', 'Created', 'Hash', 'Remarks', 'OCR_Used']
                        extracted_df = extracted_df.reindex(columns=column_order, fill_value='')
                        extracted_df.to_excel(writer, sheet_name='Extracted Data', index=False)
                    
                    # Key Fields sheet - summary of unique key field values
                    key_fields = ['PLATE_NO', 'HEAT_NO', 'TEST_CERT_NO']
                    key_data = []
                    for field in key_fields:
                        unique_values = set()
                        for combo in combinations.values():
                            value = combo.get(field, '')
                            if value:
                                unique_values.add(value)
                        
                        for value in unique_values:
                            # Find the combination that contains this value
                            for combo in combinations.values():
                                if combo.get(field) == value:
                                    key_data.append({
                                        'Field': field,
                                        'Value': value,
                                        'Page': combo['Page'],
                                        'PDF File': f"extracted_pdfs/{combo['Filename']}",
                                        'Status': 'Verified' if value else 'Not Found'
                                    })
                                    break
                    
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
            
            # Add extracted PDFs using vendor and page number info from ExtractedData
            pdf_count = 0
            extracted_dir = os.path.join(media_root, "extracted")
            
            # Get all vendor folders available
            available_vendor_folders = []
            if os.path.exists(extracted_dir):
                available_vendor_folders = [d for d in os.listdir(extracted_dir) 
                                           if os.path.isdir(os.path.join(extracted_dir, d))]
            
            # Build a mapping of vendor names to folder names
            vendor_folder_map = {}
            for item in extracted_data:
                vendor_name = item.vendor.name
                if vendor_name not in vendor_folder_map:
                    # Try to find a matching folder
                    vendor_folder = None
                    vendor_name_clean = vendor_name.replace(' ', '_')
                    
                    # First try exact match
                    if vendor_name_clean in available_vendor_folders:
                        vendor_folder = vendor_name_clean
                    else:
                        # Try fuzzy matching - find folder that contains key parts of vendor name
                        vendor_parts = vendor_name.upper().split()
                        for folder in available_vendor_folders:
                            folder_upper = folder.upper()
                            # Check if folder contains key parts of vendor name
                            if any(part in folder_upper for part in vendor_parts if len(part) > 3):
                                vendor_folder = folder
                                break
                    
                    vendor_folder_map[vendor_name] = vendor_folder
            
            # Now collect extracted PDFs - deduplicated by combination key
            added_files = set()  # Track to avoid duplicates
            combination_pdfs = {}  # Map combination keys to PDF filenames
            
            # First, identify unique combinations from the extracted data
            for item in extracted_data:
                vendor_folder = vendor_folder_map.get(item.vendor.name)
                if not vendor_folder:
                    continue
                    
                vendor_dir = os.path.join(extracted_dir, vendor_folder)
                if not os.path.exists(vendor_dir):
                    continue
                
                # Build combination key for this item
                page_key = f"page_{item.page_number}"
                if page_key not in combination_pdfs:
                    # Collect all field values for this page to build combination key
                    page_data = [d for d in extracted_data if d.page_number == item.page_number]
                    plate_no = heat_no = test_cert = ''
                    
                    for field_item in page_data:
                        if field_item.field_key == 'PLATE_NO':
                            plate_no = field_item.field_value
                        elif field_item.field_key == 'HEAT_NO':
                            heat_no = field_item.field_value
                        elif field_item.field_key == 'TEST_CERT_NO':
                            test_cert = field_item.field_value
                    
                    # Create combination key
                    combination_key = f"{heat_no}_{plate_no}_{test_cert}".replace('/', '-').replace(' ', '_')
                    
                    # Look for PDF files that match this combination
                    matching_pdfs = []
                    for fname in os.listdir(vendor_dir):
                        if fname.lower().endswith('.pdf'):
                            # Check if filename contains key parts of the combination
                            fname_clean = fname.lower().replace('.pdf', '').replace('-', '_').replace(' ', '_')
                            
                            # Look for combinations that match key field values
                            if (plate_no and plate_no.lower().replace('/', '_').replace('-', '_') in fname_clean) or \
                               (heat_no and heat_no.lower().replace('/', '_').replace('-', '_') in fname_clean) or \
                               (test_cert and test_cert.lower().replace('/', '_').replace('-', '_') in fname_clean):
                                matching_pdfs.append(fname)
                    
                    # If we found matching PDFs, use the first one for this combination
                    if matching_pdfs:
                        combination_pdfs[combination_key] = matching_pdfs[0]
                    else:
                        # Fallback: look for any PDF that might correspond to this page
                        for fname in os.listdir(vendor_dir):
                            if fname.lower().endswith('.pdf') and str(item.page_number) in fname:
                                combination_pdfs[combination_key] = fname
                                break
            
            # Now add the unique combination PDFs to the ZIP
            pdf_count = 0
            for combination_key, pdf_filename in combination_pdfs.items():
                if pdf_filename not in added_files:
                    vendor_folder = None
                    # Find the vendor folder for this PDF
                    for item in extracted_data:
                        vendor_folder_name = vendor_folder_map.get(item.vendor.name)
                        if vendor_folder_name:
                            vendor_dir = os.path.join(extracted_dir, vendor_folder_name)
                            pdf_path = os.path.join(vendor_dir, pdf_filename)
                            if os.path.exists(pdf_path):
                                try:
                                    zip_file.write(pdf_path, arcname=f"extracted_pdfs/{pdf_filename}")
                                    added_files.add(pdf_filename)
                                    pdf_count += 1
                                    logger.info(f"Added unique combination PDF: {pdf_filename}")
                                    break
                                except Exception as e:
                                    error_msg = f"Error adding extracted PDF {pdf_filename}: {str(e)}"
                                    stats['errors'].append(error_msg)
                                    logger.error(error_msg)
                            break
            
            stats['pdf_count'] = pdf_count
            logger.info(f"Added {pdf_count} unique combination PDFs to package (deduplicated from potential duplicates)")
            
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
        
        # Verify buffer has content
        buffer_size = len(buffer.getvalue())
        if buffer_size == 0:
            logger.error(f"ZIP buffer is empty for PDF {pdf_id}")
            return False, "Generated package is empty. Please try again."
        
        # Log success
        logger.info(f"ZIP package created successfully for PDF {pdf_id} with {stats['pdf_count']} PDFs and Excel: {stats['excel_included']}, buffer size: {buffer_size} bytes")
        
        return True, (buffer, zip_filename, stats)
        
    except Exception as e:
        logger.exception(f"Error creating single file package: {str(e)}")
        return False, f"Error creating package: {str(e)}. Please contact support."


def download_single_file_package(request, pdf_id):
    """
    Downloads a ZIP package containing extracted PDFs and Excel data for a specific uploaded PDF.
    """
    try:
        # Convert pdf_id to integer if it's a string
        try:
            pdf_id = int(pdf_id)
        except (ValueError, TypeError):
            logger.error(f"Invalid PDF ID provided: {pdf_id}")
            messages.error(request, f"Invalid PDF ID: {pdf_id}")
            return redirect('dashboard')
            
        logger.info(f"Starting download request for PDF ID: {pdf_id}")
        success, result = create_single_file_package(pdf_id)
        
        if not success:
            # Show error message and redirect
            logger.error(f"Package creation failed for PDF {pdf_id}: {result}")
            messages.error(request, result)
            return redirect('dashboard')
        
        # Unpack the result
        buffer, zip_filename, stats = result
        
        # Ensure buffer is at the beginning for FileResponse
        buffer.seek(0)
        buffer_size = len(buffer.getvalue())
        
        logger.info(f"Creating FileResponse for {zip_filename}, size: {buffer_size} bytes")
        
        # Create response - use same pattern as working downloads.py
        response = FileResponse(buffer, as_attachment=True, filename=zip_filename)
        
        # Set content type explicitly (like other working downloads)
        response['Content-Type'] = 'application/zip'
        
        # Set content disposition with proper filename (like other working downloads)
        response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
        
        logger.info(f"FileResponse created successfully for PDF {pdf_id}")
        return response
        
    except Exception as e:
        logger.exception(f"Error creating single file package response: {str(e)}")
        messages.error(request, f"Error creating package: {str(e)}")
        return redirect('dashboard')


def download_individual_pdf(request, pdf_id):
    """
    Downloads a single PDF file with combination-based filename.
    
    Args:
        pdf_id: The ID of the UploadedPDF record
        
    Returns:
        FileResponse with the individual PDF file
    """
    try:
        # Convert pdf_id to integer if it's a string
        try:
            pdf_id = int(pdf_id)
        except (ValueError, TypeError):
            logger.error(f"Invalid PDF ID provided: {pdf_id}")
            messages.error(request, f"Invalid PDF ID: {pdf_id}")
            return redirect('dashboard')
            
        logger.info(f"Starting individual PDF download for PDF ID: {pdf_id}")
        
        # Get the uploaded PDF record
        pdf = get_object_or_404(UploadedPDF, id=pdf_id)
        
        # Get extracted data for this PDF to build the combination filename
        extracted_data = ExtractedData.objects.filter(pdf=pdf)
        
        if not extracted_data.exists():
            logger.error(f"No extracted data found for PDF ID: {pdf_id}")
            messages.error(request, "No extracted data found for this PDF")
            return redirect('dashboard')
        
        # Build combination from extracted data
        plate_no = heat_no = test_cert = ''
        
        for item in extracted_data:
            if item.field_key == 'PLATE_NO':
                plate_no = item.field_value
            elif item.field_key == 'HEAT_NO':
                heat_no = item.field_value
            elif item.field_key == 'TEST_CERT_NO':
                test_cert = item.field_value
        
        # Create combination filename
        if plate_no or heat_no or test_cert:
            # Clean the values for filename use
            clean_plate = str(plate_no).replace('/', '-').replace(' ', '_') if plate_no else 'Unknown'
            clean_heat = str(heat_no).replace('/', '-').replace(' ', '_') if heat_no else 'Unknown'
            clean_cert = str(test_cert).replace('/', '-').replace(' ', '_') if test_cert else 'Unknown'
            
            filename = f"{clean_heat}_{clean_plate}_{clean_cert}.pdf"
        else:
            # Fallback to original filename
            filename = f"{os.path.splitext(pdf.file.name)[0]}_certificate.pdf"
        
        # Find the extracted PDF file
        # First, determine the vendor folder mapping
        vendor_folder_map = {
            'CITIC Pacific Special Steel': 'citic_steel',
            'CITIC Steel': 'citic_steel',
            'Tata Steel': 'tata_steel',
            'JSW Steel': 'jsw_steel',
            # Add more mappings as needed
        }
        
        extracted_dir = os.path.join(settings.MEDIA_ROOT, 'extracted')
        vendor_folder = vendor_folder_map.get(pdf.vendor.name, pdf.vendor.name.lower().replace(' ', '_'))
        vendor_dir = os.path.join(extracted_dir, vendor_folder)
        
        if not os.path.exists(vendor_dir):
            logger.error(f"Vendor directory not found: {vendor_dir}")
            messages.error(request, "Extracted PDF not found")
            return redirect('dashboard')
        
        # Find the PDF file that matches this combination
        pdf_file_path = None
        
        # Look for PDF files in the vendor directory
        for file_name in os.listdir(vendor_dir):
            if file_name.lower().endswith('.pdf'):
                # Check if the filename contains parts of our combination
                file_name_clean = file_name.lower().replace('-', '_').replace(' ', '_')
                
                if ((plate_no and str(plate_no).lower().replace('/', '_').replace('-', '_') in file_name_clean) or
                    (heat_no and str(heat_no).lower().replace('/', '_').replace('-', '_') in file_name_clean) or
                    (test_cert and str(test_cert).lower().replace('/', '_').replace('-', '_') in file_name_clean)):
                    pdf_file_path = os.path.join(vendor_dir, file_name)
                    break
        
        if not pdf_file_path or not os.path.exists(pdf_file_path):
            logger.error(f"PDF file not found for combination: {filename}")
            messages.error(request, "PDF file not found")
            return redirect('dashboard')
        
        logger.info(f"Serving PDF file: {pdf_file_path} as {filename}")
        
        # Serve the PDF file
        response = FileResponse(
            open(pdf_file_path, 'rb'),
            as_attachment=True,
            filename=filename
        )
        
        response['Content-Type'] = 'application/pdf'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Exception as e:
        logger.exception(f"Error downloading individual PDF: {str(e)}")
        messages.error(request, f"Error downloading PDF: {str(e)}")
        return redirect('dashboard')
