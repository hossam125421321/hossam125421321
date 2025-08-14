# -*- coding: utf-8 -*-
"""
Views إدارة الصلاحيات المحسنة
توفر واجهات متقدمة لإدارة صلاحيات المستخدمين
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.utils import timezone
from .permissions_system import PermissionSystem, PermissionAudit
from .permission_decorators import (
    enhanced_permission_required, 
    subscription_required, 
    company_required,
    permission_audit_log
)
from .models import Permission, Company, Branch, Warehouse, UserProfile
import json
import logging

logger = logging.getLogger(__name__)

@login_required
@subscription_required
@company_required
@enhanced_permission_required('permissions', 'view')
def permissions_dashboard(request):
    """لوحة تحكم الصلاحيات الرئيسية"""
    company = getattr(request, 'company', None)
    
    # إحصائيات عامة
    stats = {
        'total_users': User.objects.filter(is_active=True).count(),
        'users_with_permissions': Permission.objects.values('user').distinct().count(),
        'total_screens': len(PermissionSystem.AVAILABLE_SCREENS),
        'permission_groups': len(PermissionSystem.PERMISSION_GROUPS),
        'company_users': UserProfile.objects.filter(company=company, is_active=True).count() if company else 0
    }
    
    # المستخدمون الأكثر نشاطاً
    active_users = User.objects.filter(
        is_active=True,
        last_login__isnull=False
    ).order_by('-last_login')[:5]
    
    # الصلاحيات الحديثة
    recent_permissions = Permission.objects.select_related('user').order_by('-created_at')[:10]
    
    # توزيع الصلاحيات حسب الشاشات
    screen_distribution = {}
    for screen_key, screen_name in PermissionSystem.AVAILABLE_SCREENS.items():
        count = Permission.objects.filter(screen=screen_key, can_view=True).count()
        screen_distribution[screen_name] = count
    
    context = {
        'stats': stats,
        'active_users': active_users,
        'recent_permissions': recent_permissions,
        'screen_distribution': screen_distribution,
        'permission_groups': PermissionSystem.PERMISSION_GROUPS,
        'available_screens': PermissionSystem.AVAILABLE_SCREENS,
        'available_actions': PermissionSystem.AVAILABLE_ACTIONS,
    }
    
    return render(request, 'permissions/dashboard.html', context)

@login_required
@subscription_required
@company_required
@enhanced_permission_required('permissions', 'view')
def users_permissions_list(request):
    """قائمة صلاحيات المستخدمين"""
    company = getattr(request, 'company', None)
    
    # فلترة المستخدمين
    search = request.GET.get('search', '')
    group_filter = request.GET.get('group', '')
    status_filter = request.GET.get('status', 'active')
    
    # جلب المستخدمين
    users_query = User.objects.all()
    
    if search:
        users_query = users_query.filter(
            Q(username__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search)
        )
    
    if status_filter == 'active':
        users_query = users_query.filter(is_active=True)
    elif status_filter == 'inactive':
        users_query = users_query.filter(is_active=False)
    
    # فلترة حسب الشركة
    if company:
        user_profiles = UserProfile.objects.filter(company=company, is_active=True)
        user_ids = user_profiles.values_list('user_id', flat=True)
        users_query = users_query.filter(id__in=user_ids)
    
    users_query = users_query.order_by('username')
    
    # تحضير بيانات المستخدمين مع صلاحياتهم
    users_with_permissions = []
    for user in users_query:
        user_permissions = PermissionSystem.get_user_permissions(user, company)
        accessible_screens = len([s for s, a in user_permissions.items() if 'view' in a])
        
        # تحديد مجموعة الصلاحيات المحتملة
        detected_group = detect_user_permission_group(user, company)
        
        users_with_permissions.append({
            'user': user,
            'permissions_count': len(user_permissions),
            'accessible_screens': accessible_screens,
            'detected_group': detected_group,
            'last_login': user.last_login,
            'is_superuser': user.is_superuser
        })
    
    # تطبيق فلتر المجموعة
    if group_filter:
        users_with_permissions = [
            u for u in users_with_permissions 
            if u['detected_group'] == group_filter
        ]
    
    # تقسيم الصفحات
    paginator = Paginator(users_with_permissions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'group_filter': group_filter,
        'status_filter': status_filter,
        'permission_groups': PermissionSystem.PERMISSION_GROUPS,
        'total_users': len(users_with_permissions),
    }
    
    return render(request, 'permissions/users_list.html', context)

@login_required
@subscription_required
@company_required
@enhanced_permission_required('permissions', 'view')
def user_permissions_detail(request, user_id):
    """تفاصيل صلاحيات مستخدم معين"""
    user = get_object_or_404(User, id=user_id)
    company = getattr(request, 'company', None)
    
    # جلب ملخص الصلاحيات
    permission_summary = PermissionSystem.get_permission_summary(user, company)
    
    # جلب الصلاحيات التفصيلية
    permissions = Permission.objects.filter(user=user)
    if company:
        permissions = permissions.filter(
            Q(company=company) | Q(company__isnull=True)
        )
    
    # تجميع الصلاحيات حسب الشاشة
    permissions_by_screen = {}
    for permission in permissions:
        screen_name = PermissionSystem.AVAILABLE_SCREENS.get(permission.screen, permission.screen)
        
        actions = []
        if permission.can_view: actions.append('عرض')
        if permission.can_add: actions.append('إضافة')
        if permission.can_edit: actions.append('تعديل')
        if permission.can_delete: actions.append('حذف')
        if permission.can_confirm: actions.append('تأكيد')
        if permission.can_print: actions.append('طباعة')
        if permission.can_export: actions.append('تصدير')
        
        permissions_by_screen[screen_name] = {
            'permission': permission,
            'actions': actions,
            'branches': list(permission.branch_access.all()),
            'warehouses': list(permission.warehouse_access.all())
        }
    
    # الشاشات غير المتاحة
    available_screens = set(PermissionSystem.AVAILABLE_SCREENS.keys())
    user_screens = set(p.screen for p in permissions)
    missing_screens = available_screens - user_screens
    
    context = {
        'target_user': user,
        'permission_summary': permission_summary,
        'permissions_by_screen': permissions_by_screen,
        'missing_screens': missing_screens,
        'available_screens': PermissionSystem.AVAILABLE_SCREENS,
        'available_actions': PermissionSystem.AVAILABLE_ACTIONS,
        'permission_groups': PermissionSystem.PERMISSION_GROUPS,
        'branches': Branch.objects.filter(company=company) if company else [],
        'warehouses': Warehouse.objects.filter(company=company) if company else [],
    }
    
    return render(request, 'permissions/user_detail.html', context)

@login_required
@subscription_required
@company_required
@enhanced_permission_required('permissions', 'edit')
@permission_audit_log('تعديل صلاحيات المستخدم')
def edit_user_permissions(request, user_id):
    """تعديل صلاحيات مستخدم"""
    user = get_object_or_404(User, id=user_id)
    company = getattr(request, 'company', None)
    
    if request.method == 'POST':
        try:
            # جلب البيانات من النموذج
            permissions_data = {}
            
            for screen in PermissionSystem.AVAILABLE_SCREENS.keys():
                screen_permissions = []
                
                for action in PermissionSystem.AVAILABLE_ACTIONS.keys():
                    field_name = f"{screen}_{action}"
                    if request.POST.get(field_name) == 'on':
                        screen_permissions.append(action)
                
                if screen_permissions:
                    permissions_data[screen] = screen_permissions
            
            # حذف الصلاحيات الحالية
            existing_permissions = Permission.objects.filter(user=user)
            if company:
                existing_permissions = existing_permissions.filter(company=company)
            existing_permissions.delete()
            
            # إضافة الصلاحيات الجديدة
            for screen, actions in permissions_data.items():
                # جلب الفروع والمخازن المحددة
                branches = request.POST.getlist(f"{screen}_branches")
                warehouses = request.POST.getlist(f"{screen}_warehouses")
                
                success = PermissionSystem.create_custom_permission(
                    user=user,
                    screen=screen,
                    actions=actions,
                    company=company,
                    branches=Branch.objects.filter(id__in=branches) if branches else None,
                    warehouses=Warehouse.objects.filter(id__in=warehouses) if warehouses else None
                )
                
                if not success:
                    logger.error(f"Failed to create permission for user {user.username}, screen {screen}")
            
            # تسجيل التغيير
            PermissionAudit.log_permission_change(
                user=user,
                changed_by=request.user,
                action='modified',
                details={
                    'screens_modified': list(permissions_data.keys()),
                    'total_permissions': len(permissions_data)
                },
                company=company
            )
            
            messages.success(request, f'تم تحديث صلاحيات المستخدم {user.get_full_name() or user.username} بنجاح')
            return redirect('user_permissions_detail', user_id=user.id)
            
        except Exception as e:
            logger.error(f"Error updating user permissions: {e}")
            messages.error(request, f'خطأ في تحديث الصلاحيات: {str(e)}')
    
    # جلب الصلاحيات الحالية
    current_permissions = {}
    permissions = Permission.objects.filter(user=user)
    if company:
        permissions = permissions.filter(
            Q(company=company) | Q(company__isnull=True)
        )
    
    for permission in permissions:
        current_permissions[permission.screen] = {
            'can_view': permission.can_view,
            'can_add': permission.can_add,
            'can_edit': permission.can_edit,
            'can_delete': permission.can_delete,
            'can_confirm': permission.can_confirm,
            'can_print': permission.can_print,
            'can_export': permission.can_export,
            'branches': list(permission.branch_access.values_list('id', flat=True)),
            'warehouses': list(permission.warehouse_access.values_list('id', flat=True))
        }
    
    context = {
        'target_user': user,
        'current_permissions': current_permissions,
        'available_screens': PermissionSystem.AVAILABLE_SCREENS,
        'available_actions': PermissionSystem.AVAILABLE_ACTIONS,
        'branches': Branch.objects.filter(company=company) if company else [],
        'warehouses': Warehouse.objects.filter(company=company) if company else [],
    }
    
    return render(request, 'permissions/edit_user.html', context)

@login_required
@subscription_required
@company_required
@enhanced_permission_required('permissions', 'edit')
@csrf_exempt
def assign_permission_group(request):
    """تعيين مجموعة صلاحيات لمستخدم"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'طريقة غير مسموحة'})
    
    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')
        group_name = data.get('group_name')
        
        if not user_id or not group_name:
            return JsonResponse({'success': False, 'error': 'بيانات غير مكتملة'})
        
        user = get_object_or_404(User, id=user_id)
        company = getattr(request, 'company', None)
        
        # تعيين مجموعة الصلاحيات
        success = PermissionSystem.assign_permission_group(user, group_name, company)
        
        if success:
            # تسجيل التغيير
            group_info = PermissionSystem.PERMISSION_GROUPS[group_name]
            PermissionAudit.log_permission_change(
                user=user,
                changed_by=request.user,
                action='group_assigned',
                details={
                    'group_name': group_name,
                    'group_display_name': group_info['name'],
                    'screens_count': len(group_info['permissions'])
                },
                company=company
            )
            
            return JsonResponse({
                'success': True,
                'message': f'تم تعيين مجموعة "{group_info["name"]}" للمستخدم {user.get_full_name() or user.username}'
            })
        else:
            return JsonResponse({'success': False, 'error': 'فشل في تعيين مجموعة الصلاحيات'})
            
    except Exception as e:
        logger.error(f"Error assigning permission group: {e}")
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@subscription_required
@company_required
@enhanced_permission_required('permissions', 'edit')
@csrf_exempt
def quick_permission_toggle(request):
    """تبديل صلاحية سريع"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'طريقة غير مسموحة'})
    
    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')
        screen = data.get('screen')
        action = data.get('action')
        enabled = data.get('enabled', False)
        
        user = get_object_or_404(User, id=user_id)
        company = getattr(request, 'company', None)
        
        # جلب أو إنشاء الصلاحية
        permission, created = Permission.objects.get_or_create(
            user=user,
            screen=screen,
            company=company,
            defaults={
                'can_view': False,
                'can_add': False,
                'can_edit': False,
                'can_delete': False,
                'can_confirm': False,
                'can_print': False,
                'can_export': False
            }
        )
        
        # تحديث الصلاحية
        action_field = f'can_{action}'
        if hasattr(permission, action_field):
            setattr(permission, action_field, enabled)
            permission.save()
            
            # مسح الكاش
            PermissionSystem.clear_user_permissions_cache(user.id, company.id if company else None)
            
            # تسجيل التغيير
            PermissionAudit.log_permission_change(
                user=user,
                changed_by=request.user,
                action='permission_toggled',
                details={
                    'screen': screen,
                    'action': action,
                    'enabled': enabled
                },
                company=company
            )
            
            screen_name = PermissionSystem.AVAILABLE_SCREENS.get(screen, screen)
            action_name = PermissionSystem.AVAILABLE_ACTIONS.get(action, action)
            status = 'تم تفعيل' if enabled else 'تم إلغاء'
            
            return JsonResponse({
                'success': True,
                'message': f'{status} صلاحية {action_name} في {screen_name} للمستخدم {user.username}'
            })
        else:
            return JsonResponse({'success': False, 'error': 'عملية غير صحيحة'})
            
    except Exception as e:
        logger.error(f"Error toggling permission: {e}")
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@subscription_required
@company_required
@enhanced_permission_required('permissions', 'view')
def permission_groups_list(request):
    """قائمة مجموعات الصلاحيات"""
    context = {
        'permission_groups': PermissionSystem.PERMISSION_GROUPS,
        'available_screens': PermissionSystem.AVAILABLE_SCREENS,
        'available_actions': PermissionSystem.AVAILABLE_ACTIONS,
    }
    
    return render(request, 'permissions/groups_list.html', context)

@login_required
@subscription_required
@company_required
@enhanced_permission_required('permissions', 'export')
def export_user_permissions(request, user_id):
    """تصدير صلاحيات مستخدم"""
    user = get_object_or_404(User, id=user_id)
    company = getattr(request, 'company', None)
    
    try:
        permissions_data = PermissionSystem.export_user_permissions(user, company)
        
        response = JsonResponse(permissions_data, json_dumps_params={'ensure_ascii': False, 'indent': 2})
        response['Content-Disposition'] = f'attachment; filename="permissions_{user.username}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.json"'
        
        return response
        
    except Exception as e:
        logger.error(f"Error exporting user permissions: {e}")
        messages.error(request, f'خطأ في تصدير الصلاحيات: {str(e)}')
        return redirect('user_permissions_detail', user_id=user_id)

@login_required
@subscription_required
@company_required
@enhanced_permission_required('permissions', 'add')
def import_user_permissions(request):
    """استيراد صلاحيات مستخدم"""
    if request.method == 'POST':
        try:
            uploaded_file = request.FILES.get('permissions_file')
            if not uploaded_file:
                messages.error(request, 'يرجى اختيار ملف')
                return redirect('import_user_permissions')
            
            # قراءة الملف
            file_content = uploaded_file.read().decode('utf-8')
            permissions_data = json.loads(file_content)
            
            # استيراد الصلاحيات
            success = PermissionSystem.import_user_permissions(permissions_data)
            
            if success:
                user_id = permissions_data.get('user_id')
                username = permissions_data.get('username')
                messages.success(request, f'تم استيراد صلاحيات المستخدم {username} بنجاح')
                
                if user_id:
                    return redirect('user_permissions_detail', user_id=user_id)
            else:
                messages.error(request, 'فشل في استيراد الصلاحيات')
                
        except json.JSONDecodeError:
            messages.error(request, 'ملف JSON غير صحيح')
        except Exception as e:
            logger.error(f"Error importing user permissions: {e}")
            messages.error(request, f'خطأ في استيراد الصلاحيات: {str(e)}')
    
    return render(request, 'permissions/import.html')

@login_required
@subscription_required
@company_required
@enhanced_permission_required('permissions', 'view')
def permissions_audit_log(request):
    """سجل مراجعة الصلاحيات"""
    # هذه الدالة تحتاج إلى تطبيق نظام تسجيل متقدم
    # يمكن تطويرها لاحقاً لعرض سجلات التغييرات
    
    context = {
        'audit_logs': [],  # سيتم تطويرها لاحقاً
        'date_range': 30,
    }
    
    return render(request, 'permissions/audit_log.html', context)

def detect_user_permission_group(user, company=None):
    """تحديد مجموعة الصلاحيات المحتملة للمستخدم"""
    if user.is_superuser:
        return 'admin'
    
    user_permissions = PermissionSystem.get_user_permissions(user, company)
    
    # مقارنة مع كل مجموعة
    best_match = None
    best_score = 0
    
    for group_name, group_info in PermissionSystem.PERMISSION_GROUPS.items():
        score = 0
        total_screens = len(group_info['permissions'])
        
        for screen, required_actions in group_info['permissions'].items():
            user_screen_actions = user_permissions.get(screen, [])
            matching_actions = len(set(required_actions) & set(user_screen_actions))
            if matching_actions > 0:
                score += matching_actions / len(required_actions)
        
        final_score = score / total_screens if total_screens > 0 else 0
        
        if final_score > best_score and final_score > 0.5:  # على الأقل 50% تطابق
            best_score = final_score
            best_match = group_name
    
    return best_match or 'custom'