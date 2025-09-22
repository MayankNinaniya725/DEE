#!/usr/bin/env python3
"""
Try different approaches to extract Hengrun table data
"""
import os
import sys
import django
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

import pdfplumber

def try_different_extraction_methods():
    """Try different methods to extract the table data"""
    
    pdf_path = "media/hengrun_test.pdf"
    
    print("🔍 Trying Different Extraction Methods")
    print("=" * 50)
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[0]
            
            # Method 1: Table extraction
            print("1️⃣  Table Extraction:")
            tables = page.extract_tables()
            print(f"   Tables found: {len(tables)}")
            
            for i, table in enumerate(tables):
                print(f"   Table {i+1}:")
                if table and len(table) > 0:
                    print(f"     Rows: {len(table)}")
                    print(f"     Columns: {len(table[0]) if table[0] else 0}")
                    
                    # Show first few rows
                    for j, row in enumerate(table[:3]):
                        print(f"     Row {j+1}: {row}")
                        
                        # Look for part numbers in each cell
                        for cell in row:
                            if cell and ('6-0' in str(cell) or 'S12' in str(cell)):
                                print(f"       💡 Potential data found: {cell}")
                else:
                    print(f"     Empty table")
            
            # Method 2: Extract text with different settings
            print(f"\n2️⃣  Text Extraction with Settings:")
            text_settings = [
                {},
                {"x_tolerance": 3, "y_tolerance": 3},
                {"keep_blank_chars": True},
                {"layout": True}
            ]
            
            for i, settings in enumerate(text_settings):
                text = page.extract_text(**settings)
                print(f"   Method {i+1}: {len(text) if text else 0} characters")
                if text and '6-0' in text:
                    print(f"     ✅ Found potential part numbers!")
                    # Show lines containing 6-0
                    lines = text.split('\n')
                    for line_num, line in enumerate(lines):
                        if '6-0' in line:
                            print(f"       Line {line_num}: {line.strip()}")
            
            # Method 3: Character extraction with positions
            print(f"\n3️⃣  Character-level Extraction:")
            chars = page.chars
            print(f"   Total characters: {len(chars)}")
            
            # Look for characters that form "6-0003" or "6-0002"
            text_from_chars = ''.join([char['text'] for char in chars])
            print(f"   Reconstructed text length: {len(text_from_chars)}")
            
            if '6-0' in text_from_chars:
                print(f"     ✅ Found part numbers in character data!")
                import re
                matches = re.findall(r'6-\d{4}', text_from_chars)
                print(f"     Part numbers found: {matches}")
            
            # Method 4: Crop specific regions (if we know approximate positions)
            print(f"\n4️⃣  Region-based Extraction:")
            
            # Get page dimensions
            bbox = page.bbox
            print(f"   Page size: {bbox}")
            
            # Try different vertical sections
            height = bbox[3] - bbox[1]
            sections = [
                (0, 0, bbox[2], height * 0.3),  # Top 30%
                (0, height * 0.3, bbox[2], height * 0.7),  # Middle 40%
                (0, height * 0.7, bbox[2], height)  # Bottom 30%
            ]
            
            for i, section in enumerate(sections):
                try:
                    cropped = page.crop(section)
                    cropped_text = cropped.extract_text()
                    print(f"   Section {i+1}: {len(cropped_text) if cropped_text else 0} characters")
                    
                    if cropped_text and ('6-0' in cropped_text or 'S12' in cropped_text):
                        print(f"     ✅ Found data in section {i+1}:")
                        lines = cropped_text.split('\n')
                        for line in lines[:5]:  # Show first 5 lines
                            if line.strip():
                                print(f"       {line.strip()}")
                except Exception as e:
                    print(f"   Section {i+1}: Error - {e}")
    
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try_different_extraction_methods()