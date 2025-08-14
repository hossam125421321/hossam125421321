# واجهات إدارة صاحب البرنامج
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import date, timedelta
import json

from .models import Company, User, UserProfile
from .master_admin_models import (
    MasterAdmin, CompanySubscription, CompanyPayment, SystemSettings,
    CompanyDatabase, SystemAuditLog, CompanyUsageStats, SystemNotification,
    CompanyBackup
)

def is_master_admin(user):
    """فحص إذا كان المستخدم صاحب البرنامج"""
    return user.is_superuser or hasattr(user, 'masteradmin')

@login_required
@user_passes_test(is_master_admin)
def master_dashboard(request):
    """لوحة تحكم صاحب البرنامج"""
    # إحصائيات عامة
    total_companies = Company.objects.count()
    active_companies = Company.objects.filter(is_active=True).count()
    total_users = User.objects.count()
    total_revenue = CompanyPayment.objects.filter(is_confirmed=True).aggregate(
        total=Sum('amount'))['total'] or 0
    
    # الشركات الجديدة هذا الشهر
    this_month = timezone.now().replace(day=1)
    new_companies = Company.objects.filter(created_at__gte=this_month).count()
    
    # الاشتراكات المنتهية قريباً
    next_week = date.today() + timedelta(days=7)
    expiring_subscriptions = CompanySubscription.objects.filter(
        end_date__lte=next_week,
        is_active=True
    ).count()
    
    # أحدث الشركات
    recent_companies = Company.objects.order_by('-created_at')[:5]
    
    # الدفعات الأخيرة
    recent_payments = CompanyPayment.objects.filter(
        is_confirmed=True
    ).order_by('-created_at')[:5]
    
    # إحصائيات الاستخدام
    usage_stats = CompanyUsageStats.objects.filter(
        date=date.today()
    ).aggregate(
        total_sales=Sum('total_sales'),
        total_invoices=Sum('total_invoices'),
        total_storage=Sum('storage_used_mb')
    )
    
    context = {
        'total_companies': total_companies,
        'active_companies': active_companies,
        'total_users': total_users,
        'total_revenue': total_revenue,
        'new_companies': new_companies,
        'expiring_subscriptions': expiring_subscriptions,
        'recent_companies': recent_companies,
        'recent_payments': recent_payments,
        'usage_stats': usage_stats,
    }
    
    return render(request, 'master_admin/dashboard.html', context)

@login_required
@user_passes_test(is_master_admin)
def companies_management(request):
    """إدارة الشركات"""
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    
    companies = Company.objects.all()
    
    if search:
        companies = companies.filter(
            Q(name__icontains=search) |
            Q(code__icontains=search) |
            Q(email__icontains=search)
        )
    
    if status:
        if status == 'active':
            companies = companies.filter(is_active=True)
        elif status == 'inactive':
            companies = companies.filter(is_active=False)
        elif status == 'expired':
            companies = companies.filter(subscription_end__lt=date.today())
    
    # إضافة معلومات الاشتراك لكل شركة
    for company in companies:
        try:
            subscription = CompanySubscription.objects.filter(
                company=company,
                is_active=True
            ).first()
            company.current_subscription = subscription
        except:
            company.current_subscription = None
    
    paginator = Paginator(companies, 20)
    page = request.GET.get('page')
    companies = paginator.get_page(page)
    
    context = {
        'companies': companies,
        'search': search,
        'status': status,
    }
    
    return render(request, 'master_admin/companies.html', context)

@login_required
@user_passes_test(is_master_admin)
def company_details(request, company_id):
    """تفاصيل الشركة"""
    company = get_object_or_404(Company, id=company_id)
    
    # الاشتراك الحالي
    current_subscription = CompanySubscription.objects.filter(
        company=company,
        is_active=True
    ).first()
    
    # تاريخ الاشتراكات
    subscriptions = CompanySubscription.objects.filter(
        company=company
    ).order_by('-created_at')
    
    # الدفعات
    payments = CompanyPayment.objects.filter(
        subscription__company=company
    ).order_by('-created_at')[:10]
    
    # المستخدمين
    users = UserProfile.objects.filter(company=company)
    
    # إحصائيات الاستخدام
    usage_stats = CompanyUsageStats.objects.filter(
        company=company
    ).order_by('-date')[:30]
    
    # النسخ الاحتياطية
    backups = CompanyBackup.objects.filter(
        company=company
    ).order_by('-created_at')[:5]
    
    context = {
        'company': company,
        'current_subscription': current_subscription,
        'subscriptions': subscriptions,
        'payments': payments,
        'users': users,
        'usage_stats': usage_stats,
        'backups': backups,
    }
    
    return render(request, 'master_admin/company_details.html', context)

@login_required
@user_passes_test(is_master_admin)
def subscriptions_management(request):
    """إدارة الاشتراكات"""
    status = request.GET.get('status', '')
    subscription_type = request.GET.get('type', '')
    
    subscriptions = CompanySubscription.objects.all()
    
    if status:
        if status == 'active':
            subscriptions = subscriptions.filter(is_active=True, end_date__gte=date.today())
        elif status == 'expired':
            subscriptions = subscriptions.filter(end_date__lt=date.today())
        elif status == 'expiring':
            next_week = date.today() + timedelta(days=7)
            subscriptions = subscriptions.filter(
                end_date__lte=next_week,
                end_date__gte=date.today()
            )
    
    if subscription_type:
        subscriptions = subscriptions.filter(subscription_type=subscription_type)
    
    subscriptions = subscriptions.order_by('-created_at')
    
    paginator = Paginator(subscriptions, 20)
    page = request.GET.get('page')
    subscriptions = paginator.get_page(page)
    
    context = {
        'subscriptions': subscriptions,
        'status': status,
        'subscription_type': subscription_type,
    }
    
    return render(request, 'master_admin/subscriptions.html', context)

@login_required
@user_passes_test(is_master_admin)
def create_subscription(request):
    """إنشاء اشتراك جديد"""
    if request.method == 'POST':
        company_id = request.POST.get('company')
        subscription_type = request.POST.get('subscription_type')
        start_date = request.POST.get('start_date')
        months = int(request.POST.get('months', 1))
        
        company = get_object_or_404(Company, id=company_id)
        
        # حساب تاريخ الانتهاء
        start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = start_date + timedelta(days=30 * months)
        
        # تحديد الرسوم حسب نوع الاشتراك
        fees = {
            'basic': {'monthly': 50, 'yearly': 500, 'users': 5, 'branches': 1, 'warehouses': 3, 'storage': 1},
            'standard': {'monthly': 100, 'yearly': 1000, 'users': 15, 'branches': 3, 'warehouses': 10, 'storage': 5},
            'premium': {'monthly': 200, 'yearly': 2000, 'users': 50, 'branches': 10, 'warehouses': 25, 'storage': 20},
            'enterprise': {'monthly': 500, 'yearly': 5000, 'users': 200, 'branches': 50, 'warehouses': 100, 'storage': 100},
        }
        
        fee_info = fees.get(subscription_type, fees['basic'])
        
        # إنشاء الاشتراك
        subscription = CompanySubscription.objects.create(
            company=company,
            subscription_type=subscription_type,
            start_date=start_date,
            end_date=end_date,
            monthly_fee=fee_info['monthly'],
            yearly_fee=fee_info['yearly'],
            max_users=fee_info['users'],
            max_branches=fee_info['branches'],
            max_warehouses=fee_info['warehouses'],
            storage_limit_gb=fee_info['storage'],
            features={
                'pos': subscription_type in ['standard', 'premium', 'enterprise'],
                'manufacturing': subscription_type in ['premium', 'enterprise'],
                'advanced_reports': subscription_type in ['premium', 'enterprise'],
                'api_access': subscription_type == 'enterprise',
            }
        )
        
        # تحديث معلومات الشركة
        company.subscription_end = end_date
        company.subscription_type = subscription_type
        company.max_users = fee_info['users']
        company.max_branches = fee_info['branches']
        company.max_warehouses = fee_info['warehouses']
        company.storage_limit_gb = fee_info['storage']
        company.features = subscription.features
        company.save()
        
        messages.success(request, f'تم إنشاء اشتراك {company.name} بنجاح')
        return redirect('master_admin:subscriptions')
    
    companies = Company.objects.filter(is_active=True)
    context = {'companies': companies}
    
    return render(request, 'master_admin/create_subscription.html', context)

@login_required
@user_passes_test(is_master_admin)
def payments_management(request):
    """إدارة الدفعات"""
    status = request.GET.get('status', '')
    
    payments = CompanyPayment.objects.all()
    
    if status:
        if status == 'confirmed':
            payments = payments.filter(is_confirmed=True)
        elif status == 'pending':
            payments = payments.filter(is_confirmed=False)
    
    payments = payments.order_by('-created_at')
    
    paginator = Paginator(payments, 20)
    page = request.GET.get('page')
    payments = paginator.get_page(page)
    
    context = {
        'payments': payments,
        'status': status,
    }
    
    return render(request, 'master_admin/payments.html', context)

@login_required
@user_passes_test(is_master_admin)
def confirm_payment(request, payment_id):
    """تأكيد الدفعة"""
    payment = get_object_or_404(CompanyPayment, id=payment_id)
    
    if not payment.is_confirmed:
        payment.is_confirmed = True
        payment.confirmed_by = request.user
        payment.save()
        
        # تحديث حالة الاشتراك
        subscription = payment.subscription
        subscription.payment_status = 'paid'
        subscription.save()
        
        messages.success(request, f'تم تأكيد الدفعة #{payment.payment_number}')
    
    return redirect('master_admin:payments')

@login_required
@user_passes_test(is_master_admin)
def system_settings(request):
    """إعدادات النظام"""
    if request.method == 'POST':
        for key, value in request.POST.items():
            if key.startswith('setting_'):
                setting_key = key.replace('setting_', '')
                setting, created = SystemSettings.objects.get_or_create(
                    key=setting_key,
                    defaults={'value': value, 'description': f'إعداد {setting_key}'}
                )
                if not created:
                    setting.value = value
                    setting.save()
        
        messages.success(request, 'تم حفظ الإعدادات بنجاح')
        return redirect('master_admin:system_settings')
    
    settings = SystemSettings.objects.all().order_by('key')
    
    # إعدادات افتراضية
    default_settings = {
        'system_name': 'نظام إدارة الموارد',
        'company_name': 'شركة البرمجيات',
        'support_email': 'support@erp.com',
        'support_phone': '+965-12345678',
        'backup_frequency': 'daily',
        'max_file_size': '10',
        'session_timeout': '60',
        'maintenance_mode': 'false',
    }
    
    # إضافة الإعدادات المفقودة
    for key, default_value in default_settings.items():
        if not settings.filter(key=key).exists():
            SystemSettings.objects.create(
                key=key,
                value=default_value,
                description=f'إعداد {key}'
            )
    
    settings = SystemSettings.objects.all().order_by('key')
    
    context = {'settings': settings}
    return render(request, 'master_admin/system_settings.html', context)

@login_required
@user_passes_test(is_master_admin)
def usage_statistics(request):
    """إحصائيات الاستخدام"""
    # إحصائيات عامة
    total_companies = Company.objects.count()
    active_companies = Company.objects.filter(is_active=True).count()
    total_users = User.objects.count()
    
    # إحصائيات الاشتراكات
    subscription_stats = CompanySubscription.objects.values('subscription_type').annotate(
        count=Count('id')
    )
    
    # إحصائيات الدفعات الشهرية
    current_month = timezone.now().replace(day=1)
    monthly_revenue = CompanyPayment.objects.filter(
        payment_date__gte=current_month,
        is_confirmed=True
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # أكثر الشركات استخداماً
    top_companies = CompanyUsageStats.objects.filter(
        date__gte=date.today() - timedelta(days=30)
    ).values('company__name').annotate(
        total_sales=Sum('total_sales'),
        total_invoices=Sum('total_invoices')
    ).order_by('-total_sales')[:10]
    
    # إحصائيات التخزين
    storage_stats = CompanyUsageStats.objects.filter(
        date=date.today()
    ).aggregate(
        total_storage=Sum('storage_used_mb'),
        avg_storage=Sum('storage_used_mb') / Count('id') if Count('id') > 0 else 0
    )
    
    context = {
        'total_companies': total_companies,
        'active_companies': active_companies,
        'total_users': total_users,
        'subscription_stats': subscription_stats,
        'monthly_revenue': monthly_revenue,
        'top_companies': top_companies,
        'storage_stats': storage_stats,
    }
    
    return render(request, 'master_admin/usage_statistics.html', context)

@login_required
@user_passes_test(is_master_admin)
def notifications_management(request):
    """إدارة الإشعارات"""
    if request.method == 'POST':
        title = request.POST.get('title')
        message = request.POST.get('message')
        notification_type = request.POST.get('notification_type')
        is_global = request.POST.get('is_global') == 'on'
        priority = request.POST.get('priority', 'medium')
        
        notification = SystemNotification.objects.create(
            title=title,
            message=message,
            notification_type=notification_type,
            is_global=is_global,
            priority=priority
        )
        
        if not is_global:
            company_ids = request.POST.getlist('companies')
            companies = Company.objects.filter(id__in=company_ids)
            notification.target_companies.set(companies)
        
        messages.success(request, 'تم إنشاء الإشعار بنجاح')
        return redirect('master_admin:notifications')
    
    notifications = SystemNotification.objects.order_by('-created_at')
    companies = Company.objects.filter(is_active=True)
    
    paginator = Paginator(notifications, 20)
    page = request.GET.get('page')
    notifications = paginator.get_page(page)
    
    context = {
        'notifications': notifications,
        'companies': companies,
    }
    
    return render(request, 'master_admin/notifications.html', context)

@login_required
@user_passes_test(is_master_admin)
def backup_management(request):
    """إدارة النسخ الاحتياطية"""
    backups = CompanyBackup.objects.order_by('-created_at')
    
    paginator = Paginator(backups, 20)
    page = request.GET.get('page')
    backups = paginator.get_page(page)
    
    context = {'backups': backups}
    return render(request, 'master_admin/backups.html', context)

@login_required
@user_passes_test(is_master_admin)
def create_backup(request, company_id):
    """إنشاء نسخة احتياطية"""
    company = get_object_or_404(Company, id=company_id)
    
    try:
        # إنشاء النسخة الاحتياطية
        import os
        import shutil
        from datetime import datetime
        
        backup_name = f"backup_{company.code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_path = f"backups/{backup_name}.db"
        
        # نسخ قاعدة البيانات
        source_db = f"databases/{company.database_name}"
        if os.path.exists(source_db):
            os.makedirs('backups', exist_ok=True)
            shutil.copy2(source_db, backup_path)
            
            # حساب حجم الملف
            file_size = os.path.getsize(backup_path) / (1024 * 1024)  # بالميجابايت
            
            # حفظ معلومات النسخة
            CompanyBackup.objects.create(
                company=company,
                backup_name=backup_name,
                file_path=backup_path,
                file_size_mb=file_size,
                backup_type='full',
                created_by=request.user
            )
            
            messages.success(request, f'تم إنشاء نسخة احتياطية لشركة {company.name}')
        else:
            messages.error(request, 'لم يتم العثور على قاعدة بيانات الشركة')
    
    except Exception as e:
        messages.error(request, f'خطأ في إنشاء النسخة الاحتياطية: {str(e)}')
    
    return redirect('master_admin:company_details', company_id=company_id)

@login_required
@user_passes_test(is_master_admin)
def audit_logs(request):
    """سجلات المراجعة"""
    action_type = request.GET.get('action_type', '')
    user_id = request.GET.get('user', '')
    company_id = request.GET.get('company', '')
    
    logs = SystemAuditLog.objects.all()
    
    if action_type:
        logs = logs.filter(action_type=action_type)
    
    if user_id:
        logs = logs.filter(user_id=user_id)
    
    if company_id:
        logs = logs.filter(company_id=company_id)
    
    logs = logs.order_by('-created_at')
    
    paginator = Paginator(logs, 50)
    page = request.GET.get('page')
    logs = paginator.get_page(page)
    
    # قوائم للفلترة
    users = User.objects.all()
    companies = Company.objects.all()
    
    context = {
        'logs': logs,
        'users': users,
        'companies': companies,
        'action_type': action_type,
        'user_id': user_id,
        'company_id': company_id,
    }
    
    return render(request, 'master_admin/audit_logs.html', context)

# API للحصول على البيانات بصيغة JSON
@login_required
@user_passes_test(is_master_admin)
def api_dashboard_stats(request):
    """API لإحصائيات لوحة التحكم"""
    stats = {
        'total_companies': Company.objects.count(),
        'active_companies': Company.objects.filter(is_active=True).count(),
        'total_users': User.objects.count(),
        'total_revenue': float(CompanyPayment.objects.filter(
            is_confirmed=True
        ).aggregate(total=Sum('amount'))['total'] or 0),
        'expiring_subscriptions': CompanySubscription.objects.filter(
            end_date__lte=date.today() + timedelta(days=7),
            is_active=True
        ).count(),
    }
    
    return JsonResponse(stats)

@login_required
@user_passes_test(is_master_admin)
def api_company_usage(request, company_id):
    """API لاستخدام الشركة"""
    company = get_object_or_404(Company, id=company_id)
    
    # آخر 30 يوم
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    
    usage_data = CompanyUsageStats.objects.filter(
        company=company,
        date__range=[start_date, end_date]
    ).order_by('date')
    
    data = {
        'dates': [stat.date.strftime('%Y-%m-%d') for stat in usage_data],
        'sales': [float(stat.total_sales) for stat in usage_data],
        'invoices': [stat.total_invoices for stat in usage_data],
        'users': [stat.active_users for stat in usage_data],
    }
    
    return JsonResponse(data)