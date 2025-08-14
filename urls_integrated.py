"""
Integrated URL patterns for the ERP system
Contains additional URL patterns for integrated features
"""

from django.urls import path
from . import views

# Integrated URL patterns
urlpatterns = [
    # Integrated dashboard and features
    path('dashboard/', views.dashboard, name='integrated_dashboard'),
    path('settings/', views.settings_page, name='integrated_settings'),
    
    # Add more integrated URL patterns as needed
    # These are placeholder patterns that can be expanded
]