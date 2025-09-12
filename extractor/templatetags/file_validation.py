import os
from django.conf import settings
from django.template.defaultfilters import register
from django.urls import reverse
from django.utils.html import format_html
import logging

logger = logging.getLogger(__name__)

@register.filter
def file_exists(file_path):
    """
    Template filter to check if a file exists
    Usage: {% if file_path|file_exists %}...{% endif %}
    """
    if not file_path or not isinstance(file_path, str):
        return False
        
    # Handle relative paths
    if not file_path.startswith('/'):
        # Check if it's a media path
        if file_path.startswith('media/'):
            full_path = os.path.join(settings.BASE_DIR, file_path)
        else:
            full_path = os.path.join(settings.MEDIA_ROOT, file_path)
    else:
        full_path = file_path
        
    return os.path.exists(full_path)

@register.filter
def safe_file_link(file_path, link_text=None):
    """
    Template filter to create a safe file download link
    Will show a disabled link if the file doesn't exist
    
    Usage: {{ file_path|safe_file_link:"Download" }}
    """
    if not link_text:
        link_text = os.path.basename(file_path) if file_path else "Download"
    
    if not file_path:
        return format_html('<span class="broken-link"><i class="fas fa-exclamation-triangle"></i> File not available</span>')
        
    # Check if file exists
    if file_exists(file_path):
        # If it starts with media/, convert to URL
        if file_path.startswith('media/'):
            url = f"/{file_path}"
        elif file_path.startswith('/media/'):
            url = file_path
        else:
            url = f"/media/{file_path}"
            
        return format_html('<a href="{}" class="file-link"><i class="fas fa-download"></i> {}</a>', url, link_text)
    else:
        logger.warning(f"Attempted to link to non-existent file: {file_path}")
        return format_html('<span class="broken-link"><i class="fas fa-exclamation-triangle"></i> {} not available</span>', link_text)

@register.filter
def validated_download_url(url_name, params=None):
    """
    Template filter to create a validated download URL
    Will check if the URL is valid before rendering
    
    Usage: {{ 'download_excel'|validated_download_url:pdf_id }}
    """
    if not url_name:
        return "#"
        
    try:
        # Generate the URL
        if params:
            url = f"{reverse(url_name)}?{params}" if isinstance(params, str) else reverse(url_name, args=[params])
        else:
            url = reverse(url_name)
            
        return url
    except Exception as e:
        logger.warning(f"Error generating URL for {url_name}: {e}")
        return "#"
