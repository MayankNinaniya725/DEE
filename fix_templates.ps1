# Make a backup of settings.py
Write-Host "Making a backup of settings.py..." -ForegroundColor Green
docker-compose exec web cp /code/extractor_project/settings.py /code/extractor_project/settings.py.bak

# Update the TEMPLATE_DIRS setting
Write-Host "Modifying template settings..." -ForegroundColor Yellow
docker-compose exec web bash -c "cat > /code/extractor_project/settings_update.py << 'EOL'
# Updated TEMPLATES setting
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'extractor' / 'templates',
            BASE_DIR / 'templates',
            '/usr/local/lib/python3.11/site-packages/jazzmin/templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]
EOL"

# Apply the template changes to settings.py
Write-Host "Updating settings.py..." -ForegroundColor Yellow
docker-compose exec web bash -c "sed -i '/TEMPLATES = \\[/,/]\\]/d' /code/extractor_project/settings.py && cat /code/extractor_project/settings_update.py >> /code/extractor_project/settings.py"

# Restart the web service
Write-Host "Restarting web service..." -ForegroundColor Yellow
docker-compose restart web

Write-Host "Done! Please check if the issue is resolved." -ForegroundColor Green
