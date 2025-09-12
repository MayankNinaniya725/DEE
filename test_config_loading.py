#!/usr/bin/env python
"""
Test vendor config loading
"""
import os
import json
import sys
import django
from pathlib import Path

# Setup Django
sys.path.append('/code')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

from django.conf import settings
from extractor.models import Vendor
from extractor.utils.config_loader import find_vendor_config

print("===== TESTING VENDOR CONFIG LOADING =====")

# Get all vendors
vendors = Vendor.objects.all()
print(f"Found {len(vendors)} vendors in the database")

for vendor in vendors:
    print(f"\nTesting config loading for: {vendor.name}")
    print(f"Config file in DB: {vendor.config_file.name}")
    
    # Try to find the config using our new helper
    config, path = find_vendor_config(vendor, settings)
    
    if config:
        print(f"✅ Config found at: {path}")
        print(f"  Vendor name in config: {config.get('vendor_name', 'Not specified')}")
        print(f"  Key fields: {', '.join(config.get('key_fields', []))}")
    else:
        print(f"❌ Could not find config for {vendor.name}")

print("\nConfig loading test complete.")
