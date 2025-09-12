"""Download-related views for the extractor app"""
import os
import io
import logging
import tempfile
import shutil
import zipfile
from datetime import datetime

from django.shortcuts import redirect
from django.contrib import messages
from django.conf import settings
from django.http import FileResponse, HttpResponse
from django.db.models import Q

import pandas as pd

from ..models import ExtractedData, UploadedPDF

# Configure logging
logger = logging.getLogger('extractor')

def download_all_pdfs_package(request):
    """
    Creates a comprehensive ZIP archive containing:
    - All processed PDF files
    - A single Excel file with all dashboard data
    
    This is different from download_pdfs_with_excel in that it creates a flatter structure
    and focuses on providing all PDFs with a single Excel summary file.
    
    Includes robust error handling to ensure ZIP creation always succeeds even if some
    files are missing or inaccessible.
    """
    # Debug logging - capture start time
    start_time = datetime.now()
    logger.info(f"Starting download_all_pdfs_package at {start_time}")
    
    # Track skipped files for logging
    skipped_files = []
    pdf_success_count = 0
    
    try:
        # Step 1: Create temporary directory for working with files
        logger.info("Creating temporary directory")
        with tempfile.TemporaryDirectory() as temp_dir:
            # Step 2: Query database for PDFs with extracted data
            logger.info("Querying database for PDFs with extracted data")
            pdfs_with_data = UploadedPDF.objects.filter(
                extracted_data__isnull=False,
                status='COMPLETED'
            ).distinct()
            
            pdf_count = pdfs_with_data.count()
            logger.info(f"Found {pdf_count} PDFs with extracted data")
            
            if not pdfs_with_data.exists():
                logger.warning("No PDFs with extracted data found")
                messages.warning(request, "No processed PDFs found with extracted data")
                return redirect("dashboard")

            # Step 3: Create directory structure
            logger.info("Creating directory structure")
            package_dir = os.path.join(temp_dir, 'pdf_package')
            pdfs_dir = os.path.join(package_dir, 'pdfs')
            
            try:
                os.makedirs(pdfs_dir, exist_ok=True)
                logger.info(f"Created directories: {package_dir}, {pdfs_dir}")
            except Exception as e:
                logger.error(f"Failed to create directories: {str(e)}", exc_info=True)
                messages.error(request, "Failed to create temporary directory for ZIP package")
                return redirect("dashboard")
            
            # Step 4: Prepare data for Excel
            logger.info("Preparing data for Excel")
            all_extraction_data = []
            field_count = 0
            successful_pdfs = []
            
            # Create a minimal test file to verify file system is working
            test_file_path = os.path.join(package_dir, 'test.txt')
            try:
                with open(test_file_path, 'w') as f:
                    f.write('This is a test file to verify filesystem access.')
                logger.info(f"Created test file: {test_file_path}")
            except Exception as e:
                logger.error(f"Failed to create test file: {str(e)}", exc_info=True)
                # Continue despite test file failure
            
            # Step 5: Process each PDF with proper error handling
            logger.info("Processing PDFs")
            for idx, pdf in enumerate(pdfs_with_data):
                try:
                    pdf_index = idx + 1
                    logger.info(f"Processing PDF {pdf_index}/{pdf_count}: ID={pdf.id}")
                    
                    # 5a: Get PDF filename and paths
                    if not hasattr(pdf, 'file') or not pdf.file:
                        logger.warning(f"PDF record {pdf.id} has no file attribute or it's None")
                        skipped_files.append(f"PDF ID {pdf.id}: No file attribute")
                        continue
                    
                    pdf_filename = os.path.basename(pdf.file.name)
                    logger.info(f"PDF filename: {pdf_filename}")
                    pdf_dst_path = os.path.join(pdfs_dir, f"{pdf_index:03d}_{pdf_filename}")
                    
                    # 5b: Validate source PDF file
                    try:
                        pdf_src_path = pdf.file.path
                        logger.info(f"PDF source path: {pdf_src_path}")
                        
                        if not os.path.exists(pdf_src_path):
                            logger.warning(f"PDF file not found: {pdf_src_path}")
                            skipped_files.append(pdf_src_path)
                            continue
                            
                        if not os.access(pdf_src_path, os.R_OK):
                            logger.warning(f"PDF file not readable: {pdf_src_path}")
                            skipped_files.append(f"{pdf_src_path} (not readable)")
                            continue
                        
                        # Get file size for debugging
                        file_size = os.path.getsize(pdf_src_path)
                        logger.info(f"PDF file size: {file_size} bytes")
                    except Exception as e:
                        logger.error(f"Error validating PDF file: {str(e)}", exc_info=True)
                        skipped_files.append(f"PDF ID {pdf.id}: {str(e)}")
                        continue
                    
                    # 5c: Copy PDF file with buffered I/O
                    try:
                        logger.info(f"Copying PDF from {pdf_src_path} to {pdf_dst_path}")
                        # Use buffered I/O with smaller chunks to avoid memory issues
                        with open(pdf_src_path, 'rb') as src_file:
                            with open(pdf_dst_path, 'wb') as dst_file:
                                # Copy in 1MB chunks
                                chunk_size = 1024 * 1024  # 1MB
                                while True:
                                    chunk = src_file.read(chunk_size)
                                    if not chunk:
                                        break
                                    dst_file.write(chunk)
                        
                        # Verify the copy was successful
                        if os.path.exists(pdf_dst_path):
                            dest_size = os.path.getsize(pdf_dst_path)
                            logger.info(f"PDF copy successful: {dest_size} bytes")
                            pdf_success_count += 1
                            successful_pdfs.append(pdf)
                        else:
                            logger.error(f"PDF copy failed: Destination file does not exist")
                            skipped_files.append(f"{pdf_src_path} (copy failed: destination missing)")
                            continue
                        
                    except Exception as e:
                        logger.error(f"Failed to copy PDF {pdf_src_path} to {pdf_dst_path}: {str(e)}", exc_info=True)
                        skipped_files.append(f"{pdf_src_path} (copy failed: {str(e)})")
                        continue
                    
                    # 5d: Get extracted data for this PDF
                    try:
                        logger.info(f"Getting extracted data for PDF ID {pdf.id}")
                        extracted_data = ExtractedData.objects.filter(pdf=pdf).order_by('field_key')
                        data_count = extracted_data.count()
                        logger.info(f"Found {data_count} extracted fields")
                        field_count += data_count
                        
                        # Get key fields for this PDF
                        for item in extracted_data:
                            all_extraction_data.append({
                                'Sr No': len(all_extraction_data) + 1,
                                'PDF File': pdf_filename,
                                'Vendor': pdf.vendor.name,
                                'Field Key': item.field_key,
                                'Field Value': item.field_value,
                                'Page Number': item.page_number,
                                'Extracted At': item.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                                'PDF Path': f"pdfs/{pdf_index:03d}_{pdf_filename}"
                            })
                    except Exception as e:
                        logger.error(f"Error processing extracted data for PDF {pdf_filename}: {str(e)}", exc_info=True)
                        # Continue with next PDF since we already copied this one
                
                except Exception as e:
                    logger.error(f"Error processing PDF ID {pdf.id}: {str(e)}", exc_info=True)
                    continue
            
            # Step 6: Check if we have any successful PDFs
            logger.info(f"PDF processing complete. Success: {pdf_success_count}/{pdf_count}")
            if pdf_success_count == 0:
                logger.error("No PDFs were successfully processed for the package")
                messages.error(request, "Could not include any PDF files in the package. Please check file permissions.")
                return redirect("dashboard")
            
            # Create a minimal text file with extracted data as a fallback
            fallback_text_path = os.path.join(package_dir, 'extracted_data.txt')
            try:
                with open(fallback_text_path, 'w') as f:
                    f.write(f"Extracted data from {pdf_count} PDFs\n\n")
                    for item in all_extraction_data:
                        f.write(f"PDF: {item['PDF File']}, Field: {item['Field Key']}, Value: {item['Field Value']}\n")
                logger.info(f"Created fallback text file: {fallback_text_path}")
            except Exception as e:
                logger.error(f"Failed to create fallback text file: {str(e)}", exc_info=True)
            
            # Step 7: Create comprehensive Excel file
            logger.info("Creating Excel file")
            excel_path = os.path.join(package_dir, 'all_extracted_data.xlsx')
            excel_created = False
            
            try:
                # First, try to create a simple test Excel file to check permissions
                test_excel_path = os.path.join(package_dir, 'test.xlsx')
                logger.info(f"Creating test Excel file: {test_excel_path}")
                
                # Use a simpler dataframe for testing
                test_df = pd.DataFrame({'Test': ['This is a test']})
                
                # Try multiple engines in case one fails
                excel_engines = ['openpyxl', 'xlsxwriter']
                excel_engine_success = False
                
                for engine in excel_engines:
                    try:
                        logger.info(f"Trying Excel engine: {engine}")
                        test_df.to_excel(test_excel_path, engine=engine, index=False)
                        if os.path.exists(test_excel_path) and os.path.getsize(test_excel_path) > 0:
                            logger.info(f"Test Excel created successfully with {engine} engine")
                            excel_engine_success = True
                            excel_engine = engine
                            break
                    except Exception as e:
                        logger.warning(f"Excel engine {engine} failed: {str(e)}")
                        continue
                
                if not excel_engine_success:
                    logger.error("All Excel engines failed, trying CSV as fallback")
                    csv_path = os.path.join(package_dir, 'test.csv')
                    test_df.to_csv(csv_path, index=False)
                    logger.info("Created CSV fallback file")
                    
                    # Create a plain text version of the Excel data
                    txt_path = os.path.join(package_dir, 'extracted_data_full.txt')
                    with open(txt_path, 'w') as f:
                        f.write("# Extracted Data\n\n")
                        for idx, row in test_df.iterrows():
                            f.write(f"{row.to_string()}\n")
                    logger.info("Created TXT fallback file")
                    
                    raise Exception("Excel creation not possible with any engine")
                
                # Now create the real Excel file with the successful engine
                logger.info(f"Creating main Excel file using {excel_engine} engine: {excel_path}")
                with pd.ExcelWriter(excel_path, engine=excel_engine) as writer:
                    # Create Summary sheet
                    summary_data = {
                        'Information': [
                            'Total PDFs', 'Successfully Included PDFs', 'Total Extracted Fields', 
                            'Generation Date', 'Package Type', 'Skipped Files'
                        ],
                        'Value': [
                            pdf_count, pdf_success_count, field_count,
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'Complete PDF Package',
                            len(skipped_files)
                        ]
                    }
                    pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
                    
                    # Create All extracted data sheet
                    if all_extraction_data:
                        df = pd.DataFrame(all_extraction_data)
                        df.to_excel(writer, sheet_name='All Extracted Data', index=False)
                    else:
                        # Create empty sheet with headers if no data
                        empty_df = pd.DataFrame(columns=[
                            'Sr No', 'PDF File', 'Vendor', 'Field Key', 'Field Value', 
                            'Page Number', 'Extracted At', 'PDF Path'
                        ])
                        empty_df.to_excel(writer, sheet_name='All Extracted Data', index=False)
                    
                    # Create Key fields sheet
                    key_fields_data = []
                    for idx, pdf in enumerate(successful_pdfs):
                        try:
                            pdf_filename = os.path.basename(pdf.file.name)
                            extracted = ExtractedData.objects.filter(pdf=pdf)
                            
                            # Get values for key fields
                            field_values = {}
                            for field in ['PLATE_NO', 'HEAT_NO', 'TEST_CERT_NO']:
                                matches = [item for item in extracted if item.field_key == field]
                                field_values[field] = matches[0].field_value if matches else ''
                            
                            pdf_index = idx + 1
                            key_fields_data.append({
                                'PDF File': pdf_filename,
                                'Vendor': pdf.vendor.name,
                                'PLATE_NO': field_values.get('PLATE_NO', ''),
                                'HEAT_NO': field_values.get('HEAT_NO', ''),
                                'TEST_CERT_NO': field_values.get('TEST_CERT_NO', ''),
                                'Fields Found': extracted.count(),
                                'Uploaded At': pdf.uploaded_at.strftime("%Y-%m-%d %H:%M:%S"),
                                'PDF Path': f"pdfs/{pdf_index:03d}_{pdf_filename}"
                            })
                        except Exception as e:
                            logger.error(f"Error adding key fields data for PDF {pdf.id}: {str(e)}", exc_info=True)
                            continue
                    
                    if key_fields_data:
                        pd.DataFrame(key_fields_data).to_excel(writer, sheet_name='Key Fields Summary', index=False)
                    else:
                        empty_df = pd.DataFrame(columns=[
                            'PDF File', 'Vendor', 'PLATE_NO', 'HEAT_NO', 'TEST_CERT_NO',
                            'Fields Found', 'Uploaded At', 'PDF Path'
                        ])
                        empty_df.to_excel(writer, sheet_name='Key Fields Summary', index=False)
                    
                    # Create Skipped files sheet
                    if skipped_files:
                        skipped_df = pd.DataFrame({'Skipped Files': skipped_files})
                        skipped_df.to_excel(writer, sheet_name='Skipped Files', index=False)
                
                # Verify Excel file was created
                if os.path.exists(excel_path) and os.path.getsize(excel_path) > 0:
                    excel_size = os.path.getsize(excel_path)
                    logger.info(f"Excel file created successfully: {excel_size} bytes")
                    excel_created = True
                else:
                    logger.error("Excel file creation failed: file does not exist or is empty")
                    
                    # Create a CSV backup if Excel failed
                    csv_path = os.path.join(package_dir, 'all_extracted_data.csv')
                    
                    if all_extraction_data:
                        pd.DataFrame(all_extraction_data).to_csv(csv_path, index=False)
                        logger.info("Created CSV fallback file for extracted data")
                
            except Exception as e:
                logger.error(f"Error creating Excel file: {str(e)}", exc_info=True)
                
                # Try to create CSV versions as fallback
                try:
                    logger.info("Creating CSV fallbacks after Excel failure")
                    
                    # Summary CSV
                    summary_csv = os.path.join(package_dir, 'summary.csv')
                    summary_data = {
                        'Information': [
                            'Total PDFs', 'Successfully Included PDFs', 'Total Extracted Fields', 
                            'Generation Date', 'Package Type', 'Skipped Files'
                        ],
                        'Value': [
                            pdf_count, pdf_success_count, field_count,
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'Complete PDF Package',
                            len(skipped_files)
                        ]
                    }
                    pd.DataFrame(summary_data).to_csv(summary_csv, index=False)
                    
                    # All data CSV
                    if all_extraction_data:
                        all_data_csv = os.path.join(package_dir, 'all_extracted_data.csv')
                        pd.DataFrame(all_extraction_data).to_csv(all_data_csv, index=False)
                    
                    logger.info("Created CSV fallback files successfully")
                except Exception as e2:
                    logger.error(f"Error creating CSV fallbacks: {str(e2)}", exc_info=True)
                
                # Create a text fallback file with basic data
                try:
                    logger.info("Creating text fallback file with extracted data")
                    txt_path = os.path.join(package_dir, 'extracted_data_full.txt')
                    with open(txt_path, 'w') as f:
                        f.write(f"# Extracted Data Report\n")
                        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write(f"Total PDFs: {pdf_count}\n")
                        f.write(f"Successful PDFs: {pdf_success_count}\n")
                        f.write(f"Total Fields: {field_count}\n\n")
                        
                        f.write("## Extracted Fields\n\n")
                        for item in all_extraction_data:
                            f.write(f"PDF: {item['PDF File']}\n")
                            f.write(f"Vendor: {item['Vendor']}\n")
                            f.write(f"Field: {item['Field Key']}\n")
                            f.write(f"Value: {item['Field Value']}\n")
                            f.write(f"Page: {item['Page Number']}\n")
                            f.write(f"Path: {item['PDF Path']}\n\n")
                    
                    logger.info("Created text fallback file successfully")
                except Exception as e3:
                    logger.error(f"Error creating text fallback: {str(e3)}", exc_info=True)
            
            # Step 8: Create README file with error info
            readme_content = f"""# PDF Extraction Package
## Summary
- Total PDFs attempted: {pdf_count}
- Successfully included PDFs: {pdf_success_count}
- Total Extracted Fields: {field_count}
- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Contents
This package contains:
1. All successfully processed PDF files in the 'pdfs' folder
2. Excel file with all extracted data: 'all_extracted_data.xlsx'

## Excel File Structure
The Excel file contains the following sheets:
- Summary: Overview of this package
- All Extracted Data: Complete dataset with all extracted fields
- Key Fields Summary: Summary of important fields like PLATE_NO, HEAT_NO, TEST_CERT_NO
- Skipped Files: List of files that could not be included (if any)

## PDF Files
The PDFs are numbered sequentially for easy reference. The original filenames are preserved
with a prefix (e.g., 001_filename.pdf, 002_filename.pdf).

## PDF to Excel Mapping
Each entry in the Excel file contains a 'PDF Path' column that shows the relative path 
to the corresponding PDF file in this package.

"""
            
            # Add skipped files information to README
            if skipped_files:
                readme_content += "\n## Skipped Files\nThe following files could not be included in the package:\n"
                for skipped in skipped_files:
                    readme_content += f"- {skipped}\n"
            
            # Write README with try/except
            readme_path = os.path.join(package_dir, 'README.txt')
            try:
                with open(readme_path, 'w') as f:
                    f.write(readme_content)
                logger.info("README created successfully")
            except Exception as e:
                logger.error(f"Error creating README file: {str(e)}", exc_info=True)
                # Continue even if README creation fails
            
            # Step 9: Create ZIP file
            logger.info("Creating ZIP file")
            zip_filename = f"complete_pdf_package_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            
            # Create a fallback minimal ZIP if everything else fails
            fallback_zip_buffer = io.BytesIO()
            with zipfile.ZipFile(fallback_zip_buffer, 'w', zipfile.ZIP_DEFLATED) as fallback_zipf:
                fallback_readme = "# Error creating full PDF package\n\nThere was an error creating the complete PDF package. Please contact support."
                fallback_zipf.writestr("README.txt", fallback_readme)
            fallback_zip_buffer.seek(0)
            
            # Try to create the real ZIP
            zip_buffer = io.BytesIO()
            zip_success = False
            
            try:
                logger.info("Opening ZIP file")
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    # First, add all files in the package directory
                    files_added = 0
                    for root, dirs, files in os.walk(package_dir):
                        for file in files:
                            try:
                                file_path = os.path.join(root, file)
                                
                                # Skip files that don't exist or aren't readable
                                if not os.path.exists(file_path):
                                    logger.warning(f"File does not exist when creating ZIP: {file_path}")
                                    continue
                                    
                                if not os.access(file_path, os.R_OK):
                                    logger.warning(f"File not readable when creating ZIP: {file_path}")
                                    continue
                                
                                arcname = os.path.relpath(file_path, package_dir)
                                zipf.write(file_path, arcname=arcname)
                                files_added += 1
                                logger.info(f"Added to ZIP: {arcname}")
                            except Exception as e:
                                logger.error(f"Error adding file {file} to ZIP: {str(e)}", exc_info=True)
                                continue
                    
                    logger.info(f"Added {files_added} files to ZIP")
                
                # Check if ZIP was created successfully
                zip_buffer.seek(0, os.SEEK_END)
                zip_size = zip_buffer.tell()
                zip_buffer.seek(0)
                
                if zip_size > 0:
                    logger.info(f"ZIP created successfully: {zip_size} bytes")
                    zip_success = True
                else:
                    logger.error("ZIP creation failed: zero bytes")
                
            except Exception as e:
                logger.error(f"Error creating ZIP file: {str(e)}", exc_info=True)
            
            # Step 10: Return ZIP as response
            if not zip_success:
                logger.warning("Using fallback ZIP due to creation failure")
                zip_buffer = fallback_zip_buffer
            
            # Reset buffer position and create response
            zip_buffer.seek(0)
            
            # Log summary of ZIP creation
            log_message = (
                f"Created ZIP package with {pdf_success_count}/{pdf_count} PDFs, "
                f"{field_count} fields, Excel file: {excel_created}, "
                f"Skipped files: {len(skipped_files)}"
            )
            logger.info(log_message)
            
            if len(skipped_files) > 0:
                warning_msg = f"ZIP package created with {pdf_success_count} PDFs. {len(skipped_files)} files were skipped."
                messages.warning(request, warning_msg)
            else:
                success_msg = f"ZIP package created successfully with {pdf_success_count} PDFs."
                messages.success(request, success_msg)
            
            # Use FileResponse since our test proved it works
            response = FileResponse(zip_buffer, as_attachment=True, filename=zip_filename)
            
            # Set content type explicitly
            response['Content-Type'] = 'application/zip'
            
            # Set content disposition with proper filename
            response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
            
            # Calculate total execution time
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            logger.info(f"download_all_pdfs_package completed in {execution_time} seconds")
            
            return response
            
    except Exception as e:
        logger.error(f"Error creating complete PDF package: {str(e)}", exc_info=True)
        messages.error(request, "Could not create the complete PDF package. See logs for details.")
        return redirect("dashboard")
