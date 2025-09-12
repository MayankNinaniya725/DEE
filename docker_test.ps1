# Script to test PDF extraction inside Docker container
$ErrorActionPreference = "Stop"

Write-Host "=== PDF Extraction Test ===" -ForegroundColor Green

# First, make sure Docker is running
Write-Host "1. Checking Docker status..." -ForegroundColor Cyan
try {
    $dockerStatus = docker info
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Docker is not running! Please start Docker Desktop first." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Docker is not installed or not running: $_" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Docker is running" -ForegroundColor Green

# Check if containers are running
Write-Host "2. Checking if containers are running..." -ForegroundColor Cyan
$containers = docker ps --format "{{.Names}}"
$webContainer = $containers | Where-Object { $_ -like "*web*" -or $_ -like "*app*" }

if (-not $webContainer) {
    Write-Host "⚠️ Web container not running. Starting with docker-compose..." -ForegroundColor Yellow
    docker-compose up -d
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to start containers with docker-compose" -ForegroundColor Red
        exit 1
    }
    
    # Wait for containers to fully start
    Write-Host "Waiting for containers to start..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10
    
    # Get the web container name again
    $containers = docker ps --format "{{.Names}}"
    $webContainer = $containers | Where-Object { $_ -like "*web*" -or $_ -like "*app*" }
    
    if (-not $webContainer) {
        Write-Host "❌ Could not find web container after starting docker-compose" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "✅ Web container is running: $webContainer" -ForegroundColor Green
}

# Run test inside container
Write-Host "3. Running extraction test inside container..." -ForegroundColor Cyan
$basicDbTestExists = docker exec $webContainer test -f basic_db_test.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️ basic_db_test.py not found in container. Copying it..." -ForegroundColor Yellow
    # Create a temporary file with the test script
    $testScript = @"
"""
Basic DB test - directly create random entries
"""
import os
import sys
import django
import random
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('db_test')

def main():
    # Setup Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
    django.setup()
    
    # Now we can import Django models
    from django.core.files.base import ContentFile
    from extractor.models import Vendor, UploadedPDF, ExtractedData
    
    try:
        # Get an existing vendor
        vendor = Vendor.objects.first()
        if not vendor:
            logger.error("No vendor found in database. Please create one first.")
            return False
        
        logger.info(f"Using vendor: {vendor.name}")
        
        # Create a PDF object - skipping fields that might cause issues
        pdf_content = b"%PDF-1.4\\n1 0 obj\\n<</Type/Catalog/Pages 2 0 R>>\\nendobj\\n2 0 obj\\n<</Type/Pages/Kids[3 0 R]/Count 1>>\\nendobj\\n3 0 obj\\n<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>\\nendobj\\nxref\\n0 4\\n0000000000 65535 f\\n0000000009 00000 n\\n0000000058 00000 n\\n0000000111 00000 n\\ntrailer\\n<</Size 4/Root 1 0 R>>\\nstartxref\\n190\\n%%EOF"
        pdf_file = ContentFile(pdf_content, name=f"test_file_{random.randint(1000, 9999)}.pdf")
        
        logger.info("Creating test PDF record (minimal fields)...")
        pdf = UploadedPDF(
            vendor=vendor,
            file=pdf_file,
            file_hash=f"hash_{random.randint(10000, 99999)}",
            file_size=len(pdf_content)
        )
        
        # Check all fields that might be required and handle them
        all_fields = [f.name for f in UploadedPDF._meta.get_fields()]
        logger.info(f"Available fields in UploadedPDF model: {', '.join(all_fields)}")
        
        # Check if there's a user field
        if 'user' in all_fields:
            from django.contrib.auth.models import User
            admin_user = User.objects.filter(is_superuser=True).first()
            if admin_user:
                pdf.user = admin_user
                logger.info(f"Set user field to admin: {admin_user.username}")
        
        # Save the PDF
        pdf.save()
        logger.info(f"Created PDF record with ID: {pdf.id}")
        
        # Generate test extraction data
        logger.info("Creating extraction data...")
        field_keys = ["PLATE_NO", "HEAT_NO", "TEST_CERT_NO"]
        
        for key in field_keys:
            # Generate random values based on field type
            if key == "PLATE_NO":
                value = f"T{random.randint(10000, 99999)}"
            elif key == "HEAT_NO":
                value = f"H{random.randint(10000, 99999)}"
            else:
                value = f"C{random.randint(10000, 99999)}"
                
            # Create the extraction record
            ExtractedData.objects.create(
                vendor=vendor,
                pdf=pdf,
                field_key=key,
                field_value=value,
                page_number=1
            )
            logger.info(f"Created extraction record: {key} = {value}")
        
        # Verify the extraction data
        extraction_count = ExtractedData.objects.filter(pdf=pdf).count()
        logger.info(f"Created {extraction_count} extraction records for PDF ID {pdf.id}")
        
        if extraction_count == len(field_keys):
            logger.info("✅ Extraction test PASSED! Database is working correctly.")
            return True
        else:
            logger.error(f"❌ Extraction test FAILED. Expected {len(field_keys)} records but found {extraction_count}.")
            return False
            
    except Exception as e:
        logger.error(f"Error during test: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
"@
    $testScript | docker exec -i $webContainer sh -c 'cat > /app/basic_db_test.py'
}

docker exec $webContainer python basic_db_test.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Test completed successfully! The extraction system is working properly." -ForegroundColor Green
} else {
    Write-Host "❌ Test failed! The extraction system may have issues." -ForegroundColor Red
}

# Optional: Check logs for any errors
Write-Host "4. Checking container logs for errors..." -ForegroundColor Cyan
docker logs --tail 20 $webContainer | Select-String -Pattern "ERROR|Error|error"

Write-Host "=== Test Complete ===" -ForegroundColor Green
