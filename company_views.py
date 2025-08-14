from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import date, timedelta
from .models import Company, Branch, Warehouse, UserProfile, User
from .decorators import permission_required, subscription_required

@login_required
@subscription_required
@permission_required('companies', 'view')
def companies_list(request):
    """قائمة الشركات"""
    companies = Company.objects.all().order_by('-created_at')
    
    # فلترة بالبحث
    search = request.GET.get('search', '')
    if search:
        companies = companies.filter(
            Q(name__icontains=search) |
            Q(code__icontains=search) |
            Q(database_name__icontains=search)
        )
    
    # إحصائيات
    stats = {
        'total_companies': Company.objects.count(),
        'active_companies': Company.objects.filter(is_active=True).count(),
        'inactive_companies': Company.objects.filter(is_active=False).count(),
        'expired_subscriptions': Company.objects.filter(subscription_end__lt=date.today()).count(),
    }
    
    context = {
        'companies': companies,
        'search': search,
        'stats': stats,
    }
    return render(request, 'companies.html', context)

@login_required
@subscription_required
@permission_required('companies', 'add')
def add_company(request):
    """إضافة شركة جديدة"""
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            code = request.POST.get('code')
            database_name = request.POST.get('database_name')
            address = request.POST.get('address', '')
            phone = request.POST.get('phone', '')
            email = request.POST.get('email', '')
            subscription_type = request.POST.get('subscription_type', 'monthly')
            subscription_end = request.POST.get('subscription_end')
            
            # التحقق من البيانات المطلوبة
            if not name or not code or not database_name:
                messages.error(request, 'يرجى ملء جميع الحقول المطلوبة')
                return redirect('add_company')
            
            # التحقق من عدم تكرار الكود
            if Company.objects.filter(code=code).exists():
                messages.error(request, f'كود الشركة "{code}" موجود بالفعل')
                return redirect('add_company')
            
            # التحقق من عدم تكرار اسم قاعدة البيانات
            if Company.objects.filter(database_name=database_name).exists():
                messages.error(request, f'اسم قاعدة البيانات "{database_name}" موجود بالفعل')
                return redirect('add_company')
            
            # تحويل تاريخ انتهاء الاشتراك
            if subscription_end:
                from datetime import datetime
                subscription_end = datetime.strptime(subscription_end, '%Y-%m-%d').date()
            else:
                # تاريخ افتراضي (سنة من الآن)
                subscription_end = date.today() + timedelta(days=365)
            
            # إنشاء الشركة
            company = Company.objects.create(
                name=name,
                code=code,
                database_name=database_name,
                address=address,
                phone=phone,
                email=email,
                subscription_type=subscription_type,
                subscription_end=subscription_end,
                logo=request.FILES.get('logo'),
                is_active=True
            )
            
            messages.success(request, f'تم إضافة الشركة "{name}" بنجاح')
            
            if request.headers.get('Content-Type') == 'application/json':
                return JsonResponse({
                    'success': True, 
                    'message': f'تم إضافة الشركة "{name}" بنجاح',
                    'company_id': company.id
                })
            
            return redirect('companies')
            
        except Exception as e:
            messages.error(request, f'خطأ: {str(e)}')
            if request.headers.get('Content-Type') == 'application/json':
                return JsonResponse({'success': False, 'message': str(e)})
    
    context = {
        'subscription_types': [
            ('monthly', 'شهري'),
            ('yearly', 'سنوي')
        ],
        'today': date.today().strftime('%Y-%m-%d'),
    }
    return render(request, 'add_company.html', context)

@login_required
@subscription_required
@permission_required('companies', 'delete')
@csrf_exempt
def delete_company(request, company_id):
    """حذف شركة"""
    if request.method != 'DELETE':
        return JsonResponse({'success': False, 'error': 'طريقة غير مسموحة'})
    
    try:
        company = get_object_or_404(Company, id=company_id)
        company_name = company.name
        
        # التحقق من عدم وجود مستخدمين مرتبطين
        if UserProfile.objects.filter(company=company).exists():
            return JsonResponse({
                'success': False, 
                'error': 'لا يمكن حذف الشركة لوجود مستخدمين مرتبطين بها'
            })
        
        # التحقق من عدم وجود فروع
        if Branch.objects.filter(company=company).exists():
            return JsonResponse({
                'success': False, 
                'error': 'لا يمكن حذف الشركة لوجود فروع مرتبطة بها'
            })
        
        company.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'تم حذف الشركة "{company_name}" بنجاح'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@subscription_required
@permission_required('companies', 'view')
def company_details(request, company_id):
    """تفاصيل الشركة"""
    company = get_object_or_404(Company, id=company_id)
    
    # إحصائيات الشركة
    branches_count = Branch.objects.filter(company=company).count()
    warehouses_count = Warehouse.objects.filter(branch__company=company).count()
    users_count = UserProfile.objects.filter(company=company).count()
    
    # الفروع
    branches = Branch.objects.filter(company=company).select_related('manager')
    
    # المستخدمين
    users = UserProfile.objects.filter(company=company).select_related('user')
    
    # حالة الاشتراك
    days_remaining = (company.subscription_end - date.today()).days if company.subscription_end else 0
    subscription_status = 'نشط' if company.is_subscription_active else 'منتهي'
    
    context = {
        'company': company,
        'branches': branches,
        'users': users,
        'stats': {
            'branches_count': branches_count,
            'warehouses_count': warehouses_count,
            'users_count': users_count,
            'days_remaining': days_remaining,
            'subscription_status': subscription_status,
        }
    }
    return render(request, 'company_details.html', context)