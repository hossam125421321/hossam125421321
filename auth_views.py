from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import date, timedelta
import json
from .models import Company, UserProfile

def login_view(request):
    """تسجيل الدخول المتطور"""
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        company_code = request.POST.get('company_code', 'DEFAULT').strip()
        
        if not username or not password:
            return render(request, 'auth/advanced_login.html', {
                'error': 'يرجى إدخال اسم المستخدم وكلمة المرور',
                'companies': Company.objects.filter(is_active=True).order_by('name')
            })
        
        # التحقق من وجود الشركة
        try:
            company = Company.objects.get(code=company_code, is_active=True)
            if not company.is_subscription_active:
                return render(request, 'auth/advanced_login.html', {
                    'error': 'انتهت صلاحية اشتراك الشركة',
                    'companies': Company.objects.filter(is_active=True).order_by('name')
                })
        except Company.DoesNotExist:
            return render(request, 'auth/advanced_login.html', {
                'error': 'كود الشركة غير صحيح',
                'companies': Company.objects.filter(is_active=True).order_by('name')
            })
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            # التحقق من انتماء المستخدم للشركة
            try:
                profile = UserProfile.objects.get(user=user, company=company, is_active=True)
                login(request, user)
                request.session['company_id'] = company.id
                request.session['company_code'] = company.code
                request.session['company_name'] = company.name
                
                # إضافة معلومات إضافية للجلسة
                request.session['user_profile_id'] = profile.id
                if profile.default_branch:
                    request.session['default_branch_id'] = profile.default_branch.id
                if profile.default_warehouse:
                    request.session['default_warehouse_id'] = profile.default_warehouse.id
                
                return redirect('dashboard')
            except UserProfile.DoesNotExist:
                return render(request, 'auth/advanced_login.html', {
                    'error': 'المستخدم غير مسموح له بالدخول لهذه الشركة',
                    'companies': Company.objects.filter(is_active=True).order_by('name')
                })
        else:
            return render(request, 'auth/advanced_login.html', {
                'error': 'اسم المستخدم أو كلمة المرور غير صحيح',
                'companies': Company.objects.filter(is_active=True).order_by('name')
            })
    
    # جلب قائمة الشركات النشطة
    companies = Company.objects.filter(is_active=True).order_by('name')
    
    # إذا كانت هناك شركة واحدة فقط، استخدمها كافتراضية
    default_company = companies.first() if companies.count() == 1 else None
    
    context = {
        'companies': companies,
        'default_company': default_company,
        'show_company_selection': companies.count() > 1,
    }
    return render(request, 'auth/advanced_login.html', context)

def logout_view(request):
    """تسجيل الخروج"""
    logout(request)
    request.session.flush()
    messages.success(request, 'تم تسجيل الخروج بنجاح')
    return redirect('login')

@csrf_exempt
def get_user_companies(request):
    """الحصول على شركات المستخدم"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'طريقة غير مسموحة'})
    
    try:
        data = json.loads(request.body)
        username = data.get('username', '').strip()
        
        if not username:
            return JsonResponse({'success': False, 'error': 'اسم المستخدم مطلوب'})
        
        # البحث عن المستخدم
        try:
            user = User.objects.get(username=username, is_active=True)
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'المستخدم غير موجود'})
        
        # جلب الشركات المرتبطة بالمستخدم
        profiles = UserProfile.objects.filter(
            user=user, 
            is_active=True,
            company__is_active=True
        ).select_related('company')
        
        companies = []
        for profile in profiles:
            company = profile.company
            companies.append({
                'code': company.code,
                'name': company.name,
                'is_subscription_active': company.is_subscription_active,
                'subscription_end': company.subscription_end.strftime('%Y-%m-%d') if company.subscription_end else None
            })
        
        return JsonResponse({
            'success': True,
            'companies': companies,
            'user_full_name': user.get_full_name() or user.username
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})