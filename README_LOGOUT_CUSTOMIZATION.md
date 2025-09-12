# Admin Logout Customization Guide

This document explains how to customize the logout behavior in your Django application.

## Default Behavior

By default, when a user logs out from the admin interface:

1. They are logged out via a GET request to `/admin/logout/`
2. They are redirected to the admin login page (`/admin/login/`)
3. This behavior is controlled by the `LOGOUT_REDIRECT_URL` setting in `settings.py`

## How to Customize the Redirect URL

To change where users are redirected after logout, simply modify the `LOGOUT_REDIRECT_URL` setting in `settings.py`:

```python
# Redirect to admin login (default)
LOGOUT_REDIRECT_URL = '/admin/login/'

# Or redirect to the main site login
# LOGOUT_REDIRECT_URL = '/login/'

# Or redirect to the home page
# LOGOUT_REDIRECT_URL = '/'
```

## Advanced Customization

For more advanced customization:

1. **Custom Logout Template**: You can edit `templates/admin/logout.html` to customize the logout page
2. **Custom Logout View**: For complete control, you can create a custom logout view and update `urls.py`

## Troubleshooting

If you experience HTTP 405 errors when logging out:

1. Ensure the logout link is a simple anchor tag (GET request), not a form (POST request)
2. Check for any JavaScript that might be forcing POST requests
3. Verify there are no middleware or security settings blocking GET requests to `/admin/logout/`

## Note on Security

Django's admin logout via GET is secure because:
- The CSRF token is not needed for logout operations
- Session invalidation happens server-side
- The redirect behavior is controlled by the server
