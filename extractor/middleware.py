# extractor/middleware.py
import os
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponse, FileResponse

class NoCacheMiddleware(MiddlewareMixin):
    """
    Add headers to prevent caching of responses in the browser
    """
    def process_response(self, request, response):
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response

class BrokenLinkMiddleware:
    """
    Middleware to handle broken links for file downloads gracefully
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Process the request first
        response = self.get_response(request)
        
        # Only process FileResponse errors or media URLs
        if (isinstance(response, FileResponse) and response.status_code == 200) or \
           ('/media/' in request.path and response.status_code == 404):
            
            # For FileResponse objects, check if file exists and is readable
            if isinstance(response, FileResponse):
                try:
                    if not hasattr(response, 'file') or not response.file.readable():
                        return self.handle_broken_file(request)
                except (IOError, FileNotFoundError, AttributeError):
                    return self.handle_broken_file(request)
            
            # For 404 media requests, return our custom response
            if '/media/' in request.path and response.status_code == 404:
                return self.handle_broken_file(request)
                
        return response
    
    def handle_broken_file(self, request):
        """
        Return a proper response for broken file links
        """
        # Get the requested file name from the path
        file_name = os.path.basename(request.path)
        
        # Check if this is an AJAX request
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return HttpResponse(
                status=404,
                content=f"The requested file '{file_name}' could not be found or is no longer available.",
                content_type='text/plain'
            )
        
        # Otherwise return a user-friendly HTML page
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>File Not Found</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 40px;
                    line-height: 1.6;
                    color: #333;
                }}
                .error-container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 30px;
                    background-color: #f8f9fa;
                    border-radius: 10px;
                    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                    text-align: center;
                }}
                h1 {{
                    color: #dc3545;
                    margin-bottom: 20px;
                }}
                .btn {{
                    display: inline-block;
                    padding: 10px 20px;
                    background-color: #007bff;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    margin-top: 20px;
                }}
                .btn:hover {{
                    background-color: #0069d9;
                }}
                .error-icon {{
                    font-size: 60px;
                    color: #dc3545;
                }}
            </style>
        </head>
        <body>
            <div class="error-container">
                <div class="error-icon">⚠️</div>
                <h1>File Not Found</h1>
                <p>The requested file <strong>{file_name}</strong> could not be found or is no longer available.</p>
                <p>This could be due to one of the following reasons:</p>
                <ul style="text-align: left;">
                    <li>The file has been deleted or moved</li>
                    <li>The file path is incorrect</li>
                    <li>You don't have permission to access this file</li>
                </ul>
                <a href="javascript:history.back()" class="btn">Go Back</a>
                <a href="/dashboard/" class="btn">Go to Dashboard</a>
            </div>
        </body>
        </html>
        """
        
        return HttpResponse(html_content, status=404, content_type='text/html')
