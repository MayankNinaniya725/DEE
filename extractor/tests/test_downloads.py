"""
Unit tests for download_all_pdfs_package function

These tests verify the ZIP creation functionality works properly under various conditions
"""
import os
import io
import tempfile
import zipfile
from unittest.mock import patch, MagicMock

from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from django.contrib.messages.storage.fallback import FallbackStorage
from django.http import FileResponse

from extractor.models import UploadedPDF, ExtractedData, Vendor
from extractor.views.downloads import download_all_pdfs_package

class DownloadAllPdfsPackageTest(TestCase):
    """
    Test cases for the download_all_pdfs_package view function
    """
    
    def setUp(self):
        """Set up test data"""
        # Create a test vendor
        self.vendor = Vendor.objects.create(name="Test Vendor")
        
        # Create a test PDF record
        self.pdf = UploadedPDF.objects.create(
            file="uploads/test.pdf",  # This file doesn't need to exist for some tests
            vendor=self.vendor,
            status="COMPLETED",
            uploaded_at="2025-01-01T00:00:00Z"
        )
        
        # Create some test extracted data
        self.extracted_data = ExtractedData.objects.create(
            pdf=self.pdf,
            field_key="TEST_FIELD",
            field_value="Test Value",
            page_number=1,
            created_at="2025-01-01T00:00:00Z"
        )
        
        # Create a request factory
        self.factory = RequestFactory()
        
    def test_no_pdfs(self):
        """Test when no PDFs with extracted data exist"""
        # Delete existing data
        ExtractedData.objects.all().delete()
        UploadedPDF.objects.all().delete()
        
        # Create a request
        request = self.factory.get(reverse('download_all_pdfs_package'))
        
        # Add messages support
        setattr(request, 'session', 'session')
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        
        # Call the view
        with patch('extractor.views.downloads.redirect') as mock_redirect:
            mock_redirect.return_value = "Redirected to dashboard"
            response = download_all_pdfs_package(request)
            
        # Check that we were redirected
        mock_redirect.assert_called_once_with("dashboard")
        self.assertEqual(response, "Redirected to dashboard")
    
    @patch('os.path.exists')
    @patch('os.access')
    @patch('os.path.getsize')
    @patch('builtins.open')
    def test_pdf_file_missing(self, mock_open, mock_getsize, mock_access, mock_exists):
        """Test when PDF file is missing"""
        # Mock file existence check to fail
        mock_exists.return_value = False
        
        # Create a request
        request = self.factory.get(reverse('download_all_pdfs_package'))
        
        # Add messages support
        setattr(request, 'session', 'session')
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        
        # Call the view
        with patch('extractor.views.downloads.redirect') as mock_redirect:
            mock_redirect.return_value = "Redirected to dashboard"
            response = download_all_pdfs_package(request)
            
        # Check that we were redirected
        mock_redirect.assert_called_once_with("dashboard")
        self.assertEqual(response, "Redirected to dashboard")
        
    @patch('os.path.exists')
    @patch('os.access')
    @patch('os.path.getsize')
    @patch('builtins.open')
    @patch('zipfile.ZipFile')
    @patch('pandas.DataFrame.to_excel')
    def test_successful_download(self, mock_to_excel, mock_zipfile, mock_open, 
                                mock_getsize, mock_access, mock_exists):
        """Test successful ZIP creation"""
        # Mock file operations to succeed
        mock_exists.return_value = True
        mock_access.return_value = True
        mock_getsize.return_value = 1024  # 1KB
        
        # Mock open to return file-like objects
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        # Mock ZipFile
        mock_zip = MagicMock()
        mock_zipfile.return_value.__enter__.return_value = mock_zip
        
        # Create a request
        request = self.factory.get(reverse('download_all_pdfs_package'))
        
        # Add messages support
        setattr(request, 'session', 'session')
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        
        # Call the view
        response = download_all_pdfs_package(request)
        
        # Check response
        self.assertIsInstance(response, FileResponse)
        self.assertEqual(response['Content-Type'], 'application/zip')
        self.assertTrue('attachment; filename=' in response['Content-Disposition'])

def run_tests():
    """Run the tests"""
    import django
    from django.test.utils import get_runner
    from django.conf import settings
    
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(['tests'])
    return failures

if __name__ == '__main__':
    run_tests()
