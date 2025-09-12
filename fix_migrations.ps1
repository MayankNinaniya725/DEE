# Script to fix database migrations and restart Docker containers
$ErrorActionPreference = "Stop"

Write-Host "=== Database Migration Fix Script ===" -ForegroundColor Green

# Check Docker status
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

# Find web container
Write-Host "2. Finding web container..." -ForegroundColor Cyan
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
}
Write-Host "✅ Found web container: $webContainer" -ForegroundColor Green

# Detect if status field exists
Write-Host "3. Checking models.py and migration status..." -ForegroundColor Cyan
$fieldExists = docker exec $webContainer python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
import django
django.setup()
from extractor.models import UploadedPDF
has_status = 'status' in [f.name for f in UploadedPDF._meta.get_fields()]
has_status_code = False
with open('extractor/models.py', 'r') as f:
    has_status_code = 'status =' in f.read()
print(f'Status field in DB: {has_status}')
print(f'Status field in code: {has_status_code}')
"

Write-Host $fieldExists

# Run makemigrations and migrate
Write-Host "4. Running migrations..." -ForegroundColor Cyan
docker exec $webContainer python manage.py makemigrations
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to run makemigrations" -ForegroundColor Red
    exit 1
}

docker exec $webContainer python manage.py migrate
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to run migrate" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Migrations applied successfully" -ForegroundColor Green

# Restart Docker containers
Write-Host "5. Restarting containers..." -ForegroundColor Cyan
docker-compose restart
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to restart containers" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Containers restarted successfully" -ForegroundColor Green

# Verify extraction system is working
Write-Host "6. Verifying extraction system..." -ForegroundColor Cyan
Write-Host "Waiting for services to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Run the extraction test
docker exec $webContainer python basic_db_test.py
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Extraction system is working properly!" -ForegroundColor Green
} else {
    Write-Host "❌ Extraction system may still have issues." -ForegroundColor Red
}

Write-Host "=== Migration Fix Complete ===" -ForegroundColor Green
