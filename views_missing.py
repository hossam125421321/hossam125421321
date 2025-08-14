# الدوال المفقودة للـ URLs
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Sum
from .models import *
from .decorators import permission_required, subscription_required

@login_required
@subscription_required
@permission_required('purchases', 'view')
def purchases(request):
    purchases = Purchase.objects.select_related('supplier', 'created_by').all().order_by('-created_at')
    
    # فلترة حسب الحالة
    status = request.GET.get('status', '')
    if status:
        purchases = purchases.filter(status=status)
    
    # فلترة بالبحث
    search = request.GET.get('search', '')
    if search:
        purchases = purchases.filter(
            Q(invoice_number__icontains=search) |
            Q(supplier__name__icontains=search)
        )
    
    # حساب الإحصائيات
    total_purchases = purchases.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    confirmed_count = purchases.filter(status='confirmed').count()
    paid_count = purchases.filter(status='paid').count()
    
    context = {
        'purchases': purchases,
        'search': search,
        'status': status,
        'status_choices': Purchase.INVOICE_STATUS,
        'total_purchases': total_purchases,
        'confirmed_count': confirmed_count,
        'paid_count': paid_count,
        'currency_symbol': 'د.ك',
        'company_name': 'شركة ERP',
    }
    return render(request, 'purchases.html', context)

@login_required
@subscription_required
@permission_required('suppliers', 'view')
def suppliers(request):
    suppliers = Supplier.objects.all().order_by('-created_at')
    
    search = request.GET.get('search', '')
    if search:
        suppliers = suppliers.filter(
            Q(name__icontains=search) |
            Q(phone__icontains=search) |
            Q(email__icontains=search)
        )
    
    context = {
        'suppliers': suppliers,
        'search': search,
    }
    return render(request, 'suppliers.html', context)

@login_required
@subscription_required
@permission_required('customers', 'view')
def customers(request):
    customers = Customer.objects.all().order_by('-created_at')
    
    # فلترة بالبحث
    search = request.GET.get('search', '')
    if search:
        customers = customers.filter(
            Q(name__icontains=search) | 
            Q(phone__icontains=search) |
            Q(email__icontains=search)
        )
    
    context = {
        'customers': customers,
        'search': search,
    }
    return render(request, 'customers.html', context)

@login_required
@subscription_required
@permission_required('sales', 'view')
def sales(request):
    sales = Sale.objects.select_related('customer', 'created_by').all().order_by('-created_at')
    
    # فلترة حسب الحالة
    status = request.GET.get('status', '')
    if status:
        sales = sales.filter(status=status)
    
    # فلترة بالبحث
    search = request.GET.get('search', '')
    if search:
        sales = sales.filter(
            Q(invoice_number__icontains=search) |
            Q(customer__name__icontains=search)
        )
    
    context = {
        'sales': sales,
        'search': search,
        'status': status,
        'status_choices': Sale.INVOICE_STATUS,
    }
    return render(request, 'sales.html', context)

@login_required
@subscription_required
@permission_required('stock', 'view')
def stock(request):
    products = Product.objects.all().order_by('name')
    
    context = {
        'products': products,
    }
    return render(request, 'stock.html', context)

@login_required
@subscription_required
@permission_required('reports', 'view')
def reports(request):
    context = {
        'total_sales': 0,
        'total_purchases': 0,
        'total_products': Product.objects.count(),
        'total_customers': Customer.objects.count(),
    }
    return render(request, 'reports.html', context)

@login_required
@subscription_required
@permission_required('settings', 'view')
def settings(request):
    if request.method == 'POST':
        messages.success(request, 'تم حفظ الإعدادات بنجاح')
        return redirect('settings')
    
    context = {
        'current_settings': {
            'company_name': 'شركة ERP',
            'currency_symbol': 'د.ك',
            'theme_color': 'blue',
        }
    }
    return render(request, 'settings.html', context)

@login_required
@subscription_required
@permission_required('permissions', 'view')
def permissions_list(request):
    from django.contrib.auth.models import User
    
    users = User.objects.all()
    users_with_permissions = []
    
    for user in users:
        try:
            permissions = Permission.objects.filter(user=user)
            user_permissions = {}
            for perm in permissions:
                user_permissions[perm.screen] = {
                    'can_view': perm.can_view,
                    'can_add': perm.can_add,
                    'can_edit': perm.can_edit,
                    'can_delete': perm.can_delete,
                    'can_confirm': perm.can_confirm,
                    'can_print': perm.can_print,
                    'can_export': perm.can_export
                }
        except:
            user_permissions = {}
        
        users_with_permissions.append({
            'user': user,
            'permissions': user_permissions,
            'permissions_count': len(user_permissions),
            'accessible_screens': 7 if user.is_superuser else len(user_permissions),
            'is_superuser': user.is_superuser,
            'last_login': user.last_login
        })
    
    context = {
        'users_with_permissions': users_with_permissions,
        'total_users': users.count(),
        'available_screens_count': 7,
        'available_actions_count': 7,
        'available_screens': {
            'dashboard': 'لوحة التحكم',
            'products': 'المنتجات',
            'customers': 'العملاء',
            'suppliers': 'الموردين',
            'sales': 'المبيعات',
            'purchases': 'المشتريات',
            'reports': 'التقارير'
        },

    }
    return render(request, 'permissions.html', context)

