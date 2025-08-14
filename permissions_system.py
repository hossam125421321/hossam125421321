# -*- coding: utf-8 -*-
"""
نظام إدارة الصلاحيات المتطور
يوفر إدارة شاملة للصلاحيات مع دعم الشركات المتعددة والفروع
"""

from django.contrib.auth.models import User
from django.db import models
from django.core.cache import cache
from django.utils import timezone
from typing import Dict, List, Optional, Tuple
import json
import logging

logger = logging.getLogger(__name__)

class PermissionSystem:
    """نظام إدارة الصلاحيات المتطور"""
    
    # تعريف الشاشات المتاحة
    AVAILABLE_SCREENS = {
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
        'pos': 'نقاط البيع',
        'manufacturing': 'التصنيع',
        'attendance': 'الحضور والانصراف',
        'salaries': 'الرواتب',
        'employees': 'الموظفين',
        'sales_reps': 'مناديب المبيعات'
    }
    
    # تعريف العمليات المتاحة
    AVAILABLE_ACTIONS = {
        'view': 'عرض',
        'add': 'إضافة',
        'edit': 'تعديل',
        'delete': 'حذف',
        'confirm': 'تأكيد',
        'print': 'طباعة',
        'export': 'تصدير'
    }
    
    # مجموعات الصلاحيات المحددة مسبقاً
    PERMISSION_GROUPS = {
        'admin': {
            'name': 'مدير النظام',
            'description': 'صلاحيات كاملة على جميع الشاشات',
            'permissions': {}
        },
        'manager': {
            'name': 'مدير',
            'description': 'صلاحيات إدارية محدودة',
            'permissions': {
                'dashboard': ['view'],
                'products': ['view', 'add', 'edit', 'print', 'export'],
                'sales': ['view', 'add', 'edit', 'confirm', 'print', 'export'],
                'purchases': ['view', 'add', 'edit', 'confirm', 'print', 'export'],
                'customers': ['view', 'add', 'edit', 'print', 'export'],
                'suppliers': ['view', 'add', 'edit', 'print', 'export'],
                'stock': ['view', 'print', 'export'],
                'accounts': ['view', 'print', 'export'],
                'reports': ['view', 'print', 'export'],
                'users': ['view', 'add', 'edit'],
                'employees': ['view', 'add', 'edit'],
                'attendance': ['view', 'add', 'edit', 'export'],
                'salaries': ['view', 'add', 'edit', 'confirm', 'export']
            }
        },
        'cashier': {
            'name': 'كاشير',
            'description': 'صلاحيات نقاط البيع والمبيعات',
            'permissions': {
                'dashboard': ['view'],
                'products': ['view'],
                'sales': ['view', 'add', 'print'],
                'customers': ['view', 'add'],
                'pos': ['view', 'add', 'print'],
                'stock': ['view']
            }
        },
        'sales_rep': {
            'name': 'مندوب مبيعات',
            'description': 'صلاحيات المبيعات والعملاء',
            'permissions': {
                'dashboard': ['view'],
                'products': ['view'],
                'sales': ['view', 'add', 'print'],
                'customers': ['view', 'add', 'edit'],
                'reports': ['view']
            }
        },
        'accountant': {
            'name': 'محاسب',
            'description': 'صلاحيات المحاسبة والتقارير',
            'permissions': {
                'dashboard': ['view'],
                'sales': ['view', 'confirm'],
                'purchases': ['view', 'confirm'],
                'customers': ['view'],
                'suppliers': ['view'],
                'accounts': ['view', 'add', 'edit'],
                'reports': ['view', 'print', 'export'],
                'salaries': ['view', 'add', 'edit', 'confirm']
            }
        },
        'warehouse_keeper': {
            'name': 'أمين مخزن',
            'description': 'صلاحيات إدارة المخزون',
            'permissions': {
                'dashboard': ['view'],
                'products': ['view', 'add', 'edit'],
                'purchases': ['view', 'add'],
                'stock': ['view', 'add', 'edit', 'export'],
                'suppliers': ['view']
            }
        }
    }
    
    @staticmethod
    def get_cache_key(user_id: int, company_id: int = None) -> str:
        """إنشاء مفتاح الكاش للصلاحيات"""
        return f"user_permissions_{user_id}_{company_id or 'global'}"
    
    @staticmethod
    def clear_user_permissions_cache(user_id: int, company_id: int = None):
        """مسح كاش صلاحيات المستخدم"""
        cache_key = PermissionSystem.get_cache_key(user_id, company_id)
        cache.delete(cache_key)
        logger.info(f"Cleared permissions cache for user {user_id}, company {company_id}")
    
    @staticmethod
    def get_user_permissions(user: User, company=None, use_cache: bool = True) -> Dict:
        """جلب صلاحيات المستخدم مع دعم الكاش"""
        if not user or not user.is_active:
            return {}
        
        # إذا كان مدير عام، أعط كل الصلاحيات
        if user.is_superuser:
            return {
                screen: list(PermissionSystem.AVAILABLE_ACTIONS.keys())
                for screen in PermissionSystem.AVAILABLE_SCREENS.keys()
            }
        
        company_id = company.id if company else None
        cache_key = PermissionSystem.get_cache_key(user.id, company_id)
        
        # محاولة جلب الصلاحيات من الكاش
        if use_cache:
            cached_permissions = cache.get(cache_key)
            if cached_permissions is not None:
                return cached_permissions
        
        try:
            from .models import Permission
            
            # جلب صلاحيات المستخدم من قاعدة البيانات
            permissions_query = Permission.objects.filter(user=user)
            if company:
                permissions_query = permissions_query.filter(
                    models.Q(company=company) | models.Q(company__isnull=True)
                )
            
            user_permissions = {}
            for permission in permissions_query:
                screen_permissions = []
                
                if permission.can_view:
                    screen_permissions.append('view')
                if permission.can_add:
                    screen_permissions.append('add')
                if permission.can_edit:
                    screen_permissions.append('edit')
                if permission.can_delete:
                    screen_permissions.append('delete')
                if permission.can_confirm:
                    screen_permissions.append('confirm')
                if permission.can_print:
                    screen_permissions.append('print')
                if permission.can_export:
                    screen_permissions.append('export')
                
                user_permissions[permission.screen] = screen_permissions
            
            # حفظ في الكاش لمدة ساعة
            if use_cache:
                cache.set(cache_key, user_permissions, 3600)
            
            return user_permissions
            
        except Exception as e:
            logger.error(f"Error getting user permissions: {e}")
            return {}
    
    @staticmethod
    def has_permission(user: User, screen: str, action: str = 'view', 
                      company=None, branch=None, warehouse=None) -> bool:
        """فحص صلاحية محددة للمستخدم"""
        if not user or not user.is_active:
            return False
        
        # المدير العام له كل الصلاحيات
        if user.is_superuser:
            return True
        
        # التحقق من وجود الشاشة والعملية
        if screen not in PermissionSystem.AVAILABLE_SCREENS:
            return False
        
        if action not in PermissionSystem.AVAILABLE_ACTIONS:
            return False
        
        try:
            # جلب صلاحيات المستخدم
            user_permissions = PermissionSystem.get_user_permissions(user, company)
            
            # فحص الصلاحية الأساسية
            screen_permissions = user_permissions.get(screen, [])
            if action not in screen_permissions:
                return False
            
            # فحص صلاحيات الفرع والمخزن إذا كانت مطلوبة
            if branch or warehouse:
                from .models import Permission
                
                permission_obj = Permission.objects.filter(
                    user=user, 
                    screen=screen
                ).first()
                
                if permission_obj:
                    # فحص صلاحية الفرع
                    if branch and permission_obj.branch_access.exists():
                        if not permission_obj.branch_access.filter(id=branch.id).exists():
                            return False
                    
                    # فحص صلاحية المخزن
                    if warehouse and permission_obj.warehouse_access.exists():
                        if not permission_obj.warehouse_access.filter(id=warehouse.id).exists():
                            return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking permission: {e}")
            return False
    
    @staticmethod
    def assign_permission_group(user: User, group_name: str, company=None) -> bool:
        """تعيين مجموعة صلاحيات للمستخدم"""
        if group_name not in PermissionSystem.PERMISSION_GROUPS:
            logger.error(f"Permission group '{group_name}' not found")
            return False
        
        try:
            from .models import Permission
            
            group = PermissionSystem.PERMISSION_GROUPS[group_name]
            
            # حذف الصلاحيات الحالية للمستخدم في هذه الشركة
            existing_permissions = Permission.objects.filter(user=user)
            if company:
                existing_permissions = existing_permissions.filter(company=company)
            existing_permissions.delete()
            
            # إضافة الصلاحيات الجديدة
            for screen, actions in group['permissions'].items():
                permission_data = {
                    'user': user,
                    'screen': screen,
                    'can_view': 'view' in actions,
                    'can_add': 'add' in actions,
                    'can_edit': 'edit' in actions,
                    'can_delete': 'delete' in actions,
                    'can_confirm': 'confirm' in actions,
                    'can_print': 'print' in actions,
                    'can_export': 'export' in actions,
                }
                
                if company:
                    permission_data['company'] = company
                
                Permission.objects.create(**permission_data)
            
            # مسح الكاش
            PermissionSystem.clear_user_permissions_cache(user.id, company.id if company else None)
            
            logger.info(f"Assigned permission group '{group_name}' to user {user.username}")
            return True
            
        except Exception as e:
            logger.error(f"Error assigning permission group: {e}")
            return False
    
    @staticmethod
    def create_custom_permission(user: User, screen: str, actions: List[str], 
                                company=None, branches=None, warehouses=None) -> bool:
        """إنشاء صلاحية مخصصة"""
        try:
            from .models import Permission
            
            # التحقق من صحة البيانات
            if screen not in PermissionSystem.AVAILABLE_SCREENS:
                return False
            
            for action in actions:
                if action not in PermissionSystem.AVAILABLE_ACTIONS:
                    return False
            
            # حذف الصلاحية الحالية إن وجدت
            Permission.objects.filter(
                user=user, 
                screen=screen,
                company=company
            ).delete()
            
            # إنشاء الصلاحية الجديدة
            permission_data = {
                'user': user,
                'screen': screen,
                'can_view': 'view' in actions,
                'can_add': 'add' in actions,
                'can_edit': 'edit' in actions,
                'can_delete': 'delete' in actions,
                'can_confirm': 'confirm' in actions,
                'can_print': 'print' in actions,
                'can_export': 'export' in actions,
            }
            
            if company:
                permission_data['company'] = company
            
            permission = Permission.objects.create(**permission_data)
            
            # إضافة صلاحيات الفروع والمخازن
            if branches:
                permission.branch_access.set(branches)
            
            if warehouses:
                permission.warehouse_access.set(warehouses)
            
            # مسح الكاش
            PermissionSystem.clear_user_permissions_cache(user.id, company.id if company else None)
            
            logger.info(f"Created custom permission for user {user.username}, screen {screen}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating custom permission: {e}")
            return False
    
    @staticmethod
    def get_user_accessible_screens(user: User, company=None) -> List[str]:
        """جلب قائمة الشاشات المتاحة للمستخدم"""
        user_permissions = PermissionSystem.get_user_permissions(user, company)
        return [screen for screen, actions in user_permissions.items() if 'view' in actions]
    
    @staticmethod
    def get_permission_summary(user: User, company=None) -> Dict:
        """جلب ملخص صلاحيات المستخدم"""
        user_permissions = PermissionSystem.get_user_permissions(user, company)
        
        summary = {
            'user': {
                'id': user.id,
                'username': user.username,
                'full_name': user.get_full_name() or user.username,
                'is_superuser': user.is_superuser,
                'is_active': user.is_active
            },
            'company': {
                'id': company.id if company else None,
                'name': company.name if company else None
            },
            'screens_count': len(user_permissions),
            'accessible_screens': len([s for s, a in user_permissions.items() if 'view' in a]),
            'permissions': {}
        }
        
        for screen, actions in user_permissions.items():
            summary['permissions'][screen] = {
                'screen_name': PermissionSystem.AVAILABLE_SCREENS.get(screen, screen),
                'actions': actions,
                'actions_names': [PermissionSystem.AVAILABLE_ACTIONS.get(a, a) for a in actions]
            }
        
        return summary
    
    @staticmethod
    def log_permission_check(user: User, screen: str, action: str, 
                           result: bool, company=None, ip_address: str = None):
        """تسجيل فحص الصلاحيات للمراجعة"""
        try:
            log_data = {
                'timestamp': timezone.now().isoformat(),
                'user_id': user.id,
                'username': user.username,
                'screen': screen,
                'action': action,
                'result': result,
                'company_id': company.id if company else None,
                'ip_address': ip_address
            }
            
            if result:
                logger.info(f"PERMISSION_GRANTED: {json.dumps(log_data)}")
            else:
                logger.warning(f"PERMISSION_DENIED: {json.dumps(log_data)}")
                
        except Exception as e:
            logger.error(f"Error logging permission check: {e}")
    
    @staticmethod
    def export_user_permissions(user: User, company=None) -> Dict:
        """تصدير صلاحيات المستخدم للنسخ الاحتياطي"""
        try:
            from .models import Permission
            
            permissions_data = []
            permissions = Permission.objects.filter(user=user)
            
            if company:
                permissions = permissions.filter(company=company)
            
            for permission in permissions:
                perm_data = {
                    'screen': permission.screen,
                    'can_view': permission.can_view,
                    'can_add': permission.can_add,
                    'can_edit': permission.can_edit,
                    'can_delete': permission.can_delete,
                    'can_confirm': permission.can_confirm,
                    'can_print': permission.can_print,
                    'can_export': permission.can_export,
                    'branches': list(permission.branch_access.values_list('id', flat=True)),
                    'warehouses': list(permission.warehouse_access.values_list('id', flat=True)),
                    'created_at': permission.created_at.isoformat() if permission.created_at else None
                }
                permissions_data.append(perm_data)
            
            return {
                'user_id': user.id,
                'username': user.username,
                'company_id': company.id if company else None,
                'export_date': timezone.now().isoformat(),
                'permissions': permissions_data
            }
            
        except Exception as e:
            logger.error(f"Error exporting user permissions: {e}")
            return {}
    
    @staticmethod
    def import_user_permissions(permissions_data: Dict) -> bool:
        """استيراد صلاحيات المستخدم من النسخ الاحتياطي"""
        try:
            from .models import Permission, Branch, Warehouse
            
            user_id = permissions_data.get('user_id')
            company_id = permissions_data.get('company_id')
            
            if not user_id:
                return False
            
            user = User.objects.get(id=user_id)
            company = None
            
            if company_id:
                from .models import Company
                company = Company.objects.get(id=company_id)
            
            # حذف الصلاحيات الحالية
            existing_permissions = Permission.objects.filter(user=user)
            if company:
                existing_permissions = existing_permissions.filter(company=company)
            existing_permissions.delete()
            
            # إضافة الصلاحيات المستوردة
            for perm_data in permissions_data.get('permissions', []):
                permission = Permission.objects.create(
                    user=user,
                    company=company,
                    screen=perm_data['screen'],
                    can_view=perm_data.get('can_view', False),
                    can_add=perm_data.get('can_add', False),
                    can_edit=perm_data.get('can_edit', False),
                    can_delete=perm_data.get('can_delete', False),
                    can_confirm=perm_data.get('can_confirm', False),
                    can_print=perm_data.get('can_print', False),
                    can_export=perm_data.get('can_export', False)
                )
                
                # إضافة صلاحيات الفروع
                branch_ids = perm_data.get('branches', [])
                if branch_ids:
                    branches = Branch.objects.filter(id__in=branch_ids)
                    permission.branch_access.set(branches)
                
                # إضافة صلاحيات المخازن
                warehouse_ids = perm_data.get('warehouses', [])
                if warehouse_ids:
                    warehouses = Warehouse.objects.filter(id__in=warehouse_ids)
                    permission.warehouse_access.set(warehouses)
            
            # مسح الكاش
            PermissionSystem.clear_user_permissions_cache(user.id, company_id)
            
            logger.info(f"Imported permissions for user {user.username}")
            return True
            
        except Exception as e:
            logger.error(f"Error importing user permissions: {e}")
            return False
    
    @classmethod
    def initialize_permission_groups(cls):
        """تهيئة مجموعات الصلاحيات بعد تعريف الكلاس"""
        cls.PERMISSION_GROUPS['admin']['permissions'] = {
            screen: list(cls.AVAILABLE_ACTIONS.keys()) 
            for screen in cls.AVAILABLE_SCREENS.keys()
        }


# تهيئة مجموعات الصلاحيات
PermissionSystem.initialize_permission_groups()


class PermissionAudit:
    """نظام مراجعة الصلاحيات"""
    
    @staticmethod
    def log_permission_change(user: User, changed_by: User, action: str, 
                            details: Dict, company=None):
        """تسجيل تغيير في الصلاحيات"""
        try:
            audit_data = {
                'timestamp': timezone.now().isoformat(),
                'user_id': user.id,
                'username': user.username,
                'changed_by_id': changed_by.id,
                'changed_by_username': changed_by.username,
                'action': action,  # 'granted', 'revoked', 'modified'
                'details': details,
                'company_id': company.id if company else None
            }
            
            logger.info(f"PERMISSION_AUDIT: {json.dumps(audit_data)}")
            
        except Exception as e:
            logger.error(f"Error logging permission change: {e}")
    
    @staticmethod
    def get_user_permission_history(user: User, company=None, days: int = 30) -> List[Dict]:
        """جلب تاريخ تغييرات صلاحيات المستخدم"""
        # هذه الدالة تحتاج إلى تطبيق نظام تسجيل متقدم
        # يمكن تطويرها لاحقاً لجلب السجلات من قاعدة البيانات
        return []