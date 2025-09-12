#!/usr/bin/env python
"""
Script to regenerate the master Excel file from the database
"""
import os
import sys
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

# Import after Django setup
from extractor.utils.update_excel import update_master_excel

if __name__ == "__main__":
    print("Regenerating master Excel file from database...")
    success = update_master_excel()
    
    if success:
        print("Excel file regenerated successfully!")
    else:
        print("Failed to regenerate Excel file. Check logs for details.")
    