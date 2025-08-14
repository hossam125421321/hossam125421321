from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse
from .permission_views import check_user_permission

class PermissionMiddleware:
    """
    Middleware للتحقق من الصلاحيات تلقائياً
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # URL patterns that require specific permissions
        self.protected_urls = {
            # Products
            'products': ('products', 'view'),
            'add_product': ('products', 'add'),
            'edit_product': ('products', 'edit'),
            'delete_product': ('products', 'delete'),
            'export_products': ('products', 'export'),
            
            # Sales
            'sales': ('sales', 'view'),
            'add_sale': ('sales', 'add'),
            'confirm_invoice': ('sales', 'confirm'),
            'delete_sale': ('sales', 'delete'),
            
            # Purchases
            'purchases': ('purchases', 'view'),
            'add_purchase': ('purchases', 'add'),
            'confirm_purchase': ('purchases', 'confirm'),
            'delete_purchase': ('purchases', 'delete'),
            
            # Customers
            'customers': ('customers', 'view'),
            'add_customer': ('customers', 'add'),
            'edit_customer': ('customers', 'edit'),
            'delete_customer': ('customers', 'delete'),
            
            # Suppliers
            'suppliers': ('suppliers', 'view'),
            'add_supplier': ('suppliers', 'add'),
            'edit_supplier': ('suppliers', 'edit'),
            'delete_supplier': ('suppliers', 'delete'),
            
            # Stock
            'stock': ('stock', 'view'),
            'adjust_stock': ('stock', 'edit'),
            
            # Accounts
            'accounts': ('accounts', 'view'),
            'add_account': ('accounts', 'add'),
            'edit_account': ('accounts', 'edit'),
            'delete_account': ('accounts', 'delete'),
            
            # Reports
            'reports': ('reports', 'view'),
            'export_permissions': ('reports', 'export'),
            
            # Settings
            'settings': ('settings', 'view'),
            'add_setting': ('settings', 'add'),
            
            # Users and Permissions
            'users': ('users', 'view'),
            'add_user': ('users', 'add'),
            'edit_user': ('users', 'edit'),
            'delete_user': ('users', 'delete'),
            'permissions': ('permissions', 'view'),
            'users_permissions_list': ('permissions', 'view'),
            
            # Employees
            'employees': ('employees', 'view'),
            'add_employee': ('employees', 'add'),
            
            # Attendance
            'attendance': ('attendance', 'view'),
            'add_attendance': ('attendance', 'add'),
            'edit_attendance': ('attendance', 'edit'),
            'delete_attendance': ('attendance', 'delete'),
            
            # Salaries
            'salaries': ('salaries', 'view'),
            'add_salary': ('salaries', 'add'),
            'edit_salary': ('salaries', 'edit'),
            'delete_salary': ('salaries', 'delete'),
            'confirm_salary': ('salaries', 'confirm'),
            
            # POS
            'pos': ('pos', 'view'),
            'pos_open_session': ('pos', 'add'),
            'pos_close_session': ('pos', 'edit'),
            
            # Manufacturing
            'manufacturing': ('manufacturing', 'view'),
        }
        
        # URLs that should be excluded from permission checks
        self.excluded_urls = [
            'login',
            'logout',
            'dashboard',
            'api/',  # API endpoints
        ]

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        """Process view before it's called"""
        
        # Skip if user is not authenticated
        if not request.user.is_authenticated:
            return None
        
        # Skip if user is superuser
        if request.user.is_superuser:
            return None
        
        # Get current URL name
        url_name = request.resolver_match.url_name if request.resolver_match else None
        
        if not url_name:
            return None
        
        # Skip excluded URLs
        for excluded in self.excluded_urls:
            if excluded in url_name or url_name.startswith(excluded):
                return None
        
        # Check if URL requires permission
        if url_name in self.protected_urls:
            screen, action = self.protected_urls[url_name]
            
            if not check_user_permission(request.user, screen, action):
                messages.error(
                    request, 
                    f'ليس لديك صلاحية {self.get_action_name(action)} في {self.get_screen_name(screen)}'
                )
                return redirect('dashboard')
        
        return None
    
    def get_screen_name(self, screen):
        """Get Arabic name for screen"""
        screen_names = {
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
            'employees': 'الموظفين',
            'attendance': 'الحضور والانصراف',
            'salaries': 'الرواتب',
            'pos': 'نقاط البيع',
            'manufacturing': 'التصنيع'
        }
        return screen_names.get(screen, screen)
    
    def get_action_name(self, action):
        """Get Arabic name for action"""
        action_names = {
            'view': 'عرض',
            'add': 'إضافة',
            'edit': 'تعديل',
            'delete': 'حذف',
            'confirm': 'تأكيد',
            'print': 'طباعة',
            'export': 'تصدير'
        }
        return action_names.get(action, action)