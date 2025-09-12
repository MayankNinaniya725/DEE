# Fix Jazzmin template issue
Write-Host "Fixing Jazzmin template issue..." -ForegroundColor Green

# First, let's check if the container is running
docker ps | Select-String "extractor_project_web"

if ($LASTEXITCODE -ne 0) {
    Write-Host "Container is not running. Starting it..."
    docker-compose up -d
}

# Run collectstatic command to ensure static files are collected
Write-Host "Running collectstatic command..." -ForegroundColor Yellow
docker-compose exec web python manage.py collectstatic --noinput

# Check if Jazzmin is installed correctly
Write-Host "Checking Jazzmin installation..." -ForegroundColor Yellow
docker-compose exec web pip install django-jazzmin==2.6.0 --force-reinstall

# Verify Jazzmin template location
Write-Host "Checking template locations..." -ForegroundColor Yellow
docker-compose exec web find /usr/local/lib/python3.11/site-packages -name "jazzmin" -type d

# Restart the web service
Write-Host "Restarting web service..." -ForegroundColor Yellow
docker-compose restart web

Write-Host "Done! Please check if the issue is resolved." -ForegroundColor Green
