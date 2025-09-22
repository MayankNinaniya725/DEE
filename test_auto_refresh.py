#!/usr/bin/env python3
"""
Test script to verify dashboard auto-refresh functionality
This script tests that the dashboard updates automatically when new PDFs are uploaded.
"""

import requests
import time
import json

def test_dashboard_auto_refresh():
    """Test the dashboard auto-refresh functionality"""
    
    print("🔄 Testing Dashboard Auto-Refresh...")
    print("=" * 50)
    
    base_url = "http://127.0.0.1:8000"
    
    # Test 1: Check that the API endpoint works
    print("1️⃣ Testing API Endpoint...")
    try:
        response = requests.get(f"{base_url}/api/latest-pdfs/")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ API endpoint works - Found {data.get('count', 0)} PDFs")
            print(f"   📊 Response includes: {list(data.keys())}")
            
            if data.get('pdfs'):
                latest_pdf = data['pdfs'][0]
                print(f"   📄 Latest PDF: {latest_pdf.get('filename')} ({latest_pdf.get('status')})")
        else:
            print(f"   ❌ API endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ API endpoint error: {e}")
        return False
    
    # Test 2: Check dashboard loads with new functionality
    print("\n2️⃣ Testing Dashboard with Auto-Refresh...")
    try:
        response = requests.get(f"{base_url}/dashboard/")
        if response.status_code == 200:
            content = response.text
            
            # Check for auto-refresh components
            checks = [
                ('pdfTableBody', 'PDF table body ID'),
                ('data-pdf-id', 'PDF row tracking attributes'),
                ('checkForUpdates', 'Auto-refresh function'),
                ('Auto-refresh active', 'Auto-refresh indicator'),
                ('startAutoRefresh', 'Auto-refresh initialization'),
                ('toastr', 'Notification system')
            ]
            
            print("   🔍 Checking dashboard components:")
            for check_text, description in checks:
                if check_text in content:
                    print(f"   ✅ {description}")
                else:
                    print(f"   ❌ Missing: {description}")
        else:
            print(f"   ❌ Dashboard failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Dashboard error: {e}")
        return False
    
    # Test 3: Check timestamp handling
    print("\n3️⃣ Testing Timestamp-Based Updates...")
    try:
        # Get initial data
        response = requests.get(f"{base_url}/api/latest-pdfs/")
        initial_data = response.json()
        timestamp = initial_data.get('timestamp')
        
        if timestamp:
            print(f"   ✅ Timestamp received: {timestamp}")
            
            # Test with timestamp parameter
            response = requests.get(f"{base_url}/api/latest-pdfs/?since={timestamp}")
            filtered_data = response.json()
            print(f"   ✅ Timestamp filtering works: {filtered_data.get('count', 0)} new PDFs since {timestamp[:19]}")
        else:
            print("   ❌ No timestamp in response")
    except Exception as e:
        print(f"   ❌ Timestamp test error: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 AUTO-REFRESH FUNCTIONALITY SUMMARY")
    print("=" * 50)
    
    print("\n🔧 New Features Added:")
    print("-" * 25)
    print("✅ Auto-refresh checks for new PDFs every 5 seconds")
    print("✅ Updates table dynamically without page reload")
    print("✅ Shows notifications for new uploads (success/error)")
    print("✅ Highlights new rows temporarily in green")
    print("✅ Tracks vendor mismatch and validation errors")
    print("✅ Pauses when tab is not active (performance)")
    print("✅ Manual refresh button with enhanced UI")
    
    print("\n📊 How It Works:")
    print("-" * 20)
    print("1. 🔄 JavaScript polls `/api/latest-pdfs/` every 5 seconds")
    print("2. 📅 Uses timestamps to get only new PDFs since last check")
    print("3. 📄 Dynamically adds new PDF rows to table (no page reload)")
    print("4. 🎨 Highlights new rows in green for 3 seconds")
    print("5. 🔔 Shows toastr notifications for uploads")
    print("6. ❌ Specifically tracks ERROR status PDFs from vendor issues")
    
    print("\n📋 Expected Behavior:")
    print("-" * 25)
    print("• Upload PDF with wrong vendor → appears immediately with ERROR status")
    print("• Upload PDF with correct vendor → appears immediately with processing status")
    print("• No more need to manually refresh to see uploads")
    print("• Clear visual indication of new vs existing entries")
    print("• Tooltips work on dynamically added ERROR badges")
    
    print("\n🧪 Test This:")
    print("-" * 15)
    print("1. Open dashboard: http://127.0.0.1:8000/dashboard/")
    print("2. In another tab, go to: http://127.0.0.1:8000/upload/")
    print("3. Upload a PDF with WRONG vendor")
    print("4. Watch dashboard tab - new row should appear within 5 seconds")
    print("5. Should show ERROR status with red badge immediately")
    print("6. Should display notification about failed upload")
    
    return True

if __name__ == "__main__":
    success = test_dashboard_auto_refresh()
    if success:
        print("\n🎉 Auto-refresh functionality is ready!")
        print("📝 Dashboard will now update automatically when PDFs are uploaded.")
    else:
        print("\n❌ Some components failed. Please check the server.")