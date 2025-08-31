from django import template

register = template.Library()

@register.filter
def filename(value):
    """Returns the filename from a file path."""
    try:
        return value.split('/')[-1]
    except:
        return value

@register.filter
def get_item(dictionary, key):
    """Gets an item from a dictionary using any key, including ones with spaces."""
    try:
        return dictionary.get(key, '')
    except (AttributeError, TypeError):
        return ''
        
@register.filter
def excel_format(value, field_name):
    """Formats values to match Excel format, especially for certificate fields."""
    if not value:
        return ''
    
    # Format specific fields according to Excel display format
    if field_name in ['PLATE_NO', 'HEAT_NO', 'TEST_CERT_NO']:
        # Convert to uppercase if it's not already
        return str(value).upper().strip()
    
    return value
