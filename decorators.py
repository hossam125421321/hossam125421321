from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required

class PermissionManager:
    """مدير الصلاحيات المتقدم"""
    
    @staticmethod
    def has_permission(user, screen, action='view', branch=None, warehouse=None):
        """فحص صلاحية المستخدم"""
        # التحقق من حالة المستخدم
        if not user.is_active:
            return False
        
        # إذا كان المستخدم مدير عام، يحصل على كل الصلاحيات
        if user.is_superuser:
            return True
        
        # فحص الصلاحيات من قاعدة البيانات
        try:
            from .models import Permission, UserProfile
            
            # التحقق من وجود ملف المستخدم وأنه نشط
            profile = UserProfile.objects.filter(user=user, is_active=True).first()
            if not profile:
                return False
            
            # فحص الصلاحية المحددة
            permission = Permission.objects.filter(user=user, screen=screen).first()
            
            if permission:
                # فحص العملية المطلوبة
                action_field = f'can_{action}'
                if hasattr(permission, action_field):
                    has_action_permission = getattr(permission, action_field, False)
                    if not has_action_permission:
                        return False
                
                # فحص صلاحية الفرع
                if branch and permission.branch_access.exists():
                    if not permission.branch_access.filter(id=branch.id).exists():
                        return False
                
                # فحص صلاحية المخزن
                if warehouse and permission.warehouse_access.exists():
                    if not permission.warehouse_access.filter(id=warehouse.id).exists():
                        return False
                
                return True
            else:
                # إذا لم توجد صلاحية محددة، اعط صلاحية العرض فقط
                return action == 'view' and screen in ['dashboard']
                
        except Exception as e:
            # في حالة حدوث خطأ، اعط صلاحية محدودة
            if user.is_staff and action == 'view':
                return True
            return False
    
    @staticmethod
    def get_user_screens(user):
        """جلب قائمة بالشاشات المسموحة للمستخدم"""
        if user.is_superuser:
            return ['dashboard', 'products', 'sales', 'purchases', 'customers', 'suppliers', 'stock', 'accounts', 'reports', 'settings', 'users', 'permissions']
        
        try:
            from .models import Permission
            permissions = Permission.objects.filter(user=user, can_view=True)
            return [perm.screen for perm in permissions]
        except:
            return ['dashboard']

def permission_required(screen, action='view'):
    """ديكوريتر للتحقق من صلاحية المستخدم"""
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        @company_required
        def _wrapped_view(request, *args, **kwargs):
            # التحقق من وجود ملف المستخدم
            try:
                from .models import UserProfile
                profile = UserProfile.objects.get(user=request.user, company=request.company)
                if not profile.is_active:
                    messages.error(request, 'حسابك غير نشط')
                    return redirect('login')
            except UserProfile.DoesNotExist:
                messages.error(request, 'ملف المستخدم غير موجود في هذه الشركة')
                return redirect('login')
            
            # فحص الصلاحية
            if not PermissionManager.has_permission(
                request.user, 
                screen, 
                action, 
                getattr(request, 'current_branch', None),
                getattr(request, 'current_warehouse', None)
            ):
                # تسجيل محاولة الوصول غير المصرح بها
                log_unauthorized_access(request.user, screen, action, request)
                
                messages.error(request, f'ليس لديك صلاحية {get_action_name(action)} في {get_screen_name(screen)}')
                return redirect('dashboard')
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def subscription_required(view_func):
    """ديكوريتر للتحقق من صحة الاشتراك"""
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        try:
            from .models import UserProfile
            profile = UserProfile.objects.get(user=request.user)
            
            if profile.company and not profile.company.is_subscription_active:
                messages.error(request, f'انتهى اشتراك شركة {profile.company.name}، يرجى التجديد')
                return redirect('login')
        except Exception:
            messages.error(request, 'خطأ في التحقق من الاشتراك')
            return redirect('login')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def branch_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not hasattr(request, 'current_branch') or not request.current_branch:
            messages.error(request, 'يجب تحديد فرع افتراضي')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def warehouse_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not hasattr(request, 'current_warehouse') or not request.current_warehouse:
            messages.error(request, 'يجب تحديد مخزن افتراضي')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def company_required(view_func):
    """ديكوريتر للتحقق من وجود شركة للمستخدم"""
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not hasattr(request, 'company') or not request.company:
            messages.error(request, 'يجب ربط المستخدم بشركة')
            return redirect('login')
        
        # فحص صحة الاشتراك
        if not request.company.is_subscription_active:
            messages.error(request, f'انتهى اشتراك شركة {request.company.name}، يرجى التجديد')
            return redirect('login')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def log_unauthorized_access(user, screen, action, request):
    """تسجيل محاولة وصول غير مصرح بها"""
    try:
        import logging
        logger = logging.getLogger('audit')
        
        ip_address = get_client_ip(request)
        company_name = request.session.get('company_name', 'Unknown')
        
        logger.warning(f'UNAUTHORIZED_ACCESS: User={user.username}, Screen={screen}, Action={action}, Company={company_name}, IP={ip_address}')
    except Exception:
        pass

def get_client_ip(request):
    """جلب عنوان IP الخاص بالعميل"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def get_action_name(action):
    """ترجمة اسم العملية إلى العربية"""
    action_names = {
        'view': 'عرض',
        'add': 'إضافة',
        'edit': 'تعديل',
        'delete': 'حذف',
        'confirm': 'تأكيد',
        'print': 'طباعة',
        'export': 'تصدير',
    }
    return action_names.get(action, action)

def get_screen_name(screen):
    """ترجمة اسم الشاشة إلى العربية"""
    screen_names = {
        'dashboard': 'لوحة التحكم',
        'products': 'المنتجات',
        'sales': 'المبيعات',
        'purchases': 'المشتريات',
        'customers': 'العملاء',
        'suppliers': 'الموردين',
        'stock': 'المخزون',
        'accounts': 'الحسابات',
        'reports': 'التقارير',
        'settings': 'الإعدادات',
        'users': 'المستخدمين',
        'permissions': 'الصلاحيات',
        'companies': 'الشركات',
        'branches': 'الفروع',
        'warehouses': 'المخازن',
    }
    return screen_names.get(screen, screen)