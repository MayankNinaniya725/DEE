from django import template

register = template.Library()

@register.filter
def filename(value):
    """Returns the filename from a file path."""
    try:
        return value.split('/')[-1]
    except:
        return value
