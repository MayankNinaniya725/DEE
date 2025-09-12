"""
Create a simple Jazzmin base.html template to fix the issue.
This template will extend the admin base.html template.
"""

TEMPLATE = """{% extends "admin/base.html" %}

{% block title %}{{ title }} | {{ site_title|default:_('Django site admin') }}{% endblock %}

{% block branding %}
<h1 id="site-name"><a href="{% url 'admin:index' %}">{{ site_header|default:_('Django administration') }}</a></h1>
{% endblock %}

{% block nav-global %}{% endblock %}
"""

# Create directory if it doesn't exist
import os
os.makedirs('templates/jazzmin', exist_ok=True)

# Write the template
with open('templates/jazzmin/base.html', 'w') as f:
    f.write(TEMPLATE)

print("Created templates/jazzmin/base.html")
