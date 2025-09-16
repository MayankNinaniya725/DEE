#!/bin/sh

# Wait for database to be ready
echo "Waiting for database..."
sleep 5

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate

# Create superuser if it doesn't exist
echo "Creating superuser if not exists..."
python manage.py shell -c "
from django.contrib.auth import get_user_model;
User = get_user_model();
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin');
"

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Create required directories
echo "Creating required directories..."
mkdir -p media/uploads media/extracted media/vendor_configs staticfiles

# Start server
echo "Starting server..."
python manage.py runserver 0.0.0.0:8000


