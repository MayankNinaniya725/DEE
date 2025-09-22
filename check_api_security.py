#!/usr/bin/env python3
"""
Security audit of API endpoints for the extractor system
"""

import os
import django
import sys
from django.urls import reverse
from django.test import RequestFactory, Client

# Add the project directory to Python path and set up Django
sys.path.append('/mnt/c/Users/Mayank/Desktop/DEE/extractor_project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

def check_api_security():
    """Check API endpoint security"""
    
    print("🔒 API Security Audit")
    print("=" * 50)
    
    # Create a test client
    client = Client()
    
    # Test endpoints without authentication
    print("\n1. Testing API endpoints without authentication:")
    print("-" * 40)
    
    # Test get_latest_pdfs endpoint
    try:
        response = client.get('/api/get-latest-pdfs/')
        print(f"📡 /api/get-latest-pdfs/ - Status: {response.status_code}")
        
        if response.status_code == 200:
            print("   ⚠️  WARNING: API accessible without authentication!")
        elif response.status_code == 302:
            print("   ✅ Good: Redirects to login (likely requires auth)")
        elif response.status_code == 401:
            print("   ✅ Good: Returns 401 Unauthorized")
        elif response.status_code == 403:
            print("   ✅ Good: Returns 403 Forbidden")
        else:
            print(f"   ❓ Unexpected status code: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error testing endpoint: {e}")
    
    # Test download_package endpoint
    try:
        response = client.get('/download-package/1/')
        print(f"📦 /download-package/1/ - Status: {response.status_code}")
        
        if response.status_code == 200:
            print("   ⚠️  WARNING: Download accessible without authentication!")
        elif response.status_code == 302:
            print("   ✅ Good: Redirects to login (likely requires auth)")
        elif response.status_code == 401:
            print("   ✅ Good: Returns 401 Unauthorized")
        elif response.status_code == 403:
            print("   ✅ Good: Returns 403 Forbidden")
        elif response.status_code == 404:
            print("   ✅ Good: Returns 404 (but would need auth for real files)")
        else:
            print(f"   ❓ Unexpected status code: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error testing endpoint: {e}")
    
    # Test upload endpoint
    try:
        response = client.get('/')  # Main upload page
        print(f"🏠 / (Main upload page) - Status: {response.status_code}")
        
        if response.status_code == 200:
            print("   ⚠️  Public access to upload page")
        elif response.status_code == 302:
            print("   ✅ Good: Redirects to login")
        else:
            print(f"   ❓ Status: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error testing endpoint: {e}")
    
    print("\n2. Checking authentication middleware:")
    print("-" * 40)
    
    # Check if authentication middleware is in place
    from django.conf import settings
    
    middlewares = getattr(settings, 'MIDDLEWARE', [])
    auth_middlewares = [m for m in middlewares if 'auth' in m.lower() or 'session' in m.lower()]
    
    print(f"🔧 Authentication-related middleware found:")
    for middleware in auth_middlewares:
        print(f"   - {middleware}")
    
    # Check if login_required decorators are used
    print("\n3. Checking view protection:")
    print("-" * 40)
    
    # Read views.py to check for login_required
    try:
        with open('/mnt/c/Users/Mayank/Desktop/DEE/extractor_project/extractor/views.py', 'r') as f:
            views_content = f.read()
            
        login_required_count = views_content.count('@login_required')
        print(f"🔐 @login_required decorators found: {login_required_count}")
        
        if 'from django.contrib.auth.decorators import login_required' in views_content:
            print("   ✅ login_required imported")
        else:
            print("   ⚠️  login_required not imported (might be in other files)")
            
    except Exception as e:
        print(f"   ❌ Error reading views.py: {e}")
    
    # Check API views
    try:
        with open('/mnt/c/Users/Mayank/Desktop/DEE/extractor_project/extractor/views/api_views.py', 'r') as f:
            api_views_content = f.read()
            
        login_required_count = api_views_content.count('@login_required')
        print(f"🔐 @login_required in API views: {login_required_count}")
        
        if 'from django.contrib.auth.decorators import login_required' in api_views_content:
            print("   ✅ login_required imported in API views")
        else:
            print("   ⚠️  login_required not imported in API views")
            
    except Exception as e:
        print(f"   ❌ Error reading api_views.py: {e}")
    
    print("\n4. Security Recommendations:")
    print("-" * 40)
    print("✅ Ensure all sensitive endpoints use @login_required")
    print("✅ Use CSRF protection for form submissions") 
    print("✅ Implement rate limiting for API endpoints")
    print("✅ Use HTTPS in production")
    print("✅ Validate user permissions for file downloads")
    print("✅ Log access attempts for audit purposes")
    
    print("\n🎯 Summary:")
    print("The API endpoints should be protected with authentication.")
    print("Test with a logged-in user to verify full functionality.")

if __name__ == "__main__":
    check_api_security()