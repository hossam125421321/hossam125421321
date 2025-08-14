# -*- coding: utf-8 -*-
"""
URLs للصلاحيات المحسنة
"""

from django.urls import path
from . import permissions_views

urlpatterns = [
    # لوحة تحكم الصلاحيات
    path('permissions/', permissions_views.permissions_dashboard, name='permissions_dashboard'),
    
    # إدارة المستخدمين والصلاحيات
    path('permissions/users/', permissions_views.users_permissions_list, name='users_permissions_list'),
    path('permissions/user/<int:user_id>/', permissions_views.user_permissions_detail, name='user_permissions_detail'),
    path('permissions/user/<int:user_id>/edit/', permissions_views.edit_user_permissions, name='edit_user_permissions'),
    
    # مجموعات الصلاحيات
    path('permissions/groups/', permissions_views.permission_groups_list, name='permission_groups_list'),
    path('permissions/assign-group/', permissions_views.assign_permission_group, name='assign_permission_group'),
    
    # عمليات سريعة
    path('permissions/quick-toggle/', permissions_views.quick_permission_toggle, name='quick_permission_toggle'),
    
    # تصدير واستيراد
    path('permissions/user/<int:user_id>/export/', permissions_views.export_user_permissions, name='export_user_permissions'),
    path('permissions/import/', permissions_views.import_user_permissions, name='import_user_permissions'),
    
    # سجل المراجعة
    path('permissions/audit-log/', permissions_views.permissions_audit_log, name='permissions_audit_log'),
]