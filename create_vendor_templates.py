#!/usr/bin/env python
"""
Create template vendor config JSON files
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

print("===== CREATING TEMPLATE VENDOR CONFIG FILES =====")

# Base template
base_template = {
  "key_fields": [
    "PLATE_NO",
    "HEAT_NO",
    "TEST_CERT_NO"
  ],
  "extraction_rules": {
    "PLATE_NO": {
      "regex_patterns": ["Plate No\\.?:?\\s*([A-Z0-9-]+)", "PLATE:?\\s*([A-Z0-9-]+)"],
      "context_keywords": ["plate", "mill"]
    },
    "HEAT_NO": {
      "regex_patterns": ["Heat No\\.?:?\\s*([A-Z0-9-]+)", "HEAT:?\\s*([A-Z0-9-]+)"],
      "context_keywords": ["heat", "melt", "cast"]
    },
    "TEST_CERT_NO": {
      "regex_patterns": ["Certificate\\s*No\\.?:?\\s*([A-Z0-9-]+)", "CERT:?\\s*([A-Z0-9-]+)"],
      "context_keywords": ["certificate", "cert", "test report"]
    }
  }
}

# Directory for template configs
template_dir = os.path.join(settings.BASE_DIR, 'extractor', 'vendor_configs')
os.makedirs(template_dir, exist_ok=True)

# Get all vendors
vendors = Vendor.objects.all()
print(f"Found {len(vendors)} vendors in the database")

for vendor in vendors:
    # Create base filename
    filename = os.path.basename(vendor.config_file.name)
    
    # If filename has a random suffix, clean it
    if '_' in filename:
        parts = filename.split('_')
        if len(parts) > 1 and '.' in parts[-1]:
            last_part = parts[-1]
            ext_idx = last_part.rfind('.')
            if ext_idx > 0:
                filename = '_'.join(parts[:-1]) + last_part[ext_idx:]
    
    # Path to template file
    template_path = os.path.join(template_dir, filename)
    
    # Check if template already exists
    if os.path.exists(template_path):
        print(f"Template already exists: {template_path}")
        continue
    
    # Create a custom config for this vendor
    vendor_config = base_template.copy()
    vendor_config["vendor_name"] = vendor.name
    
    # Save the template
    try:
        with open(template_path, 'w') as f:
            json.dump(vendor_config, f, indent=2)
        print(f"✅ Created template config: {template_path}")
    except Exception as e:
        print(f"❌ Error creating template for {vendor.name}: {str(e)}")

print("\nTemplate creation complete. These will be used as fallbacks when the original config cannot be found.")
