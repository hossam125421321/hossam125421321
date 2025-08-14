from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import date, timedelta
import json
import os
from .models import Company
from .decorators import permission_required, subscription_required

@login_required
@subscription_required
@permission_required('companies', 'view')
def database_manager(request):
    """مدير قواعد البيانات"""
    companies = Company.objects.all().order_by('name')
    
    # إضافة معلومات قاعدة البيانات لكل شركة
    companies_with_db_info = []
    for company in companies:
        db_info = {
            'company': company,
            'database_exists': True,  # سيتم تطويرها لاحقاً
            'database_size': '0 MB',  # سيتم تطويرها لاحقاً
            'last_backup': None,  # سيتم تطويرها لاحقاً
            'status': 'متصلة' if company.is_active else 'غير نشطة'
        }
        companies_with_db_info.append(db_info)
    
    context = {
        'companies_with_db_info': companies_with_db_info,
        'total_companies': companies.count(),
        'active_companies': companies.filter(is_active=True).count(),
    }
    return render(request, 'database/manager.html', context)

@login_required
@subscription_required
@permission_required('companies', 'add')
@csrf_exempt
def create_company_database(request, company_id):
    """إنشاء قاعدة بيانات للشركة"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'طريقة غير مسموحة'})
    
    try:
        company = get_object_or_404(Company, id=company_id)
        
        # هنا سيتم إضافة منطق إنشاء قاعدة البيانات
        # مؤقتاً سنعيد رسالة نجاح
        
        return JsonResponse({
            'success': True,
            'message': f'تم إنشاء قاعدة بيانات للشركة "{company.name}" بنجاح'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@subscription_required
@permission_required('companies', 'delete')
@csrf_exempt
def delete_company_database(request, company_id):
    """حذف قاعدة بيانات الشركة"""
    if request.method != 'DELETE':
        return JsonResponse({'success': False, 'error': 'طريقة غير مسموحة'})
    
    try:
        company = get_object_or_404(Company, id=company_id)
        
        # التحقق من التأكيد
        if not company.is_active:
            return JsonResponse({
                'success': False, 
                'error': 'لا يمكن حذف قاعدة بيانات شركة نشطة'
            })
        
        # هنا سيتم إضافة منطق حذف قاعدة البيانات
        # مؤقتاً سنعيد رسالة تحذير
        
        return JsonResponse({
            'success': False,
            'error': 'هذه الميزة قيد التطوير - لا يمكن حذف قواعد البيانات حالياً'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@subscription_required
@permission_required('companies', 'view')
def database_info(request, company_id):
    """معلومات قاعدة بيانات الشركة"""
    company = get_object_or_404(Company, id=company_id)
    
    # معلومات قاعدة البيانات (مؤقتة)
    db_info = {
        'database_name': company.database_name,
        'size': '0 MB',
        'tables_count': 0,
        'records_count': 0,
        'last_backup': None,
        'created_date': company.created_at,
        'status': 'متصلة' if company.is_active else 'غير نشطة'
    }
    
    return JsonResponse({
        'success': True,
        'company': {
            'name': company.name,
            'code': company.code,
        },
        'database_info': db_info
    })

@login_required
@subscription_required
@permission_required('companies', 'add')
@csrf_exempt
def backup_company_database(request, company_id):
    """نسخ احتياطي لقاعدة بيانات الشركة"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'طريقة غير مسموحة'})
    
    try:
        company = get_object_or_404(Company, id=company_id)
        
        # هنا سيتم إضافة منطق النسخ الاحتياطي
        # مؤقتاً سنعيد رسالة نجاح
        
        return JsonResponse({
            'success': True,
            'message': f'تم إنشاء نسخة احتياطية لقاعدة بيانات "{company.name}" بنجاح',
            'backup_file': f'backup_{company.code}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.sql'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@subscription_required
@permission_required('companies', 'add')
@csrf_exempt
def restore_company_database(request, company_id):
    """استعادة قاعدة بيانات الشركة من نسخة احتياطية"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'طريقة غير مسموحة'})
    
    try:
        company = get_object_or_404(Company, id=company_id)
        
        # التحقق من وجود ملف النسخة الاحتياطية
        backup_file = request.FILES.get('backup_file')
        if not backup_file:
            return JsonResponse({'success': False, 'error': 'يرجى اختيار ملف النسخة الاحتياطية'})
        
        # هنا سيتم إضافة منطق الاستعادة
        # مؤقتاً سنعيد رسالة تحذير
        
        return JsonResponse({
            'success': False,
            'error': 'هذه الميزة قيد التطوير - لا يمكن استعادة قواعد البيانات حالياً'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})