# Start Docker containers
Write-Host "Starting Docker containers..." -ForegroundColor Green
docker compose up -d

# Wait for containers to be ready
Write-Host "Waiting for services to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Start ngrok tunnel
Write-Host "Starting ngrok tunnel..." -ForegroundColor Green
ngrok http 8000

# Note: To stop everything:
# 1. Press Ctrl+C to stop ngrok
# 2. Run 'docker compose down' to stop containers
