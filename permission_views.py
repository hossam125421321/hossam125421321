from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from .models import Permission, Company
from .permissions_utils import check_user_permission, AVAILABLE_SCREENS, AVAILABLE_ACTIONS
import json
import logging

logger = logging.getLogger(__name__)

def is_admin_or_has_permission(user):
    """Check if user is admin or has permissions management access"""
    return user.is_superuser or user.groups.filter(name='Administrators').exists()

@login_required
@user_passes_test(is_admin_or_has_permission)
def permissions_dashboard(request):
    """Dashboard for permissions management"""
    try:
        # Get current company
        company = getattr(request.user, 'userprofile', None)
        if company:
            company = company.company
        else:
            company = Company.objects.first()
        
        # Statistics
        total_users = User.objects.filter(is_active=True).count()
        total_screens = len(AVAILABLE_SCREENS)
        users_with_permissions = Permission.objects.values('user').distinct().count()
        
        # Active users (logged in within last 30 days)
        from datetime import timedelta
        thirty_days_ago = timezone.now() - timedelta(days=30)
        active_users = User.objects.filter(
            last_login__gte=thirty_days_ago,
            is_active=True
        ).order_by('-last_login')[:5]
        
        # Recent permissions
        recent_permissions = Permission.objects.select_related('user').order_by('-created_at')[:10]
        
        # Screen distribution
        screen_distribution = {}
        for screen_key, screen_name in AVAILABLE_SCREENS.items():
            count = Permission.objects.filter(screen=screen_key).count()
            screen_distribution[screen_name] = count
        
        # Permission groups (predefined templates)
        permission_groups = {
            'admin': {
                'name': 'مدير النظام',
                'description': 'صلاحيات كاملة لجميع الشاشات',
                'permissions': {screen: list(AVAILABLE_ACTIONS.keys()) for screen in AVAILABLE_SCREENS.keys()}
            },
            'manager': {
                'name': 'مدير',
                'description': 'صلاحيات إدارية محدودة',
                'permissions': {
                    'dashboard': ['view'],
                    'products': ['view', 'add', 'edit'],
                    'sales': ['view', 'add', 'edit', 'print'],
                    'customers': ['view', 'add', 'edit'],
                    'reports': ['view', 'export']
                }
            },
            'employee': {
                'name': 'موظف',
                'description': 'صلاحيات أساسية للعمل اليومي',
                'permissions': {
                    'dashboard': ['view'],
                    'products': ['view'],
                    'sales': ['view', 'add'],
                    'customers': ['view']
                }
            }
        }
        
        context = {
            'stats': {
                'total_users': total_users,
                'total_screens': total_screens,
                'permission_groups': len(permission_groups),
                'users_with_permissions': users_with_permissions
            },
            'active_users': active_users,
            'recent_permissions': recent_permissions,
            'screen_distribution': screen_distribution,
            'permission_groups': permission_groups,
            'available_screens': AVAILABLE_SCREENS,
            'available_actions': AVAILABLE_ACTIONS
        }
        
        return render(request, 'permissions/dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Error in permissions dashboard: {str(e)}")
        messages.error(request, 'حدث خطأ في تحميل لوحة تحكم الصلاحيات')
        return redirect('dashboard')

@login_required
@user_passes_test(is_admin_or_has_permission)
def users_permissions_list(request):
    """List all users with their permissions"""
    try:
        # Get current company
        company = getattr(request.user, 'userprofile', None)
        if company:
            company = company.company
        else:
            company = Company.objects.first()
        
        # Get all active users
        users = User.objects.filter(is_active=True).order_by('first_name', 'username')
        
        # Get all permissions for these users
        user_permissions = {}
        permissions = Permission.objects.filter(
            user__in=users,
            company=company
        ).select_related('user')
        
        for permission in permissions:
            user_id = permission.user.id
            if user_id not in user_permissions:
                user_permissions[user_id] = {}
            
            screen = permission.screen
            if screen not in user_permissions[user_id]:
                user_permissions[user_id][screen] = []
            
            # Add all available actions for this permission
            actions = []
            if permission.can_view: actions.append('view')
            if permission.can_add: actions.append('add')
            if permission.can_edit: actions.append('edit')
            if permission.can_delete: actions.append('delete')
            if permission.can_confirm: actions.append('confirm')
            if permission.can_print: actions.append('print')
            if permission.can_export: actions.append('export')
            
            user_permissions[user_id][screen] = actions
        
        # Statistics
        total_users = users.count()
        total_screens = len(AVAILABLE_SCREENS)
        active_users = users.filter(last_login__isnull=False).count()
        
        context = {
            'users': users,
            'user_permissions': user_permissions,
            'available_screens': AVAILABLE_SCREENS,
            'available_actions': AVAILABLE_ACTIONS,
            'total_users': total_users,
            'total_screens': total_screens,
            'active_users': active_users
        }
        
        return render(request, 'permissions/users_list.html', context)
        
    except Exception as e:
        logger.error(f"Error in users permissions list: {str(e)}")
        messages.error(request, 'حدث خطأ في تحميل قائمة صلاحيات المستخدمين')
        return redirect('permissions_dashboard')

@login_required
@user_passes_test(is_admin_or_has_permission)
@require_http_methods(["POST"])
def update_user_permissions(request):
    """Update user permissions via AJAX"""
    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')
        permissions_data = data.get('permissions', {})
        
        if not user_id:
            return JsonResponse({'success': False, 'error': 'معرف المستخدم مطلوب'})
        
        user = get_object_or_404(User, id=user_id)
        
        # Get current company
        company = getattr(request.user, 'userprofile', None)
        if company:
            company = company.company
        else:
            company = Company.objects.first()
        
        with transaction.atomic():
            # Process each screen's permissions
            for screen, actions in permissions_data.items():
                if screen not in AVAILABLE_SCREENS:
                    continue
                
                # Get or create permission object
                permission, created = Permission.objects.get_or_create(
                    user=user,
                    screen=screen,
                    company=company,
                    defaults={
                        'created_by': request.user
                    }
                )
                
                # Update permission actions
                permission.can_view = actions.get('view', False)
                permission.can_add = actions.get('add', False)
                permission.can_edit = actions.get('edit', False)
                permission.can_delete = actions.get('delete', False)
                permission.can_confirm = actions.get('confirm', False)
                permission.can_print = actions.get('print', False)
                permission.can_export = actions.get('export', False)
                permission.updated_at = timezone.now()
                
                permission.save()
                
                # If no permissions are granted, delete the permission object
                if not any([permission.can_view, permission.can_add, permission.can_edit,
                           permission.can_delete, permission.can_confirm, permission.can_print,
                           permission.can_export]):
                    permission.delete()
        
        # Log the action
        logger.info(f"User {request.user.username} updated permissions for user {user.username}")
        
        return JsonResponse({
            'success': True,
            'message': 'تم حفظ الصلاحيات بنجاح',
            'updated_at': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'بيانات غير صحيحة'})
    except Exception as e:
        logger.error(f"Error updating user permissions: {str(e)}")
        return JsonResponse({'success': False, 'error': 'حدث خطأ في حفظ الصلاحيات'})

@login_required
@user_passes_test(is_admin_or_has_permission)
def user_permissions_detail(request, user_id):
    """Detailed view of a specific user's permissions"""
    try:
        user = get_object_or_404(User, id=user_id)
        
        # Get current company
        company = getattr(request.user, 'userprofile', None)
        if company:
            company = company.company
        else:
            company = Company.objects.first()
        
        # Get user's permissions
        permissions = Permission.objects.filter(
            user=user,
            company=company
        ).order_by('screen')
        
        # Organize permissions by screen
        user_permissions = {}
        for permission in permissions:
            actions = []
            if permission.can_view: actions.append('view')
            if permission.can_add: actions.append('add')
            if permission.can_edit: actions.append('edit')
            if permission.can_delete: actions.append('delete')
            if permission.can_confirm: actions.append('confirm')
            if permission.can_print: actions.append('print')
            if permission.can_export: actions.append('export')
            
            user_permissions[permission.screen] = {
                'actions': actions,
                'permission_obj': permission
            }
        
        context = {
            'target_user': user,
            'user_permissions': user_permissions,
            'available_screens': AVAILABLE_SCREENS,
            'available_actions': AVAILABLE_ACTIONS
        }
        
        return render(request, 'permissions/user_detail.html', context)
        
    except Exception as e:
        logger.error(f"Error in user permissions detail: {str(e)}")
        messages.error(request, 'حدث خطأ في تحميل تفاصيل صلاحيات المستخدم')
        return redirect('users_permissions_list')

@login_required
@user_passes_test(is_admin_or_has_permission)
def apply_permission_template(request, user_id, template_name):
    """Apply a predefined permission template to a user"""
    try:
        user = get_object_or_404(User, id=user_id)
        
        # Get current company
        company = getattr(request.user, 'userprofile', None)
        if company:
            company = company.company
        else:
            company = Company.objects.first()
        
        # Define permission templates
        templates = {
            'admin': {
                screen: list(AVAILABLE_ACTIONS.keys()) 
                for screen in AVAILABLE_SCREENS.keys()
            },
            'manager': {
                'dashboard': ['view'],
                'products': ['view', 'add', 'edit'],
                'sales': ['view', 'add', 'edit', 'print'],
                'purchases': ['view', 'add', 'edit'],
                'customers': ['view', 'add', 'edit'],
                'suppliers': ['view', 'add', 'edit'],
                'stock': ['view'],
                'reports': ['view', 'export']
            },
            'employee': {
                'dashboard': ['view'],
                'products': ['view'],
                'sales': ['view', 'add'],
                'customers': ['view'],
                'stock': ['view']
            }
        }
        
        if template_name not in templates:
            messages.error(request, 'قالب الصلاحيات غير موجود')
            return redirect('user_permissions_detail', user_id=user_id)
        
        template = templates[template_name]
        
        with transaction.atomic():
            # Clear existing permissions
            Permission.objects.filter(user=user, company=company).delete()
            
            # Apply template permissions
            for screen, actions in template.items():
                if screen not in AVAILABLE_SCREENS:
                    continue
                
                permission = Permission.objects.create(
                    user=user,
                    screen=screen,
                    company=company,
                    can_view='view' in actions,
                    can_add='add' in actions,
                    can_edit='edit' in actions,
                    can_delete='delete' in actions,
                    can_confirm='confirm' in actions,
                    can_print='print' in actions,
                    can_export='export' in actions,
                    created_by=request.user
                )
        
        messages.success(request, f'تم تطبيق قالب "{template_name}" بنجاح')
        logger.info(f"Applied {template_name} template to user {user.username}")
        
        return redirect('user_permissions_detail', user_id=user_id)
        
    except Exception as e:
        logger.error(f"Error applying permission template: {str(e)}")
        messages.error(request, 'حدث خطأ في تطبيق قالب الصلاحيات')
        return redirect('user_permissions_detail', user_id=user_id)

@login_required
@user_passes_test(is_admin_or_has_permission)
def export_permissions(request):
    """Export permissions report"""
    try:
        import csv
        from django.http import HttpResponse
        
        # Get current company
        company = getattr(request.user, 'userprofile', None)
        if company:
            company = company.company
        else:
            company = Company.objects.first()
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="permissions_report.csv"'
        response.write('\ufeff')  # BOM for UTF-8
        
        writer = csv.writer(response)
        
        # Header
        header = ['المستخدم', 'البريد الإلكتروني', 'الشاشة', 'الصلاحيات', 'تاريخ الإنشاء']
        writer.writerow(header)
        
        # Data
        permissions = Permission.objects.filter(company=company).select_related('user').order_by('user__username', 'screen')
        
        for permission in permissions:
            actions = []
            if permission.can_view: actions.append('عرض')
            if permission.can_add: actions.append('إضافة')
            if permission.can_edit: actions.append('تعديل')
            if permission.can_delete: actions.append('حذف')
            if permission.can_confirm: actions.append('تأكيد')
            if permission.can_print: actions.append('طباعة')
            if permission.can_export: actions.append('تصدير')
            
            writer.writerow([
                permission.user.get_full_name() or permission.user.username,
                permission.user.email,
                AVAILABLE_SCREENS.get(permission.screen, permission.screen),
                ', '.join(actions),
                permission.created_at.strftime('%Y-%m-%d %H:%M')
            ])
        
        return response
        
    except Exception as e:
        logger.error(f"Error exporting permissions: {str(e)}")
        messages.error(request, 'حدث خطأ في تصدير التقرير')
        return redirect('users_permissions_list')

def check_user_permission(user, screen, action='view', company=None):
    """Check if user has specific permission"""
    if user.is_superuser:
        return True
    
    try:
        if not company:
            company = getattr(user, 'userprofile', None)
            if company:
                company = company.company
            else:
                company = Company.objects.first()
        
        permission = Permission.objects.get(
            user=user,
            screen=screen,
            company=company
        )
        
        action_map = {
            'view': permission.can_view,
            'add': permission.can_add,
            'edit': permission.can_edit,
            'delete': permission.can_delete,
            'confirm': permission.can_confirm,
            'print': permission.can_print,
            'export': permission.can_export
        }
        
        return action_map.get(action, False)
        
    except Permission.DoesNotExist:
        return action == 'view'  # Default to view permission
    except Exception:
        return False