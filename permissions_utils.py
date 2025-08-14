# -*- coding: utf-8 -*-
"""
أدوات إدارة الصلاحيات
"""

# الشاشات المتاحة في النظام
AVAILABLE_SCREENS = {
    'dashboard': 'لوحة التحكم',
    'products': 'المنتجات',
    'customers': 'العملاء',
    'suppliers': 'الموردين',
    'sales': 'المبيعات',
    'purchases': 'المشتريات',
    'stock': 'المخزون',
    'accounts': 'الحسابات',
    'reports': 'التقارير',
    'settings': 'الإعدادات',
    'users': 'المستخدمين',
    'permissions': 'الصلاحيات',
    'branches': 'الفروع',
    'warehouses': 'المخازن',
    'pos': 'نقاط البيع',
    'attendance': 'الحضور والانصراف',
    'salaries': 'الرواتب',
    'sales_reps': 'مناديب المبيعات',
    'manufacturing': 'التصنيع',
    'companies': 'الشركات'
}

# الإجراءات المتاحة
AVAILABLE_ACTIONS = {
    'view': 'عرض',
    'add': 'إضافة',
    'edit': 'تعديل',
    'delete': 'حذف',
    'confirm': 'تأكيد',
    'print': 'طباعة',
    'export': 'تصدير'
}

def check_user_permission(user, screen, action):
    """
    فحص صلاحية المستخدم
    """
    # المدير العام له جميع الصلاحيات
    if user.is_superuser:
        return True
    
    # فحص الصلاحية من قاعدة البيانات
    try:
        from .models import Permission
        permission = Permission.objects.filter(
            user=user,
            screen=screen
        ).first()
        
        if permission:
            return getattr(permission, f'can_{action}', False)
    except:
        pass
    
    return False

def get_user_screens(user):
    """
    الحصول على الشاشات المتاحة للمستخدم
    """
    if user.is_superuser:
        return AVAILABLE_SCREENS
    
    user_screens = {}
    try:
        from .models import Permission
        permissions = Permission.objects.filter(user=user, can_view=True)
        for permission in permissions:
            if permission.screen in AVAILABLE_SCREENS:
                user_screens[permission.screen] = AVAILABLE_SCREENS[permission.screen]
    except:
        pass
    
    return user_screens

def create_default_permissions(user, screens=None):
    """
    إنشاء صلاحيات افتراضية للمستخدم
    """
    if screens is None:
        screens = ['dashboard', 'products', 'customers', 'sales']
    
    try:
        from .models import Permission, Company
        company = Company.objects.first()
        
        for screen in screens:
            Permission.objects.get_or_create(
                user=user,
                screen=screen,
                company=company,
                defaults={
                    'can_view': True,
                    'can_add': False,
                    'can_edit': False,
                    'can_delete': False,
                    'can_confirm': False,
                    'can_print': True,
                    'can_export': False,
                    'created_by': user
                }
            )
    except Exception as e:
        print(f"خطأ في إنشاء الصلاحيات: {e}")