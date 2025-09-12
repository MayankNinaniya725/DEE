#!/usr/bin/env python
"""
Test vendor config loading with missing config
"""
import os
import json
import sys
import django
import shutil
from pathlib import Path

# Setup Django
sys.path.append('/code')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

from django.conf import settings
from extractor.models import Vendor
from extractor.utils.config_loader import find_vendor_config

print("===== TESTING VENDOR CONFIG FALLBACK =====")

# Get a vendor
vendor = Vendor.objects.first()
print(f"Testing with vendor: {vendor.name}")
print(f"Config file in DB: {vendor.config_file.name}")

# Get the original config
original_config_path = os.path.join(settings.MEDIA_ROOT, vendor.config_file.name)
if os.path.exists(original_config_path):
    # Create a backup
    backup_path = original_config_path + ".bak"
    print(f"Backing up original config to: {backup_path}")
    shutil.copy2(original_config_path, backup_path)
    
    # Remove the original
    print(f"Temporarily removing config: {original_config_path}")
    os.remove(original_config_path)
    
    # Try to find the config now
    print("Testing config loading with missing file...")
    config, path = find_vendor_config(vendor, settings)
    
    if config:
        print(f"✅ Fallback config found at: {path}")
        print(f"  Vendor name in config: {config.get('vendor_name', 'Not specified')}")
        print(f"  Key fields: {', '.join(config.get('key_fields', []))}")
    else:
        print(f"❌ Fallback failed, no config found for {vendor.name}")
    
    # Restore the original
    print(f"Restoring original config from: {backup_path}")
    shutil.copy2(backup_path, original_config_path)
    os.remove(backup_path)
else:
    print(f"Original config not found at: {original_config_path}")
    print("Testing with current setup...")
    config, path = find_vendor_config(vendor, settings)
    
    if config:
        print(f"✅ Config found at: {path}")
        print(f"  Vendor name in config: {config.get('vendor_name', 'Not specified')}")
        print(f"  Key fields: {', '.join(config.get('key_fields', []))}")
    else:
        print(f"❌ No config found for {vendor.name}")

print("\nFallback test complete.")
