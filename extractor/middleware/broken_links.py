import os
from django.http import HttpResponse, FileResponse
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class BrokenLinkMiddleware:
    """
    Middleware to handle broken links for file downloads gracefully
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Only process FileResponse errors
        if isinstance(response, FileResponse) and response.status_code == 200:
            # FileResponse's file attribute might be the actual file object
            try:
                # Check if the file exists
                if not hasattr(response, 'file') or not response.file.readable():
                    logger.warning(f"Broken file link detected: {request.path}")
                    return self.handle_broken_file(request)
            except (IOError, FileNotFoundError, AttributeError) as e:
                logger.warning(f"File access error: {e} for path: {request.path}")
                return self.handle_broken_file(request)
                
        return response
    
    def handle_broken_file(self, request):
        """
        Return a proper response for broken file links
        """
        # Get the requested file name from the path
        file_name = os.path.basename(request.path)
        
        # Create a descriptive response
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
                <a href="/" class="btn">Go to Dashboard</a>
            </div>
        </body>
        </html>
        """
        
        return HttpResponse(html_content, status=404, content_type='text/html')
