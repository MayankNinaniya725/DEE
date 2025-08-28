#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()


# py -m venv .venv
# .venv\Scripts\activate
# python manage.py runserver

# docker compose up -d for starting the services in detached mode
# docker compose down for stopping the services
# docker compose logs -f for viewing the logs
# docker compose up --build  for rebuilding the images and starting the services when debugging, so you can see real-time logs in the terminal. 
# docker compose up --build -d for rebuilding the images and starting the services in detached mode or for normal background running (production/dev).
# docker compose exec web python manage.py migrate for applying migrations
# docker compose exec web python manage.py createsuperuser for creating a superuser
# PS C:\Users\Mayank\desktop\dee\extractor_project> docker compose exec web python manage.py flush 

# docker compose exec web python manage.py shell for removing files for testing the files again and again
# from extractor.models import UploadedPDF, ExtractedData
# UploadedPDF.objects.all().delete()
# ExtractedData.objects.all().delete()

#  http://localhost:8000/admin
#  http://localhost:8000/upload/ for uploading PDFs