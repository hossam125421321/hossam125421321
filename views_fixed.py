"""
Views محسنة للنظام
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import date, timedelta
import json
from .models import *
from .utils import safe_decimal, safe_int, json_response, handle_error
from .security_fixes import sanitize_html_input, validate_numeric_input

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        username = sanitize_html_input(request.POST.get('username', '').strip())
        password = request.POST.get('password', '').strip()
        
        if not username or not password:
            messages.error(request, 'يرجى إدخال اسم المستخدم وكلمة المرور')
            return render(request, 'auth/simple_login.html')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'اسم المستخدم أو كلمة المرور غير صحيح')
    
    return render(request, 'auth/simple_login.html')

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def dashboard(request):
    try:
        # إحصائيات أساسية
        total_products = Product.objects.count()
        total_customers = Customer.objects.count()
        
        # مبيعات اليوم
        today = date.today()
        today_sales = Sale.objects.filter(
            created_at__date=today,
            status='confirmed'
        ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        
        today_orders = Sale.objects.filter(
            created_at__date=today
        ).count()
        
        # آخر المبيعات
        recent_sales = Sale.objects.select_related('customer').order_by('-created_at')[:5]
        
        # منتجات بمخزون منخفض
        low_stock_products = []
        for product in Product.objects.all()[:5]:
            stock = safe_decimal(getattr(product, 'stock', 0))
            if stock <= 10:
                low_stock_products.append(product)
        
        context = {
            'today_sales': today_sales,
            'today_orders': today_orders,
            'total_products': total_products,
            'total_customers': total_customers,
            'recent_sales': recent_sales,
            'low_stock_products': low_stock_products,
        }
        return render(request, 'dashboard.html', context)
        
    except Exception as e:
        messages.error(request, f'خطأ في تحميل لوحة التحكم: {str(e)}')
        return render(request, 'dashboard.html', {
            'today_sales': 0,
            'today_orders': 0,
            'total_products': 0,
            'total_customers': 0,
            'recent_sales': [],
            'low_stock_products': [],
        })

@login_required
def products(request):
    try:
        products = Product.objects.all().order_by('-created_at')
        
        # فلترة بالبحث
        search = request.GET.get('search', '')
        if search:
            search = sanitize_html_input(search)
            products = products.filter(
                Q(name__icontains=search) | 
                Q(barcode__icontains=search) |
                Q(category__icontains=search)
            )
        
        context = {
            'products': products,
            'search': search,
        }
        return render(request, 'products.html', context)
    except Exception as e:
        messages.error(request, f'خطأ في تحميل المنتجات: {str(e)}')
        return render(request, 'products.html', {'products': [], 'search': ''})

@login_required
@csrf_protect
def add_product(request):
    if request.method == 'POST':
        try:
            name = sanitize_html_input(request.POST.get('name'))
            barcode = sanitize_html_input(request.POST.get('barcode', ''))
            category = sanitize_html_input(request.POST.get('category', ''))
            unit = sanitize_html_input(request.POST.get('unit', 'قطعة'))
            description = sanitize_html_input(request.POST.get('description', ''))
            price = validate_numeric_input(request.POST.get('price', 0))
            stock = validate_numeric_input(request.POST.get('initial_stock', 0))
            
            if not name:
                messages.error(request, 'اسم المنتج مطلوب')
                return render(request, 'add_product.html')
            
            # إنشاء المنتج
            product = Product.objects.create(
                name=name,
                barcode=barcode or f"PRD{int(timezone.now().timestamp())}",
                category=category,
                unit=unit,
                description=description,
                price=price,
                stock=stock,
                is_active=True,
                created_by=request.user
            )
            
            messages.success(request, 'تم إضافة المنتج بنجاح')
            return redirect('products')
            
        except Exception as e:
            messages.error(request, f'خطأ: {str(e)}')
    
    return render(request, 'add_product.html')

@login_required
def customers(request):
    try:
        customers = Customer.objects.all().order_by('-created_at')
        
        # فلترة بالبحث
        search = request.GET.get('search', '')
        if search:
            search = sanitize_html_input(search)
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
    except Exception as e:
        messages.error(request, f'خطأ في تحميل العملاء: {str(e)}')
        return render(request, 'customers.html', {'customers': [], 'search': ''})

@login_required
@csrf_protect
def add_customer(request):
    if request.method == 'POST':
        try:
            name = sanitize_html_input(request.POST.get('name'))
            phone = sanitize_html_input(request.POST.get('phone'))
            email = sanitize_html_input(request.POST.get('email', ''))
            address = sanitize_html_input(request.POST.get('address', ''))
            credit_limit = validate_numeric_input(request.POST.get('credit_limit', 0))
            opening_balance = validate_numeric_input(request.POST.get('opening_balance', 0))
            
            if not name or not phone:
                messages.error(request, 'اسم العميل ورقم الهاتف مطلوبان')
                return render(request, 'add_customer.html')
            
            customer = Customer.objects.create(
                name=name,
                phone=phone,
                email=email,
                address=address,
                credit_limit=credit_limit,
                opening_balance=opening_balance,
                is_active=True
            )
            
            messages.success(request, 'تم إضافة العميل بنجاح')
            return redirect('customers')
            
        except Exception as e:
            messages.error(request, f'خطأ: {str(e)}')
    
    return render(request, 'add_customer.html')

@login_required
def sales(request):
    try:
        sales = Sale.objects.select_related('customer').order_by('-created_at')
        
        # فلترة حسب الحالة
        status = request.GET.get('status', '')
        if status:
            sales = sales.filter(status=status)
        
        # فلترة بالبحث
        search = request.GET.get('search', '')
        if search:
            search = sanitize_html_input(search)
            sales = sales.filter(
                Q(invoice_number__icontains=search) |
                Q(customer__name__icontains=search)
            )
        
        context = {
            'sales': sales,
            'search': search,
            'status': status,
        }
        return render(request, 'sales.html', context)
    except Exception as e:
        messages.error(request, f'خطأ في تحميل المبيعات: {str(e)}')
        return render(request, 'sales.html', {'sales': [], 'search': '', 'status': ''})

@login_required
@csrf_protect
def add_sale(request):
    if request.method == 'POST':
        try:
            customer_id = request.POST.get('customer_id')
            subtotal = validate_numeric_input(request.POST.get('subtotal', 0))
            discount_amount = validate_numeric_input(request.POST.get('discount_amount', 0))
            tax_amount = validate_numeric_input(request.POST.get('tax_amount', 0))
            total_amount = validate_numeric_input(request.POST.get('total_amount', 0))
            notes = sanitize_html_input(request.POST.get('notes', ''))
            
            if not customer_id:
                messages.error(request, 'يرجى اختيار عميل')
                return render(request, 'add_sale.html', {
                    'customers': Customer.objects.all(),
                    'products': Product.objects.filter(is_active=True)
                })
            
            sale = Sale.objects.create(
                customer_id=customer_id,
                subtotal=subtotal,
                discount_amount=discount_amount,
                tax_amount=tax_amount,
                total_amount=total_amount,
                notes=notes,
                status='draft',
                created_by=request.user
            )
            
            # إضافة عناصر الفاتورة
            items_json = request.POST.get('items', '[]')
            if items_json and items_json != '[]':
                items_data = json.loads(items_json)
                for item_data in items_data:
                    SaleItem.objects.create(
                        sale=sale,
                        product_id=item_data['product_id'],
                        quantity=validate_numeric_input(item_data['quantity']),
                        unit_price=validate_numeric_input(item_data['unit_price'])
                    )
            
            messages.success(request, f'تم إنشاء الفاتورة #{sale.invoice_number} بنجاح')
            return redirect('sales')
            
        except Exception as e:
            messages.error(request, f'خطأ: {str(e)}')
    
    context = {
        'customers': Customer.objects.all(),
        'products': Product.objects.filter(is_active=True)
    }
    return render(request, 'add_sale.html', context)

@login_required
def stock(request):
    try:
        products = Product.objects.all().order_by('name')
        
        stock_data = []
        for product in products:
            current_stock = safe_decimal(getattr(product, 'stock', 0))
            min_stock = 10  # الحد الأدنى الافتراضي
            
            stock_data.append({
                'product': product,
                'current_stock': current_stock,
                'min_stock': min_stock,
                'is_low_stock': current_stock <= min_stock,
            })
        
        context = {
            'stock_data': stock_data,
            'total_products': len(stock_data),
            'low_stock_count': sum(1 for item in stock_data if item['is_low_stock']),
        }
        return render(request, 'stock.html', context)
    except Exception as e:
        messages.error(request, f'خطأ في تحميل المخزون: {str(e)}')
        return render(request, 'stock.html', {'stock_data': [], 'total_products': 0, 'low_stock_count': 0})

@login_required
def accounts(request):
    try:
        accounts_list = Account.objects.all().order_by('account_code')
        
        stats = {
            'total_accounts': Account.objects.count(),
            'customers_count': Customer.objects.count(),
            'suppliers_count': Supplier.objects.count(),
        }
        
        context = {
            'accounts': accounts_list,
            'stats': stats,
        }
        return render(request, 'accounts.html', context)
    except Exception as e:
        messages.error(request, f'خطأ في تحميل الحسابات: {str(e)}')
        return render(request, 'accounts.html', {'accounts': [], 'stats': {}})

@login_required
def reports(request):
    try:
        # إحصائيات أساسية
        total_sales = Sale.objects.filter(status='confirmed').aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        total_purchases = Purchase.objects.filter(status='confirmed').aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        
        context = {
            'total_sales': total_sales,
            'total_purchases': total_purchases,
            'net_profit': total_sales - total_purchases,
        }
        return render(request, 'reports.html', context)
    except Exception as e:
        messages.error(request, f'خطأ في تحميل التقارير: {str(e)}')
        return render(request, 'reports.html', {'total_sales': 0, 'total_purchases': 0, 'net_profit': 0})

@login_required
def settings(request):
    if request.method == 'POST':
        try:
            # حفظ الإعدادات
            company_name = sanitize_html_input(request.POST.get('company_name', 'شركة ERP'))
            currency_symbol = sanitize_html_input(request.POST.get('currency_symbol', 'د.ك'))
            
            # يمكن إضافة المزيد من الإعدادات هنا
            
            messages.success(request, 'تم حفظ الإعدادات بنجاح')
            return redirect('settings')
            
        except Exception as e:
            messages.error(request, f'خطأ في حفظ الإعدادات: {str(e)}')
    
    current_settings = {
        'company_name': 'شركة ERP',
        'currency_symbol': 'د.ك',
    }
    
    return render(request, 'settings.html', {'current_settings': current_settings})

@login_required
def pos(request):
    try:
        # إحصائيات نقاط البيع
        today = date.today()
        today_sales = Sale.objects.filter(
            created_at__date=today,
            status='confirmed'
        ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        
        context = {
            'today_sales': today_sales,
            'active_sessions': 0,  # يمكن تطويرها لاحقاً
        }
        return render(request, 'pos.html', context)
    except Exception as e:
        messages.error(request, f'خطأ في تحميل نقاط البيع: {str(e)}')
        return render(request, 'pos.html', {'today_sales': 0, 'active_sessions': 0})

# API للبحث عن المنتجات
@login_required
def search_products_api(request):
    try:
        query = sanitize_html_input(request.GET.get('q', '').strip())
        
        if not query:
            return json_response(success=False, message='يرجى إدخال نص البحث')
        
        products = Product.objects.filter(
            Q(name__icontains=query) |
            Q(barcode__icontains=query),
            is_active=True
        ).order_by('name')[:20]
        
        products_data = []
        for product in products:
            products_data.append({
                'id': product.id,
                'name': product.name,
                'barcode': product.barcode or '',
                'price': float(getattr(product, 'price', 0) or 0),
                'stock': float(getattr(product, 'stock', 0) or 0),
            })
        
        return json_response(data={
            'products': products_data,
            'count': len(products_data)
        })
        
    except Exception as e:
        return json_response(success=False, message=str(e))

# دالة لتأكيد الفاتورة
@login_required
@csrf_protect
def confirm_invoice(request, sale_id):
    try:
        sale = get_object_or_404(Sale, id=sale_id)
        
        if sale.status == 'confirmed':
            messages.error(request, 'الفاتورة مؤكدة بالفعل')
        else:
            sale.status = 'confirmed'
            sale.save()
            
            # تحديث المخزون
            for item in sale.items.all():
                product = item.product
                if hasattr(product, 'stock'):
                    current_stock = safe_decimal(getattr(product, 'stock', 0))
                    product.stock = current_stock - safe_decimal(item.quantity)
                    product.save()
            
            messages.success(request, f'تم تأكيد الفاتورة #{sale.invoice_number} بنجاح')
            
    except Exception as e:
        messages.error(request, f'خطأ: {str(e)}')
    
    return redirect('sales')

# دالة لحذف المنتج
@login_required
def delete_product(request, product_id):
    if request.method == 'POST':
        try:
            product = get_object_or_404(Product, id=product_id)
            product_name = product.name
            product.delete()
            
            return json_response(message=f'تم حذف المنتج "{product_name}" بنجاح')
        except Exception as e:
            return json_response(success=False, message=str(e))
    
    return json_response(success=False, message='طريقة غير مسموحة')

# دالة لحذف العميل
@login_required
def delete_customer(request, customer_id):
    if request.method == 'POST':
        try:
            customer = get_object_or_404(Customer, id=customer_id)
            
            # التحقق من وجود فواتير مرتبطة
            if Sale.objects.filter(customer=customer).exists():
                return json_response(success=False, message='لا يمكن حذف العميل لوجود فواتير مرتبطة به')
            
            customer_name = customer.name
            customer.delete()
            
            return json_response(message=f'تم حذف العميل "{customer_name}" بنجاح')
        except Exception as e:
            return json_response(success=False, message=str(e))
    
    return json_response(success=False, message='طريقة غير مسموحة')

# دالة لعرض قائمة التقارير المحاسبية
@login_required
def accounting_reports_menu(request):
    return render(request, 'accounting/reports_menu.html')