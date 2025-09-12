# Fix Django version
Write-Host "Fixing Django version..." -ForegroundColor Green

# Downgrade Django back to the original version
Write-Host "Downgrading Django to 5.0.7..." -ForegroundColor Yellow
docker-compose exec web pip install django==5.0.7

# Try to clear cache (if the command exists)
Write-Host "Attempting to clear Django cache..." -ForegroundColor Yellow
docker-compose exec web python manage.py clearcache
if ($LASTEXITCODE -ne 0) {
    Write-Host "No clearcache command available, continuing..." -ForegroundColor Yellow
}

# Restart the web service
Write-Host "Restarting web service..." -ForegroundColor Yellow
docker-compose restart web

Write-Host "Done! Please check if the issue is resolved." -ForegroundColor Green
