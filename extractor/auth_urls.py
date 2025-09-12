"""
Custom auth URLs to handle admin login/logout redirections properly
"""
from django.urls import path
from django.views.generic import RedirectView
from django.urls import reverse_lazy

urlpatterns = [
    # Override the default profile view to redirect to admin
    path('profile/', 
         RedirectView.as_view(url=reverse_lazy('admin:index')), 
         name='profile'),
]
