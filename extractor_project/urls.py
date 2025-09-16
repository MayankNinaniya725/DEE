from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from django.contrib.auth import views as auth_views

# Configure admin site
admin.site.site_header = 'PDF Data Extractor'
admin.site.site_title = 'PDF Extractor Portal'
admin.site.index_title = 'PDF Extractor Management'

urlpatterns = [
    # Custom admin logout URL - must be before admin.site.urls
    re_path(r'^admin/logout/$', auth_views.LogoutView.as_view(next_page='/admin/login/'), name='admin_logout'),
    
    # Admin interface
    path('admin/', admin.site.urls),
    
    # Include the app URLs - this should handle all paths including downloads  
    path('', include('extractor.urls')),
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
