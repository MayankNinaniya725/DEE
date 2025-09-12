from django import template
import urllib.parse

register = template.Library()

@register.filter
def urlencode(value):
    """Encodes a value for use in a URL."""
    return urllib.parse.quote(str(value))
