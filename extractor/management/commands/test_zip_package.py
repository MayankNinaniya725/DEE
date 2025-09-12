import os
import sys
from django.core.management.base import BaseCommand
from django.conf import settings
import zipfile
from extractor.utils.zip_utils import create_download_package

class Command(BaseCommand):
    help = 'Tests ZIP file creation outside of HTTP context'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting ZIP package test..."))
        
        # First check file paths
        media_root = settings.MEDIA_ROOT
        excel_file = os.path.join(media_root, "master_log.xlsx")
        pdf_dir = os.path.join(media_root, "extracted")
        
        self.stdout.write(f"Media root: {media_root}")
        self.stdout.write(f"Excel path: {excel_file}")
        self.stdout.write(f"PDF dir: {pdf_dir}")
        
        # Check Excel
        if os.path.exists(excel_file):
            self.stdout.write(self.style.SUCCESS(f"Excel file exists: {os.path.getsize(excel_file)} bytes"))
        else:
            self.stdout.write(self.style.ERROR(f"Excel file missing"))
            
            # Check alternative Excel file paths
            possible_excel_paths = [
                os.path.join(media_root, "logs", "master_log.xlsx"),
                os.path.join(settings.BASE_DIR, "logs", "master_log.xlsx"),
                os.path.join(media_root, "master.xlsx"),
                os.path.join(media_root, "all_extracted_data.xlsx")
            ]
            
            for path in possible_excel_paths:
                if os.path.exists(path):
                    self.stdout.write(self.style.SUCCESS(f"Alternative Excel file found at: {path} ({os.path.getsize(path)} bytes)"))
        
        # Check PDFs directory
        if os.path.exists(pdf_dir):
            if os.path.isdir(pdf_dir):
                # Count PDF files using walk to include subdirectories
                pdf_count = 0
                for root, dirs, files in os.walk(pdf_dir):
                    for file in files:
                        if file.lower().endswith('.pdf'):
                            pdf_count += 1
                            
                self.stdout.write(self.style.SUCCESS(f"PDF dir exists with {pdf_count} PDF files"))
                
                # List a few PDFs as examples
                pdf_examples = []
                count = 0
                for root, dirs, files in os.walk(pdf_dir):
                    for file in files:
                        if file.lower().endswith('.pdf'):
                            pdf_path = os.path.join(root, file)
                            rel_path = os.path.relpath(pdf_path, media_root)
                            pdf_examples.append(f"  - {rel_path}: {os.path.getsize(pdf_path)} bytes")
                            count += 1
                            if count >= 5:
                                break
                    if count >= 5:
                        break
                
                for example in pdf_examples:
                    self.stdout.write(example)
            else:
                self.stdout.write(self.style.ERROR(f"PDF path exists but is not a directory"))
        else:
            self.stdout.write(self.style.ERROR(f"PDF directory missing"))
            
            # Check alternative PDF directories
            possible_pdf_dirs = [
                os.path.join(media_root, "uploads"),
                os.path.join(media_root, "pdfs"),
                os.path.join(media_root, "uploads", "pdfs")
            ]
            
            for path in possible_pdf_dirs:
                if os.path.exists(path) and os.path.isdir(path):
                    pdf_count = sum(1 for f in os.listdir(path) if f.lower().endswith('.pdf'))
                    self.stdout.write(self.style.SUCCESS(f"Alternative PDF directory found at: {path} with {pdf_count} PDF files"))
        
        # Try creating a test ZIP using our utility
        self.stdout.write("\nTesting ZIP package creation...")
        success, result = create_download_package()
        
        if success:
            buffer, zip_filename, stats = result
            buffer.seek(0)
            
            # Get buffer size
            buffer_size = buffer.getbuffer().nbytes
            
            self.stdout.write(self.style.SUCCESS(f"ZIP package created successfully!"))
            self.stdout.write(f"Filename: {zip_filename}")
            self.stdout.write(f"Size: {buffer_size} bytes ({buffer_size / 1024 / 1024:.2f} MB)")
            self.stdout.write(f"Excel included: {stats['excel_included']}")
            self.stdout.write(f"PDF count: {stats['pdf_count']}")
            
            if stats['errors']:
                self.stdout.write(self.style.WARNING(f"There were {len(stats['errors'])} errors during creation:"))
                for i, error in enumerate(stats['errors'][:5], 1):  # Show first 5 errors
                    self.stdout.write(f"  {i}. {error}")
                if len(stats['errors']) > 5:
                    self.stdout.write(f"  ... and {len(stats['errors']) - 5} more errors")
                    
            # Validate the ZIP contents
            self.stdout.write("\nValidating ZIP contents...")
            try:
                with zipfile.ZipFile(buffer) as zip_file:
                    file_list = zip_file.namelist()
                    self.stdout.write(f"ZIP contains {len(file_list)} files")
                    for i, file in enumerate(sorted(file_list)[:10], 1):  # Show first 10 files
                        info = zip_file.getinfo(file)
                        self.stdout.write(f"  {i}. {file} ({info.file_size} bytes)")
                    if len(file_list) > 10:
                        self.stdout.write(f"  ... and {len(file_list) - 10} more files")
                        
                    test_extract = zip_file.testzip()
                    if test_extract is None:
                        self.stdout.write(self.style.SUCCESS("ZIP integrity check passed!"))
                    else:
                        self.stdout.write(self.style.ERROR(f"ZIP integrity check failed. First bad file: {test_extract}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error validating ZIP: {str(e)}"))
                
            # Final assessment
            if stats['excel_included'] and stats['pdf_count'] > 0 and buffer_size > 0:
                self.stdout.write(self.style.SUCCESS("\n✅ PACKAGE IS READY FOR DOWNLOAD"))
            else:
                self.stdout.write(self.style.WARNING("\n⚠️ PACKAGE MAY BE INCOMPLETE"))
                if not stats['excel_included']:
                    self.stdout.write("   - Excel file is missing")
                if stats['pdf_count'] == 0:
                    self.stdout.write("   - No PDF files were included")
                if buffer_size == 0:
                    self.stdout.write("   - ZIP file is empty")
                    
        else:
            self.stdout.write(self.style.ERROR(f"Failed to create ZIP package: {result}"))
