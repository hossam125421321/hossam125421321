from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .permission_views import check_user_permission

def require_permission(screen, action='view'):
    """
    Decorator to check if user has specific permission
    Usage: @require_permission('products', 'add')
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            if not check_user_permission(request.user, screen, action):
                messages.error(request, f'ليس لديك صلاحية {action} في {screen}')
                return redirect('dashboard')
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def require_any_permission(*permissions):
    """
    Decorator to check if user has any of the specified permissions
    Usage: @require_any_permission(('products', 'view'), ('sales', 'view'))
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            has_permission = False
            for screen, action in permissions:
                if check_user_permission(request.user, screen, action):
                    has_permission = True
                    break
            
            if not has_permission:
                messages.error(request, 'ليس لديك الصلاحيات المطلوبة للوصول لهذه الصفحة')
                return redirect('dashboard')
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def require_all_permissions(*permissions):
    """
    Decorator to check if user has all of the specified permissions
    Usage: @require_all_permissions(('products', 'view'), ('products', 'edit'))
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            for screen, action in permissions:
                if not check_user_permission(request.user, screen, action):
                    messages.error(request, f'ليس لديك صلاحية {action} في {screen}')
                    return redirect('dashboard')
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def enhanced_permission_required(screen, action='view'):
    """
    Enhanced permission decorator with better error handling
    Usage: @enhanced_permission_required('products', 'add')
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            try:
                if not check_user_permission(request.user, screen, action):
                    messages.error(request, f'ليس لديك صلاحية {action} في {screen}')
                    return redirect('dashboard')
                return view_func(request, *args, **kwargs)
            except Exception as e:
                messages.error(request, f'خطأ في التحقق من الصلاحيات: {str(e)}')
                return redirect('dashboard')
        return _wrapped_view
    return decorator

def company_required(view_func):
    """
    Decorator to ensure user has a company context
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        try:
            # Check if user has company in session or profile
            if not hasattr(request, 'company') or not request.company:
                # Try to get company from session
                company_id = request.session.get('company_id')
                if company_id:
                    from .models import Company
                    try:
                        request.company = Company.objects.get(id=company_id)
                    except Company.DoesNotExist:
                        pass
                
                # If still no company, redirect to login
                if not hasattr(request, 'company') or not request.company:
                    messages.error(request, 'يرجى تسجيل الدخول مع شركة صحيحة')
                    return redirect('login')
            
            return view_func(request, *args, **kwargs)
        except Exception as e:
            messages.error(request, f'خطأ في التحقق من الشركة: {str(e)}')
            return redirect('login')
    return _wrapped_view