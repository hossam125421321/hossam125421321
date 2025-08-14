# روابط إدارة صاحب البرنامج
from django.urls import path
from . import master_admin_views

app_name = 'master_admin'

urlpatterns = [
    # لوحة التحكم الرئيسية
    path('', master_admin_views.master_dashboard, name='dashboard'),
    
    # إدارة الشركات
    path('companies/', master_admin_views.companies_management, name='companies'),
    path('companies/<int:company_id>/', master_admin_views.company_details, name='company_details'),
    
    # إدارة الاشتراكات
    path('subscriptions/', master_admin_views.subscriptions_management, name='subscriptions'),
    path('subscriptions/create/', master_admin_views.create_subscription, name='create_subscription'),
    
    # إدارة الدفعات
    path('payments/', master_admin_views.payments_management, name='payments'),
    path('payments/<int:payment_id>/confirm/', master_admin_views.confirm_payment, name='confirm_payment'),
    
    # إعدادات النظام
    path('settings/', master_admin_views.system_settings, name='system_settings'),
    
    # إحصائيات الاستخدام
    path('statistics/', master_admin_views.usage_statistics, name='usage_statistics'),
    
    # إدارة الإشعارات
    path('notifications/', master_admin_views.notifications_management, name='notifications'),
    
    # إدارة النسخ الاحتياطية
    path('backups/', master_admin_views.backup_management, name='backups'),
    path('backups/create/<int:company_id>/', master_admin_views.create_backup, name='create_backup'),
    
    # سجلات المراجعة
    path('audit-logs/', master_admin_views.audit_logs, name='audit_logs'),
    
    # APIs
    path('api/dashboard-stats/', master_admin_views.api_dashboard_stats, name='api_dashboard_stats'),
    path('api/company-usage/<int:company_id>/', master_admin_views.api_company_usage, name='api_company_usage'),
]