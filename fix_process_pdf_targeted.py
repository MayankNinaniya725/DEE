import os
import sys
import django

# Setup Django
sys.path.append('/code')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

print("===== MAKING TARGETED FIX TO PROCESS_PDF VIEW =====")

# Create a backup of the core.py file
os.system("cp /code/extractor/views/core.py /code/extractor/views/core.py.targeted_fix_bak")
print("✅ Created backup at /code/extractor/views/core.py.targeted_fix_bak")

# Read the current content
with open('/code/extractor/views/core.py', 'r') as f:
    content = f.read()

# Define the specific fix
old_creation = """        uploaded_pdf = UploadedPDF.objects.create(
            vendor=vendor,
            file=file_path,
            file_hash=file_hash,
            file_size=pdf_file.size,

        )"""

new_creation = """        uploaded_pdf = UploadedPDF.objects.create(
            vendor=vendor,
            file=file_path,
            file_hash=file_hash,
            file_size=pdf_file.size,
            status='PENDING'
        )"""

# Apply the fix
updated_content = content.replace(old_creation, new_creation)

# Check if the replacement worked
if updated_content == content:
    print("❌ Could not find the exact creation pattern")
    print("   Trying alternative approaches...")
    
    # Try with different whitespace
    old_creation_alt = """        uploaded_pdf = UploadedPDF.objects.create(
            vendor=vendor,
            file=file_path,
            file_hash=file_hash,
            file_size=pdf_file.size,
        )"""
        
    updated_content = content.replace(old_creation_alt, new_creation)
    
    if updated_content == content:
        print("❌ Still could not find the creation pattern")
        print("   Using line-by-line analysis...")
        
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if "uploaded_pdf = UploadedPDF.objects.create(" in line:
                print(f"✅ Found creation at line {i+1}")
                # Look for the closing parenthesis
                start_idx = i
                end_idx = start_idx
                for j in range(start_idx, len(lines)):
                    if "))" in lines[j] or ")," in lines[j] or lines[j].strip() == ")":
                        end_idx = j
                        break
                
                # Replace with new implementation
                old_creation_lines = lines[start_idx:end_idx+1]
                old_creation_block = '\n'.join(old_creation_lines)
                print(f"Original creation block (lines {start_idx+1}-{end_idx+1}):")
                print(old_creation_block)
                
                # Generate the right indentation
                indent = ' ' * (len(line) - len(line.lstrip()))
                status_line = f"{indent}    status='PENDING'"
                
                # Insert status before the closing parenthesis
                if end_idx > start_idx:
                    if ")" in lines[end_idx]:
                        lines.insert(end_idx, status_line)
                        print(f"✅ Inserted status line at position {end_idx+1}")
                        break
                
        # Reconstruct the content
        updated_content = '\n'.join(lines)
else:
    print("✅ Successfully replaced the creation pattern")

# Save the updated content
with open('/code/extractor/views/core.py', 'w') as f:
    f.write(updated_content)

print("✅ Updated process_pdf view with status field")
print("\nFix has been applied. Please restart the web container to apply changes.")
