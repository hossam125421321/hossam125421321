# Django imports (must be at the top)
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
import uuid
import threading
import json

# مدير النماذج المخصص للشركات المتعددة
class CompanyManager(models.Manager):
    def get_queryset(self):
        queryset = super().get_queryset()
        # الحصول على الشركة الحالية من thread local أو request
        company = getattr(threading.current_thread(), 'current_company', None)
        if company and hasattr(self.model, 'company'):
            return queryset.filter(company=company)
        return queryset
    
    def for_company(self, company):
        """الحصول على البيانات لشركة محددة"""
        if hasattr(self.model, 'company'):
            return super().get_queryset().filter(company=company)
        return super().get_queryset()
    
    def all_companies(self):
        """الحصول على البيانات لجميع الشركات (للمدراء فقط)"""
        return super().get_queryset()

class CompanyFilterMixin:
    """Mixin لإضافة فلترة الشركة تلقائياً"""
    
    def save(self, *args, **kwargs):
        # إضافة الشركة الحالية تلقائياً إذا لم تكن محددة
        if hasattr(self, 'company') and not getattr(self, 'company_id', None):
            current_company = getattr(threading.current_thread(), 'current_company', None)
            if current_company:
                self.company = current_company
        super().save(*args, **kwargs)
    
    class Meta:
        abstract = True

# نظام الشركات والفروع (تم نقله لأعلى)
class Company(models.Model):
    name = models.CharField(max_length=200, verbose_name='اسم الشركة')
    code = models.CharField(max_length=10, unique=True, verbose_name='كود الشركة')
    database_name = models.CharField(max_length=100, unique=True, verbose_name='اسم قاعدة البيانات')
    logo = models.ImageField(upload_to='company_logos/', blank=True, null=True, verbose_name='الشعار')
    address = models.TextField(blank=True, verbose_name='العنوان')
    phone = models.CharField(max_length=20, blank=True, verbose_name='رقم الهاتف')
    email = models.EmailField(blank=True, verbose_name='البريد الإلكتروني')
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    subscription_end = models.DateField(verbose_name='انتهاء الاشتراك')
    subscription_type = models.CharField(max_length=20, choices=[
        ('monthly', 'شهري'), ('yearly', 'سنوي')
    ], default='monthly', verbose_name='نوع الاشتراك')
    created_at = models.DateTimeField(default=timezone.now)
    
    @property
    def is_subscription_active(self):
        from datetime import date
        return self.subscription_end >= date.today() and self.is_active
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = 'شركة'
        verbose_name_plural = 'الشركات'
        ordering = ['-created_at']

# مركز التكلفة
class CostCenter(CompanyFilterMixin, models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='الشركة', db_index=True)
    
    objects = CompanyManager()
    name = models.CharField(max_length=200, verbose_name='اسم مركز التكلفة')
    code = models.CharField(max_length=20, verbose_name='كود مركز التكلفة')
    description = models.TextField(blank=True, null=True, verbose_name='الوصف')
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='تاريخ الإنشاء')

    class Meta:
        verbose_name = 'مركز تكلفة'
        verbose_name_plural = 'مراكز التكلفة'
        ordering = ['code']
        unique_together = ['company', 'code']

    def __str__(self):
        return f"{self.code} - {self.name}"

# المشاريع
class Project(CompanyFilterMixin, models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='الشركة', db_index=True)
    
    objects = CompanyManager()
    name = models.CharField(max_length=200, verbose_name='اسم المشروع')
    code = models.CharField(max_length=20, verbose_name='كود المشروع')
    description = models.TextField(blank=True, null=True, verbose_name='الوصف')
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='تاريخ الإنشاء')

    class Meta:
        verbose_name = 'مشروع'
        verbose_name_plural = 'المشاريع'
        ordering = ['code']
        unique_together = ['company', 'code']

    def __str__(self):
        return f"{self.code} - {self.name}"

# تم نقل نموذج Company لأعلى

class Branch(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='الشركة', db_index=True, null=True, blank=True)
    name = models.CharField(max_length=200, verbose_name='اسم الفرع')
    code = models.CharField(max_length=10, verbose_name='كود الفرع')
    address = models.TextField(blank=True, verbose_name='العنوان')
    phone = models.CharField(max_length=20, blank=True, verbose_name='رقم الهاتف')
    manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='المدير')
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='تاريخ الإنشاء')
    
    class Meta:
        unique_together = ['company', 'code']
        verbose_name = 'فرع'
        verbose_name_plural = 'الفروع'
        ordering = ['company', 'code']
    
    def __str__(self):
        return f"{self.company.name} - {self.name}"

class Warehouse(CompanyFilterMixin, models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='الشركة', db_index=True)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, verbose_name='الفرع')
    
    objects = CompanyManager()
    name = models.CharField(max_length=200, verbose_name='اسم المخزن')
    code = models.CharField(max_length=10, verbose_name='كود المخزن')
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    
    class Meta:
        unique_together = ['company', 'branch', 'code']
    
    def __str__(self):
        return f"{self.branch.name} - {self.name}"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name='المستخدم')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='الشركة', db_index=True)
    default_branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='الفرع الافتراضي')
    default_warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='المخزن الافتراضي')
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    
    objects = CompanyManager()
    
    def __str__(self):
        return f"{self.user.username} - {self.company.name}"

class Account(models.Model):
    ACCOUNT_TYPES = [
        ('asset', 'أصول'),
        ('liability', 'خصوم'),
        ('equity', 'حقوق ملكية'),
        ('revenue', 'إيرادات'),
        ('expense', 'مصروفات'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='الشركة', db_index=True)
    account_code = models.CharField(max_length=20, verbose_name='رمز الحساب')
    name = models.CharField(max_length=200, verbose_name='اسم الحساب')
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES, verbose_name='نوع الحساب')
    parent_account = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, verbose_name='الحساب الأب')
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='الرصيد')
    opening_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='الرصيد الافتتاحي')
    debit_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='الرصيد المدين')
    credit_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='الرصيد الدائن')
    auto_update = models.BooleanField(default=True, verbose_name='تحديث تلقائي')
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='تاريخ الإنشاء')
    
    class Meta:
        verbose_name = 'حساب'
        verbose_name_plural = 'الحسابات'
        ordering = ['account_code']
        unique_together = ['company', 'account_code']
    
    def __str__(self):
        return f"{self.account_code} - {self.name}"

class Employee(models.Model):
    EMPLOYMENT_STATUS = [
        ('active', 'نشط'),
        ('inactive', 'غير نشط'),
        ('terminated', 'منتهي الخدمة'),
        ('suspended', 'موقوف'),
    ]
    
    EMPLOYMENT_TYPE = [
        ('full_time', 'دوام كامل'),
        ('part_time', 'دوام جزئي'),
        ('contract', 'عقد'),
        ('temporary', 'مؤقت'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='الشركة', db_index=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name='المستخدم')
    employee_id = models.CharField(max_length=20, unique=True, editable=False, verbose_name='رقم الموظف')
    national_id = models.CharField(max_length=20, unique=True, verbose_name='رقم الهوية')
    phone = models.CharField(max_length=20, verbose_name='رقم الهاتف')
    address = models.TextField(blank=True, verbose_name='العنوان')
    birth_date = models.DateField(null=True, blank=True, verbose_name='تاريخ الميلاد')
    hire_date = models.DateField(verbose_name='تاريخ التوظيف')
    department = models.CharField(max_length=100, verbose_name='القسم')
    position = models.CharField(max_length=100, verbose_name='المنصب')
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='الراتب الأساسي')
    overtime_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='معدل الساعة الإضافية')
    employment_status = models.CharField(max_length=20, choices=EMPLOYMENT_STATUS, default='active', verbose_name='حالة التوظيف')
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPE, default='full_time', verbose_name='نوع التوظيف')
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, verbose_name='الفرع')
    fingerprint_id = models.CharField(max_length=50, blank=True, verbose_name='معرف البصمة')
    account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='الحساب المحاسبي')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='تاريخ الإنشاء')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_employees', verbose_name='أنشئ بواسطة')
    
    class Meta:
        verbose_name = 'موظف'
        verbose_name_plural = 'الموظفين'
        ordering = ['employee_id']
    
    def __str__(self):
        return f"{self.employee_id} - {self.user.get_full_name() or self.user.username}"
    
    def save(self, *args, **kwargs):
        if not self.employee_id:
            self.employee_id = self.generate_employee_id()
        super().save(*args, **kwargs)
    
    def generate_employee_id(self):
        last_employee = Employee.objects.order_by('-id').first()
        if last_employee and last_employee.employee_id.startswith('EMP'):
            try:
                last_number = int(last_employee.employee_id.replace('EMP', ''))
                new_number = last_number + 1
            except ValueError:
                new_number = 1
        else:
            new_number = 1
        return f"EMP{new_number:05d}"

class Product(CompanyFilterMixin, models.Model):
    CATEGORY_CHOICES = [
        ('إلكترونيات', 'إلكترونيات'),
        ('ملابس', 'ملابس'),
        ('أغذية', 'أغذية'),
        ('مستحضرات تجميل', 'مستحضرات تجميل'),
        ('أدوات منزلية', 'أدوات منزلية'),
        ('كتب', 'كتب'),
        ('رياضة', 'رياضة'),
        ('أخرى', 'أخرى'),
    ]
    
    UNIT_CHOICES = [
        ('قطعة', 'قطعة'),
        ('كيلو', 'كيلو'),
        ('لتر', 'لتر'),
        ('متر', 'متر'),
        ('علبة', 'علبة'),
        ('كرتون', 'كرتون'),
        ('زجاجة', 'زجاجة'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='الشركة', db_index=True)
    
    objects = CompanyManager()
    name = models.CharField(max_length=200, verbose_name='اسم المنتج')
    barcode = models.CharField(max_length=50, verbose_name='الباركود')
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, verbose_name='الفئة')
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default='قطعة', verbose_name='الوحدة')
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='السعر')
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='سعر التكلفة')
    stock = models.DecimalField(max_digits=10, decimal_places=3, default=0, verbose_name='المخزون')
    brand = models.CharField(max_length=100, blank=True, verbose_name='الماركة')
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    description = models.TextField(blank=True, null=True, verbose_name='الوصف')
    image = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name='الصورة')
    bom = models.BooleanField(default=False, verbose_name='يحتوي على BOM')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='تاريخ الإنشاء')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='أنشئ بواسطة')
    
    class Meta:
        verbose_name = 'منتج'
        verbose_name_plural = 'المنتجات'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.barcode:
            self.barcode = self.generate_barcode()
        super().save(*args, **kwargs)
    
    def generate_barcode(self):
        import time
        import random
        timestamp = str(int(time.time()))
        random_num = str(random.randint(100, 999))
        return f"{timestamp[-6:]}{random_num}"

class Customer(CompanyFilterMixin, models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='الشركة', db_index=True)
    
    objects = CompanyManager()
    name = models.CharField(max_length=200, verbose_name='اسم العميل')
    phone = models.CharField(max_length=20, verbose_name='رقم الهاتف')
    email = models.EmailField(blank=True, null=True, verbose_name='البريد الإلكتروني')
    address = models.TextField(blank=True, null=True, verbose_name='العنوان')
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='الحد الائتماني')
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='الرصيد الافتتاحي')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='تاريخ الإنشاء')
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    
    class Meta:
        verbose_name = 'عميل'
        verbose_name_plural = 'العملاء'
    
    def __str__(self):
        return self.name

class Supplier(CompanyFilterMixin, models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='الشركة', db_index=True)
    
    objects = CompanyManager()
    name = models.CharField(max_length=200, verbose_name='اسم المورد')
    phone = models.CharField(max_length=20, verbose_name='رقم الهاتف')
    email = models.EmailField(blank=True, null=True, verbose_name='البريد الإلكتروني')
    address = models.TextField(blank=True, null=True, verbose_name='العنوان')
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='الرصيد الافتتاحي')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='تاريخ الإنشاء')
    
    class Meta:
        verbose_name = 'مورد'
        verbose_name_plural = 'الموردين'
    
    def __str__(self):
        return self.name

class Sale(CompanyFilterMixin, models.Model):
    INVOICE_STATUS = [
        ('draft', 'مسودة'),
        ('pending', 'في الانتظار'),
        ('confirmed', 'مؤكدة'),
        ('paid', 'مدفوعة'),
        ('cancelled', 'ملغية'),
    ]
    
    SALE_TYPES = [
        ('invoice', 'فاتورة عادية'),
        ('pos', 'نقاط البيع'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='الشركة', db_index=True)
    
    objects = CompanyManager()
    invoice_number = models.CharField(max_length=50, verbose_name='رقم الفاتورة')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name='العميل')
    sale_type = models.CharField(max_length=20, choices=SALE_TYPES, default='invoice', verbose_name='نوع البيع')
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='المجموع الفرعي')
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='مبلغ الخصم')
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='مبلغ الضريبة')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='المبلغ الإجمالي')
    status = models.CharField(max_length=20, choices=INVOICE_STATUS, default='draft', verbose_name='الحالة')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='تاريخ البيع')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='البائع')
    
    class Meta:
        verbose_name = 'فاتورة بيع'
        verbose_name_plural = 'فواتير البيع'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"فاتورة #{self.invoice_number} - {self.customer.name}"

class Purchase(CompanyFilterMixin, models.Model):
    INVOICE_STATUS = [
        ('draft', 'مسودة'),
        ('pending', 'في الانتظار'),
        ('confirmed', 'مؤكدة'),
        ('paid', 'مدفوعة'),
        ('cancelled', 'ملغية'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='الشركة', db_index=True)
    invoice_number = models.CharField(max_length=50, verbose_name='رقم الفاتورة')
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, verbose_name='المورد')
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='المجموع الفرعي')
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='مبلغ الخصم')
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='مبلغ الضريبة')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='المبلغ الإجمالي')
    status = models.CharField(max_length=20, choices=INVOICE_STATUS, default='draft', verbose_name='الحالة')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='تاريخ الشراء')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='المشتري')
    
    class Meta:
        verbose_name = 'فاتورة شراء'
        verbose_name_plural = 'فواتير الشراء'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"فاتورة شراء #{self.invoice_number} - {self.supplier.name}"

# نماذج نقاط البيع
class POSSession(CompanyFilterMixin, models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='الشركة', db_index=True)
    
    objects = CompanyManager()
    SESSION_STATUS = [
        ('open', 'مفتوحة'),
        ('closed', 'مغلقة'),
        ('suspended', 'معلقة'),
    ]
    
    session_number = models.CharField(max_length=50, unique=True, verbose_name='رقم الجلسة')
    cashier = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='الكاشير')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, verbose_name='الفرع')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, verbose_name='المخزن')
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='الرصيد الافتتاحي')
    closing_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='الرصيد الختامي')
    total_sales = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='إجمالي المبيعات')
    total_cash = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='إجمالي النقدي')
    total_card = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='إجمالي الكي نت')
    status = models.CharField(max_length=20, choices=SESSION_STATUS, default='open', verbose_name='الحالة')
    opened_at = models.DateTimeField(default=timezone.now, verbose_name='وقت الفتح')
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name='وقت الإغلاق')
    notes = models.TextField(blank=True, null=True, verbose_name='ملاحظات')
    
    class Meta:
        verbose_name = 'جلسة نقاط البيع'
        verbose_name_plural = 'جلسات نقاط البيع'
        ordering = ['-opened_at']
    
    def __str__(self):
        return f"جلسة #{self.session_number} - {self.cashier.username}"
    
    def save(self, *args, **kwargs):
        if not self.session_number:
            self.session_number = self.generate_session_number()
        super().save(*args, **kwargs)
    
    def generate_session_number(self):
        import datetime
        today = datetime.date.today()
        prefix = f"POS-{today.year}{today.month:02d}{today.day:02d}"
        last_session = POSSession.objects.filter(session_number__startswith=prefix).order_by('-id').first()
        if last_session:
            last_number = int(last_session.session_number.split('-')[-1])
            new_number = last_number + 1
        else:
            new_number = 1
        return f"{prefix}-{new_number:03d}"

class POSSale(CompanyFilterMixin, models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='الشركة', db_index=True)
    
    objects = CompanyManager()
    PAYMENT_METHODS = [
        ('cash', 'نقدي'),
        ('card', 'كي نت'),
        ('mixed', 'مختلط'),
    ]
    
    session = models.ForeignKey(POSSession, on_delete=models.CASCADE, verbose_name='الجلسة')
    receipt_number = models.CharField(max_length=50, verbose_name='رقم الإيصال')
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='العميل')
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='المجموع الفرعي')
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='مبلغ الخصم')
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='مبلغ الضريبة')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='المبلغ الإجمالي')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='cash', verbose_name='طريقة الدفع')
    cash_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='المبلغ النقدي')
    card_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='مبلغ الكي نت')
    change_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='الباقي')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='وقت البيع')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='الكاشير')
    
    class Meta:
        verbose_name = 'بيع نقاط البيع'
        verbose_name_plural = 'مبيعات نقاط البيع'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"إيصال #{self.receipt_number}"

class POSSaleItem(CompanyFilterMixin, models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='الشركة', db_index=True)
    
    objects = CompanyManager()
    pos_sale = models.ForeignKey(POSSale, related_name='items', on_delete=models.CASCADE, verbose_name='بيع نقاط البيع')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='المنتج')
    quantity = models.DecimalField(max_digits=10, decimal_places=3, verbose_name='الكمية')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='سعر الوحدة')
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='نسبة الخصم %')
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='مبلغ الخصم')
    total_price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='السعر الإجمالي')
    
    class Meta:
        verbose_name = 'عنصر بيع نقاط البيع'
        verbose_name_plural = 'عناصر مبيعات نقاط البيع'
    
    def save(self, *args, **kwargs):
        subtotal = self.quantity * self.unit_price
        if self.discount_percent > 0:
            self.discount_amount = subtotal * (self.discount_percent / 100)
        self.total_price = subtotal - self.discount_amount
        super().save(*args, **kwargs)

# نماذج التصنيع
class ManufacturingOrder(CompanyFilterMixin, models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='الشركة', db_index=True)
    
    objects = CompanyManager()
    ORDER_STATUS = [
        ('draft', 'مسودة'),
        ('confirmed', 'مؤكد'),
        ('in_progress', 'قيد التنفيذ'),
        ('completed', 'مكتمل'),
        ('cancelled', 'ملغي'),
    ]
    
    order_number = models.CharField(max_length=50, unique=True, verbose_name='رقم الأمر')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='المنتج')
    quantity = models.DecimalField(max_digits=10, decimal_places=3, verbose_name='الكمية المطلوبة')
    produced_quantity = models.DecimalField(max_digits=10, decimal_places=3, default=0, verbose_name='الكمية المنتجة')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, verbose_name='المخزن')
    start_date = models.DateField(verbose_name='تاريخ البدء')
    end_date = models.DateField(null=True, blank=True, verbose_name='تاريخ الانتهاء')
    status = models.CharField(max_length=20, choices=ORDER_STATUS, default='draft', verbose_name='الحالة')
    notes = models.TextField(blank=True, null=True, verbose_name='ملاحظات')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='تاريخ الإنشاء')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='أنشئ بواسطة')
    
    class Meta:
        verbose_name = 'أمر تصنيع'
        verbose_name_plural = 'أوامر التصنيع'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"أمر تصنيع #{self.order_number}"

# نماذج الحضور والانصراف
class Attendance(CompanyFilterMixin, models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='الشركة', db_index=True)
    
    objects = CompanyManager()
    ATTENDANCE_STATUS = [
        ('present', 'حاضر'),
        ('absent', 'غائب'),
        ('late', 'متأخر'),
        ('early_leave', 'انصراف مبكر'),
    ]
    
    employee = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='الموظف')
    date = models.DateField(verbose_name='التاريخ')
    check_in = models.TimeField(null=True, blank=True, verbose_name='وقت الحضور')
    check_out = models.TimeField(null=True, blank=True, verbose_name='وقت الانصراف')
    status = models.CharField(max_length=20, choices=ATTENDANCE_STATUS, default='present', verbose_name='الحالة')
    notes = models.TextField(blank=True, null=True, verbose_name='ملاحظات')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='تاريخ الإنشاء')
    
    class Meta:
        unique_together = ['employee', 'date']
        verbose_name = 'حضور وانصراف'
        verbose_name_plural = 'الحضور والانصراف'
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.employee.username} - {self.date}"

# نماذج الرواتب
class Salary(CompanyFilterMixin, models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='الشركة', db_index=True)
    
    objects = CompanyManager()
    SALARY_STATUS = [
        ('draft', 'مسودة'),
        ('confirmed', 'مؤكد'),
        ('paid', 'مدفوع'),
    ]
    
    employee = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='الموظف')
    month = models.IntegerField(verbose_name='الشهر')
    year = models.IntegerField(verbose_name='السنة')
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='الراتب الأساسي')
    allowances = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='البدلات')
    deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='الخصومات')
    overtime_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='ساعات إضافية')
    overtime_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='معدل الساعة الإضافية')
    net_salary = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='صافي الراتب')
    status = models.CharField(max_length=20, choices=SALARY_STATUS, default='draft', verbose_name='الحالة')
    notes = models.TextField(blank=True, null=True, verbose_name='ملاحظات')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='تاريخ الإنشاء')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_salaries', verbose_name='أنشئ بواسطة')
    
    class Meta:
        unique_together = ['employee', 'month', 'year']
        verbose_name = 'راتب'
        verbose_name_plural = 'الرواتب'
        ordering = ['-year', '-month']
    
    def __str__(self):
        return f"راتب {self.employee.username} - {self.month}/{self.year}"
    
    def save(self, *args, **kwargs):
        overtime_amount = self.overtime_hours * self.overtime_rate
        self.net_salary = self.basic_salary + self.allowances + overtime_amount - self.deductions
        super().save(*args, **kwargs)

# نظام الصلاحيات المتقدم
class Permission(CompanyFilterMixin, models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='الشركة', db_index=True, null=True, blank=True)
    
    objects = CompanyManager()
    SCREEN_CHOICES = [
        ('dashboard', 'لوحة التحكم'),
        ('products', 'المنتجات'),
        ('sales', 'المبيعات'),
        ('purchases', 'المشتريات'),
        ('customers', 'العملاء'),
        ('suppliers', 'الموردين'),
        ('stock', 'المخزون'),
        ('accounts', 'الحسابات'),
        ('reports', 'التقارير'),
        ('settings', 'الإعدادات'),
        ('users', 'المستخدمين'),
        ('permissions', 'الصلاحيات'),
        ('companies', 'الشركات'),
        ('branches', 'الفروع'),
        ('warehouses', 'المخازن'),
        ('pos', 'نقاط البيع'),
        ('manufacturing', 'التصنيع'),
        ('attendance', 'الحضور والانصراف'),
        ('salaries', 'الرواتب'),
        ('employees', 'الموظفين'),
        ('sales_reps', 'مناديب المبيعات')
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='المستخدم', db_index=True)
    screen = models.CharField(max_length=50, choices=SCREEN_CHOICES, verbose_name='الشاشة', db_index=True)
    can_view = models.BooleanField(default=True, verbose_name='عرض')
    can_add = models.BooleanField(default=False, verbose_name='إضافة')
    can_edit = models.BooleanField(default=False, verbose_name='تعديل')
    can_delete = models.BooleanField(default=False, verbose_name='حذف')
    can_confirm = models.BooleanField(default=False, verbose_name='تأكيد')
    can_print = models.BooleanField(default=False, verbose_name='طباعة')
    can_export = models.BooleanField(default=False, verbose_name='تصدير')
    branch_access = models.ManyToManyField(Branch, blank=True, verbose_name='الفروع المسموحة')
    warehouse_access = models.ManyToManyField(Warehouse, blank=True, verbose_name='المخازن المسموحة')
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_permissions', verbose_name='أنشئ بواسطة')
    
    def save(self, *args, **kwargs):
        # إضافة الشركة الحالية تلقائياً إذا لم تكن محددة
        if not self.company_id:
            # محاولة الحصول على الشركة من المستخدم
            try:
                user_profile = UserProfile.objects.get(user=self.user)
                self.company = user_profile.company
            except UserProfile.DoesNotExist:
                # إذا لم يوجد ملف شخصي، استخدم أول شركة متاحة
                first_company = Company.objects.first()
                if first_company:
                    self.company = first_company
        
        # مسح الكاش عند الحفظ
        from django.core.cache import cache
        cache_key = f"user_permissions_{self.user.id}_{self.company.id if self.company else 'global'}"
        cache.delete(cache_key)
        
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        # مسح الكاش عند الحذف
        from django.core.cache import cache
        cache_key = f"user_permissions_{self.user.id}_{self.company.id if self.company else 'global'}"
        cache.delete(cache_key)
        
        super().delete(*args, **kwargs)
    
    @property
    def actions_list(self):
        """قائمة العمليات المسموحة"""
        actions = []
        if self.can_view: actions.append('عرض')
        if self.can_add: actions.append('إضافة')
        if self.can_edit: actions.append('تعديل')
        if self.can_delete: actions.append('حذف')
        if self.can_confirm: actions.append('تأكيد')
        if self.can_print: actions.append('طباعة')
        if self.can_export: actions.append('تصدير')
        return actions
    
    @property
    def actions_count(self):
        """عدد العمليات المسموحة"""
        return len(self.actions_list)
    
    @property
    def has_full_access(self):
        """فحص إذا كان لديه صلاحية كاملة"""
        return all([
            self.can_view, self.can_add, self.can_edit, 
            self.can_delete, self.can_confirm, self.can_print, self.can_export
        ])
    
    @property
    def access_level(self):
        """مستوى الوصول"""
        if self.has_full_access:
            return 'كامل'
        elif self.actions_count >= 4:
            return 'متقدم'
        elif self.actions_count >= 2:
            return 'متوسط'
        else:
            return 'محدود'
    
    class Meta:
        unique_together = ['user', 'screen', 'company']
        verbose_name = 'صلاحية'
        verbose_name_plural = 'الصلاحيات'
        indexes = [
            models.Index(fields=['user', 'company']),
            models.Index(fields=['screen']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.get_screen_display()}"

class PermissionManager:
    @staticmethod
    def has_permission(user, screen, action='view', branch=None, warehouse=None):
        if user.is_superuser:
            return True
        
        try:
            permission = Permission.objects.get(user=user, screen=screen)
            
            if not getattr(permission, f'can_{action}', False):
                return False
            
            if branch and permission.branch_access.exists():
                if not permission.branch_access.filter(id=branch.id).exists():
                    return False
            
            if warehouse and permission.warehouse_access.exists():
                if not permission.warehouse_access.filter(id=warehouse.id).exists():
                    return False
            
            return True
        except Permission.DoesNotExist:
            return action == 'view'
        except Exception:
            return user.is_superuser

# نظام الإعدادات الديناميكي
class Setting(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True, verbose_name='الشركة')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, null=True, blank=True, verbose_name='الفرع')
    
    SETTING_TYPES = [
        ('string', 'نص'),
        ('integer', 'رقم صحيح'),
        ('decimal', 'رقم عشري'),
        ('boolean', 'صح/خطأ'),
        ('json', 'JSON'),
        ('file', 'ملف'),
        ('image', 'صورة'),
        ('color', 'لون'),
        ('email', 'بريد إلكتروني'),
        ('url', 'رابط'),
        ('phone', 'رقم هاتف'),
    ]
    
    CATEGORIES = [
        ('عامة', 'عامة'),
        ('طباعة', 'طباعة'),
        ('باركود', 'باركود'),
        ('عملة', 'عملة'),
        ('الشركة', 'الشركة'),
        ('شاشات', 'شاشات'),
        ('فواتير', 'فواتير'),
        ('تقارير', 'تقارير'),
        ('أمان', 'أمان'),
        ('نسخ احتياطي', 'نسخ احتياطي'),
        ('نقاط البيع', 'نقاط البيع'),
        ('المخزون', 'المخزون'),
        ('المحاسبة', 'المحاسبة'),
    ]
    
    key = models.CharField(max_length=100, verbose_name='مفتاح الإعداد', db_index=True)
    value = models.TextField(verbose_name='القيمة')
    setting_type = models.CharField(max_length=20, choices=SETTING_TYPES, default='string', verbose_name='نوع الإعداد')
    category = models.CharField(max_length=50, choices=CATEGORIES, verbose_name='الفئة', db_index=True)
    description = models.CharField(max_length=255, blank=True, verbose_name='الوصف')
    is_system = models.BooleanField(default=False, verbose_name='إعداد نظام')
    is_global = models.BooleanField(default=False, verbose_name='إعداد عام')
    is_required = models.BooleanField(default=False, verbose_name='مطلوب')
    default_value = models.TextField(blank=True, verbose_name='القيمة الافتراضية')
    validation_rules = models.TextField(blank=True, verbose_name='قواعد التحقق')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='تاريخ الإنشاء')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='أنشئ بواسطة')
    
    class Meta:
        verbose_name = 'إعداد'
        verbose_name_plural = 'الإعدادات'
        ordering = ['category', 'key']
        unique_together = [['key', 'company', 'branch']]
        indexes = [
            models.Index(fields=['key', 'category']),
            models.Index(fields=['company', 'branch']),
        ]
    
    def __str__(self):
        scope = ''
        if self.company and self.branch:
            scope = f' ({self.company.name} - {self.branch.name})'
        elif self.company:
            scope = f' ({self.company.name})'
        return f"{self.key}{scope}"
    
    def get_display_value(self):
        """عرض القيمة بشكل مناسب للواجهة"""
        if self.setting_type == 'boolean':
            return '✅ نعم' if self.get_value() else '❌ لا'
        elif self.setting_type == 'color':
            return f'🎨 {self.value}'
        elif self.setting_type == 'email':
            return f'📧 {self.value}'
        elif self.setting_type == 'url':
            return f'🔗 {self.value}'
        elif self.setting_type == 'phone':
            return f'📞 {self.value}'
        elif len(self.value) > 50:
            return f'{self.value[:47]}...'
        return self.value
    
    def get_value(self):
        """الحصول على القيمة بالنوع المناسب"""
        if not self.value and self.default_value:
            value = self.default_value
        else:
            value = self.value
            
        if self.setting_type == 'boolean':
            return str(value).lower() in ['true', '1', 'yes', 'on', 'نعم']
        elif self.setting_type == 'integer':
            try:
                return int(value)
            except (ValueError, TypeError):
                return 0
        elif self.setting_type == 'decimal':
            try:
                return Decimal(str(value))
            except (ValueError, TypeError):
                return Decimal('0.0')
        elif self.setting_type == 'json':
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return {}
        else:
            return str(value)
    
    def validate_value(self):
        """التحقق من صحة القيمة"""
        if self.is_required and not self.value:
            raise ValidationError(f'الإعداد {self.key} مطلوب')
        
        if self.setting_type == 'email' and self.value:
            from django.core.validators import validate_email
            try:
                validate_email(self.value)
            except ValidationError:
                raise ValidationError('عنوان البريد الإلكتروني غير صحيح')
        
        if self.setting_type == 'url' and self.value:
            from django.core.validators import URLValidator
            validator = URLValidator()
            try:
                validator(self.value)
            except ValidationError:
                raise ValidationError('الرابط غير صحيح')
    
    def clean(self):
        self.validate_value()
    
    @classmethod
    def get_category_icon(cls, category):
        """الحصول على أيقونة الفئة"""
        icons = {
            'عامة': '⚙️',
            'طباعة': '🖨️',
            'باركود': '📊',
            'عملة': '💰',
            'الشركة': '🏢',
            'شاشات': '🖥️',
            'فواتير': '📄',
            'تقارير': '📈',
            'أمان': '🔒',
            'نسخ احتياطي': '💾',
            'نقاط البيع': '🛒',
            'المخزون': '📦',
            'المحاسبة': '💼',
        }
        return icons.get(category, '📋')

class SettingsManager:
    _cache = {}
    
    @classmethod
    def get(cls, key, company=None, branch=None, default=None):
        cache_key = f"{company.id if company else 'global'}_{branch.id if branch else 'global'}_{key}"
        
        if cache_key in cls._cache:
            return cls._cache[cache_key]
        
        try:
            # البحث بالأولوية: فرع محدد -> شركة محددة -> عام
            setting = Setting.objects.filter(key=key).filter(
                models.Q(company=company, branch=branch) |
                models.Q(company=company, branch__isnull=True) |
                models.Q(is_global=True)
            ).order_by(
                models.Case(
                    models.When(company=company, branch=branch, then=1),
                    models.When(company=company, branch__isnull=True, then=2),
                    models.When(is_global=True, then=3),
                    default=4
                )
            ).first()
            
            if setting:
                value = setting.get_value()
                cls._cache[cache_key] = value
                return value
        except Setting.DoesNotExist:
            pass
        
        return default
    
    @classmethod
    def set(cls, key, value, company=None, branch=None, setting_type='string', category='عامة', description='', user=None):
        setting, created = Setting.objects.get_or_create(
            key=key,
            company=company,
            branch=branch,
            defaults={
                'value': str(value),
                'setting_type': setting_type,
                'category': category,
                'description': description,
                'created_by': user
            }
        )
        if not created:
            setting.value = str(value)
            if description:
                setting.description = description
            setting.save()
        
        cache_key = f"{company.id if company else 'global'}_{branch.id if branch else 'global'}_{key}"
        cls._cache[cache_key] = value
        return setting
    
    @classmethod
    def clear_cache(cls):
        cls._cache.clear()

class DynamicSettingsManager:
    CACHE_PREFIX = 'setting_'
    CACHE_TIMEOUT = 3600
    
    @classmethod
    def get_cache_key(cls, key, branch_id=None):
        return f"{cls.CACHE_PREFIX}{branch_id or 'global'}_{key}"
    
    @classmethod
    def get(cls, key, branch=None, default=None):
        cache_key = cls.get_cache_key(key, branch.id if branch else None)
        value = cache.get(cache_key)
        if value is not None:
            return value
        
        value = SettingsManager.get(key, branch, default)
        cache.set(cache_key, value, cls.CACHE_TIMEOUT)
        return value
    
    @classmethod
    def set(cls, key, value, branch=None, setting_type='string', category='general'):
        setting = SettingsManager.set(key, value, branch, setting_type, category)
        cache_key = cls.get_cache_key(key, branch.id if branch else None)
        cache.set(cache_key, value, cls.CACHE_TIMEOUT)
        return setting
    
    @classmethod
    def clear_cache(cls, key=None, branch=None):
        if key:
            cache_key = cls.get_cache_key(key, branch.id if branch else None)
            cache.delete(cache_key)

# نماذج المرتجعات
class SaleReturn(CompanyFilterMixin, models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='الشركة', db_index=True)
    
    objects = CompanyManager()
    RETURN_STATUS = [
        ('draft', 'مسودة'),
        ('confirmed', 'مؤكد'),
        ('cancelled', 'ملغي'),
    ]
    
    return_number = models.CharField(max_length=50, unique=True, verbose_name='رقم المرتجع')
    original_sale = models.ForeignKey(Sale, on_delete=models.CASCADE, verbose_name='الفاتورة الأصلية')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name='العميل')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='المبلغ الإجمالي')
    reason = models.TextField(blank=True, verbose_name='سبب المرتجع')
    status = models.CharField(max_length=20, choices=RETURN_STATUS, default='draft', verbose_name='الحالة')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='تاريخ المرتجع')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='أنشئ بواسطة')
    confirmed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='confirmed_sale_returns', verbose_name='أكد بواسطة')
    confirmed_at = models.DateTimeField(null=True, blank=True, verbose_name='تاريخ التأكيد')
    
    class Meta:
        verbose_name = 'مرتجع بيع'
        verbose_name_plural = 'مرتجعات البيع'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"مرتجع #{self.return_number} - {self.customer.name}"
    
    def save(self, *args, **kwargs):
        if not self.return_number:
            self.return_number = self.generate_return_number()
        super().save(*args, **kwargs)
    
    def generate_return_number(self):
        import datetime
        today = datetime.date.today()
        prefix = f"SR-{today.year}{today.month:02d}{today.day:02d}"
        last_return = SaleReturn.objects.filter(return_number__startswith=prefix).order_by('-id').first()
        if last_return:
            last_number = int(last_return.return_number.split('-')[-1])
            new_number = last_number + 1
        else:
            new_number = 1
        return f"{prefix}-{new_number:04d}"

class SaleReturnItem(CompanyFilterMixin, models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='الشركة', db_index=True)
    
    objects = CompanyManager()
    sale_return = models.ForeignKey(SaleReturn, related_name='items', on_delete=models.CASCADE, verbose_name='مرتجع البيع')
    original_sale_item = models.ForeignKey('SaleItem', on_delete=models.CASCADE, verbose_name='العنصر الأصلي')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='المنتج')
    quantity = models.DecimalField(max_digits=10, decimal_places=3, verbose_name='الكمية المرتجعة')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='سعر الوحدة')
    total_price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='السعر الإجمالي')
    
    class Meta:
        verbose_name = 'عنصر مرتجع بيع'
        verbose_name_plural = 'عناصر مرتجعات البيع'
    
    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)

class PurchaseReturn(CompanyFilterMixin, models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='الشركة', db_index=True)
    
    objects = CompanyManager()
    RETURN_STATUS = [
        ('draft', 'مسودة'),
        ('confirmed', 'مؤكد'),
        ('cancelled', 'ملغي'),
    ]
    
    return_number = models.CharField(max_length=50, unique=True, verbose_name='رقم المرتجع')
    original_purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, verbose_name='فاتورة الشراء الأصلية')
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, verbose_name='المورد')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='المبلغ الإجمالي')
    reason = models.TextField(blank=True, verbose_name='سبب المرتجع')
    status = models.CharField(max_length=20, choices=RETURN_STATUS, default='draft', verbose_name='الحالة')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='تاريخ المرتجع')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='أنشئ بواسطة')
    confirmed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='confirmed_purchase_returns', verbose_name='أكد بواسطة')
    confirmed_at = models.DateTimeField(null=True, blank=True, verbose_name='تاريخ التأكيد')
    
    class Meta:
        verbose_name = 'مرتجع شراء'
        verbose_name_plural = 'مرتجعات الشراء'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"مرتجع شراء #{self.return_number} - {self.supplier.name}"
    
    def save(self, *args, **kwargs):
        if not self.return_number:
            self.return_number = self.generate_return_number()
        super().save(*args, **kwargs)
    
    def generate_return_number(self):
        import datetime
        today = datetime.date.today()
        prefix = f"PR-{today.year}{today.month:02d}{today.day:02d}"
        last_return = PurchaseReturn.objects.filter(return_number__startswith=prefix).order_by('-id').first()
        if last_return:
            last_number = int(last_return.return_number.split('-')[-1])
            new_number = last_number + 1
        else:
            new_number = 1
        return f"{prefix}-{new_number:04d}"

class PurchaseReturnItem(CompanyFilterMixin, models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='الشركة', db_index=True)
    
    objects = CompanyManager()
    purchase_return = models.ForeignKey(PurchaseReturn, related_name='items', on_delete=models.CASCADE, verbose_name='مرتجع الشراء')
    original_purchase_item = models.ForeignKey('PurchaseItem', on_delete=models.CASCADE, verbose_name='العنصر الأصلي')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='المنتج')
    quantity = models.DecimalField(max_digits=10, decimal_places=3, verbose_name='الكمية المرتجعة')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='سعر الوحدة')
    total_price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='السعر الإجمالي')
    
    class Meta:
        verbose_name = 'عنصر مرتجع شراء'
        verbose_name_plural = 'عناصر مرتجعات الشراء'
    
    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)

# نماذج إضافية مطلوبة
class SaleItem(CompanyFilterMixin, models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='الشركة', db_index=True)
    
    objects = CompanyManager()
    sale = models.ForeignKey(Sale, related_name='items', on_delete=models.CASCADE, verbose_name='الفاتورة')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='المنتج')
    quantity = models.DecimalField(max_digits=10, decimal_places=3, verbose_name='الكمية')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='سعر الوحدة')
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='نسبة الخصم %')
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='نسبة ال��ريبة %')
    total_price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='السعر الإجمالي')
    
    class Meta:
        verbose_name = 'عنصر فاتورة بيع'
        verbose_name_plural = 'عناصر فواتير البيع'
    
    def save(self, *args, **kwargs):
        subtotal = self.quantity * self.unit_price
        discount_amount = subtotal * (self.discount_percent / 100)
        after_discount = subtotal - discount_amount
        tax_amount = after_discount * (self.tax_rate / 100)
        self.total_price = after_discount + tax_amount
        super().save(*args, **kwargs)

class PurchaseItem(CompanyFilterMixin, models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='الشركة', db_index=True)
    
    objects = CompanyManager()
    purchase = models.ForeignKey(Purchase, related_name='items', on_delete=models.CASCADE, verbose_name='فاتورة الشراء')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='المنتج')
    quantity = models.DecimalField(max_digits=10, decimal_places=3, verbose_name='الكمية')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='سعر الوحدة')
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='نسبة الخصم %')
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='نسبة الضريبة %')
    total_price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='السعر الإجمالي')
    
    class Meta:
        verbose_name = 'عنصر فاتورة شراء'
        verbose_name_plural = 'عناصر فواتير الشراء'
    
    def save(self, *args, **kwargs):
        subtotal = self.quantity * self.unit_price
        discount_amount = subtotal * (self.discount_percent / 100)
        after_discount = subtotal - discount_amount
        tax_amount = after_discount * (self.tax_rate / 100)
        self.total_price = after_discount + tax_amount
        super().save(*args, **kwargs)

class ProductStock(CompanyFilterMixin, models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='الشركة', db_index=True)
    
    objects = CompanyManager()
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='المنتج')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, verbose_name='المخزن')
    current_stock = models.DecimalField(max_digits=10, decimal_places=3, default=0, verbose_name='المخزون الحالي')
    min_stock = models.DecimalField(max_digits=10, decimal_places=3, default=0, verbose_name='الحد الأدنى للمخزون')
    max_stock = models.DecimalField(max_digits=10, decimal_places=3, default=0, verbose_name='الحد الأقصى للمخزون')
    reserved_stock = models.DecimalField(max_digits=10, decimal_places=3, default=0, verbose_name='المخزون المحجوز')
    last_updated = models.DateTimeField(auto_now=True, verbose_name='آخر تحديث')
    
    class Meta:
        unique_together = ['product', 'warehouse']
        verbose_name = 'مخزون المنتج'
        verbose_name_plural = 'مخزون المنتجات'
    
    def __str__(self):
        return f"{self.product.name} - {self.warehouse.name}: {self.current_stock}"

class ProductPrice(CompanyFilterMixin, models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='الشركة', db_index=True)
    
    objects = CompanyManager()
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='المنتج')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, null=True, blank=True, verbose_name='الفرع')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, verbose_name='المخزن')
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='سعر التكلفة')
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='سعر البيع')
    wholesale_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='سعر الجملة')
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='تاريخ الإنشاء')
    
    class Meta:
        unique_together = ['product', 'branch', 'warehouse']
        verbose_name = 'سعر المنتج'
        verbose_name_plural = 'أسعار المنتجات'
    
    def __str__(self):
        return f"{self.product.name} - {self.selling_price}"

class StockMovement(CompanyFilterMixin, models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='الشركة', db_index=True)
    
    objects = CompanyManager()
    MOVEMENT_TYPES = [
        ('in', 'إدخال'),
        ('out', 'إخراج'),
        ('transfer', 'نقل'),
        ('adjustment', 'تسوية'),
        ('return', 'مرتجع'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='المنتج')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, null=True, blank=True, verbose_name='المخزن')
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES, verbose_name='نوع الحركة')
    quantity = models.DecimalField(max_digits=10, decimal_places=3, verbose_name='الكمية')
    reference = models.CharField(max_length=200, verbose_name='المرجع')
    notes = models.TextField(blank=True, null=True, verbose_name='ملاحظات')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='تاريخ الحركة')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='أنشئ بواسطة')
    
    class Meta:
        verbose_name = 'حركة مخزون'
        verbose_name_plural = 'حركات المخزون'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.product.name} - {self.get_movement_type_display()}: {self.quantity}"



class SalesRep(CompanyFilterMixin, models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='الشركة', db_index=True)
    
    objects = CompanyManager()
    employee = models.OneToOneField('Employee', on_delete=models.CASCADE, verbose_name='الموظف')
    employee_code = models.CharField(max_length=20, blank=True, verbose_name='كود الموظف')
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='نسبة العمولة %')
    target_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='الهدف الشهري')
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='تاريخ الإنشاء')
    
    class Meta:
        verbose_name = 'مندوب مبيعات'
        verbose_name_plural = 'مندوبي المبيعات'
    
    def __str__(self):
        try:
            return f"{self.employee.user.get_full_name()} - {self.employee_code or self.employee.employee_id}"
        except:
            return f"مندوب مبيعات #{self.id}"
    
    def save(self, *args, **kwargs):
        if not self.employee_code and self.employee:
            self.employee_code = self.employee.employee_id
        super().save(*args, **kwargs)
    
    @property
    def user(self):
        return self.employee.user

class DynamicSetting(CompanyFilterMixin, models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True, verbose_name='الشركة', db_index=True)
    
    objects = CompanyManager()
    key = models.CharField(max_length=100, unique=True, verbose_name='المفتاح')
    value = models.TextField(verbose_name='القيمة')
    description = models.CharField(max_length=255, blank=True, verbose_name='الوصف')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='تاريخ الإنشاء')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')
    
    class Meta:
        verbose_name = 'إعدا�� ديناميكي'
        verbose_name_plural = 'الإعدادات الديناميكية'
    
    def __str__(self):
        return f"{self.key} = {self.value}"

# تحديث نماذج Sale و Purchase لإضافة الحقول المفقودة
Sale.add_to_class('paid_amount', models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='المبلغ المدفوع'))
Sale.add_to_class('remaining_amount', models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='المبلغ المتبقي'))
Sale.add_to_class('notes', models.TextField(blank=True, null=True, verbose_name='ملاحظات'))
Sale.add_to_class('due_date', models.DateField(null=True, blank=True, verbose_name='تاريخ الاستحقاق'))
Sale.add_to_class('confirmed_by', models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='confirmed_sales', verbose_name='أكد بواسطة'))
Sale.add_to_class('confirmed_at', models.DateTimeField(null=True, blank=True, verbose_name='تاريخ التأكيد'))

Purchase.add_to_class('paid_amount', models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='المبلغ المدفوع'))
Purchase.add_to_class('remaining_amount', models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='المبلغ الم��بقي'))
Purchase.add_to_class('notes', models.TextField(blank=True, null=True, verbose_name='ملاحظات'))
Purchase.add_to_class('due_date', models.DateField(null=True, blank=True, verbose_name='تاريخ الاستحقاق'))
Purchase.add_to_class('confirmed_by', models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='confirmed_purchases', verbose_name='أكد بواسطة'))
Purchase.add_to_class('confirmed_at', models.DateTimeField(null=True, blank=True, verbose_name='تاريخ التأكيد'))



# إضافة حقول لجلسة نقاط البيع
POSSession.add_to_class('cash_sales', models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='مبيعات نقدية'))
POSSession.add_to_class('knet_sales', models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='مبيعات كي نت'))
POSSession.add_to_class('mixed_sales', models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='مبيعات مختلطة'))

# إضافة حقول لبيع نقاط البيع
POSSale.add_to_class('customer_name', models.CharField(max_length=200, default='عميل نقدي', verbose_name='اسم العميل'))
POSSale.add_to_class('paid_amount', models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='المبلغ المدفوع'))
POSSale.add_to_class('knet_amount', models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='مبلغ الكي نت'))
POSSale.add_to_class('linked_sale', models.ForeignKey(Sale, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='فاتورة البيع المربوطة'))

# إضافة دوال تأكيد للمرتجعات
def confirm_sale_return_method(self, user):
    return confirm_sale_return(self, user)

def confirm_purchase_return_method(self, user):
    return confirm_purchase_return(self, user)

SaleReturn.confirm_return = confirm_sale_return_method
PurchaseReturn.confirm_return = confirm_purchase_return_method

# إضافة دالة ربط نقاط البيع بالمبيعات
def link_to_sales_method(self):
    if not self.linked_sale:
        sale = create_sale_from_pos(self)
        if sale:
            self.linked_sale = sale
            self.save()
    return self.linked_sale

POSSale.link_to_sales = link_to_sales_method

# إضافة خاصية لعرض طريقة الدفع
@property
def payment_method_display(self):
    if self.cash_amount > 0 and self.knet_amount > 0:
        return 'مختلط'
    elif self.knet_amount > 0:
        return 'كي نت'
    else:
        return 'نقدي'

POSSale.payment_method_display = payment_method_display

# إضافة دالة تأكيد الفاتورة
def confirm_invoice(self, user):
    if self.status == 'confirmed' or self.is_confirmed:
        raise ValidationError('الفاتورة مؤكدة بالفعل')
    
    self.status = 'confirmed'
    self.is_confirmed = True
    self.confirmed_by = user
    self.confirmed_at = timezone.now()
    self.save()
    
    # تحديث المخزون
    for item in self.items.all():
        product = item.product
        if hasattr(product, 'stock'):
            product.stock -= item.quantity
            product.save()
    
    # إنشاء قيد محاسبي
    create_sale_journal_entry(self)
    
    # تحديث رصيد العميل
    update_customer_balance(self.customer)

Sale.confirm_invoice = confirm_invoice

# دوال تأكيد المرتجعات
def confirm_sale_return(sale_return, user):
    """تأكيد مرتجع البيع"""
    if sale_return.status == 'confirmed':
        raise ValidationError('المرتجع مؤكد بالفعل')
    
    sale_return.status = 'confirmed'
    sale_return.confirmed_by = user
    sale_return.confirmed_at = timezone.now()
    sale_return.save()
    
    # تحديث المخزون
    for item in sale_return.items.all():
        product = item.product
        if hasattr(product, 'stock'):
            product.stock = (product.stock or 0) + item.quantity
            product.save()
        
        # تسجيل حركة مخزون
        StockMovement.objects.create(
            company=sale_return.company,
            product=product,
            movement_type='return',
            quantity=item.quantity,
            reference=f'مرتجع بيع #{sale_return.return_number}',
            created_by=user
        )
    
    # إنشاء قيد محاسبي
    create_sale_return_journal_entry(sale_return)

def confirm_purchase_return(purchase_return, user):
    """تأكيد مرتجع الشراء"""
    if purchase_return.status == 'confirmed':
        raise ValidationError('المرتجع مؤكد بالفعل')
    
    purchase_return.status = 'confirmed'
    purchase_return.confirmed_by = user
    purchase_return.confirmed_at = timezone.now()
    purchase_return.save()
    
    # تحديث المخزون
    for item in purchase_return.items.all():
        product = item.product
        if hasattr(product, 'stock'):
            product.stock = (product.stock or 0) - item.quantity
            product.save()
        
        # تسجيل حركة مخزون
        StockMovement.objects.create(
            company=purchase_return.company,
            product=product,
            movement_type='return',
            quantity=-item.quantity,
            reference=f'مرتجع شراء #{purchase_return.return_number}',
            created_by=user
        )
    
    # إنشاء قيد محاسبي
    create_purchase_return_journal_entry(purchase_return)

# دوال إنشاء القيود المحاسبية
def create_sale_return_journal_entry(sale_return):
    """إنشاء قيد محاسبي لمرتجع البيع"""
    try:
        customer_account = get_or_create_customer_account(sale_return.customer)
        sales_account = get_or_create_account('4001', 'مبيعات', 'revenue', sale_return.company)
        sales_return_account = get_or_create_account('4002', 'مرتجعات مبيعات', 'revenue', sale_return.company)
        
        entry = JournalEntry.objects.create(
            company=sale_return.company,
            entry_type='return',
            transaction_type='return',
            description=f'مرتجع بيع #{sale_return.return_number} - {sale_return.customer.name}',
            reference_id=sale_return.id,
            reference_type='sale_return',
            amount=sale_return.total_amount,
            total_amount=sale_return.total_amount,
            created_by=sale_return.created_by
        )
        
        # مرتجعات مبيعات (مدين)
        JournalEntryLine.objects.create(
            company=sale_return.company,
            journal_entry=entry,
            account=sales_return_account,
            debit=sale_return.total_amount,
            credit=0,
            description=f'مرتجع بيع #{sale_return.return_number}'
        )
        
        # العميل (دائن)
        JournalEntryLine.objects.create(
            company=sale_return.company,
            journal_entry=entry,
            account=customer_account,
            debit=0,
            credit=sale_return.total_amount,
            description=f'مرتجع بيع #{sale_return.return_number}'
        )
        
        entry.is_posted = True
        entry.posted_at = timezone.now()
        entry.posted_by = sale_return.created_by
        entry.save()
        
    except Exception as e:
        pass

def create_purchase_return_journal_entry(purchase_return):
    """إنشاء قيد محاسبي لمرتجع الشراء"""
    try:
        supplier_account = get_or_create_supplier_account(purchase_return.supplier)
        purchases_account = get_or_create_account('5001', 'مشتريات', 'expense', purchase_return.company)
        purchase_return_account = get_or_create_account('5002', 'مرتجعات مشتريات', 'expense', purchase_return.company)
        
        entry = JournalEntry.objects.create(
            company=purchase_return.company,
            entry_type='return',
            transaction_type='return',
            description=f'مرتجع شراء #{purchase_return.return_number} - {purchase_return.supplier.name}',
            reference_id=purchase_return.id,
            reference_type='purchase_return',
            amount=purchase_return.total_amount,
            total_amount=purchase_return.total_amount,
            created_by=purchase_return.created_by
        )
        
        # المورد (مدين)
        JournalEntryLine.objects.create(
            company=purchase_return.company,
            journal_entry=entry,
            account=supplier_account,
            debit=purchase_return.total_amount,
            credit=0,
            description=f'مرتجع شراء #{purchase_return.return_number}'
        )
        
        # مرتجعات مشتريات (دائن)
        JournalEntryLine.objects.create(
            company=purchase_return.company,
            journal_entry=entry,
            account=purchase_return_account,
            debit=0,
            credit=purchase_return.total_amount,
            description=f'مرتجع شراء #{purchase_return.return_number}'
        )
        
        entry.is_posted = True
        entry.posted_at = timezone.now()
        entry.posted_by = purchase_return.created_by
        entry.save()
        
    except Exception as e:
        pass

def create_sale_journal_entry(sale):
    """إنشاء قيد محاسبي لفاتورة البيع"""
    try:
        # البحث عن الحسابات المطلوبة
        customer_account = get_or_create_customer_account(sale.customer)
        sales_account = get_or_create_account('4001', 'مبيعات', 'revenue', sale.company)
        
        # إنشاء القيد
        entry = JournalEntry.objects.create(
            company=sale.company,
            entry_type='sale',
            transaction_type='sale',
            description=f'فاتورة بيع #{sale.invoice_number} - {sale.customer.name}',
            reference_id=sale.id,
            reference_type='sale',
            amount=sale.total_amount,
            total_amount=sale.total_amount,
            created_by=sale.created_by
        )
        
        # سطر العميل (مدين)
        JournalEntryLine.objects.create(
            company=sale.company,
            journal_entry=entry,
            account=customer_account,
            debit=sale.total_amount,
            credit=0,
            description=f'فاتورة بيع #{sale.invoice_number}'
        )
        
        # سطر المبيعات (دائن)
        JournalEntryLine.objects.create(
            company=sale.company,
            journal_entry=entry,
            account=sales_account,
            debit=0,
            credit=sale.total_amount,
            description=f'فاتورة بيع #{sale.invoice_number}'
        )
        
        # ترحيل القيد
        entry.is_posted = True
        entry.posted_at = timezone.now()
        entry.posted_by = sale.created_by
        entry.save()
        
    except Exception as e:
        pass  # تجاهل الأخطاء لعدم تعطيل العملية الأساسية

def create_purchase_journal_entry(purchase):
    """إنشاء قيد محاسبي لفاتورة الشراء"""
    try:
        supplier_account = get_or_create_supplier_account(purchase.supplier)
        purchases_account = get_or_create_account('5001', 'مشتريات', 'expense', purchase.company)
        
        entry = JournalEntry.objects.create(
            company=purchase.company,
            entry_type='purchase',
            transaction_type='purchase',
            description=f'فاتورة شراء #{purchase.invoice_number} - {purchase.supplier.name}',
            reference_id=purchase.id,
            reference_type='purchase',
            amount=purchase.total_amount,
            total_amount=purchase.total_amount,
            created_by=purchase.created_by
        )
        
        # سطر المشتريات (مدين)
        JournalEntryLine.objects.create(
            company=purchase.company,
            journal_entry=entry,
            account=purchases_account,
            debit=purchase.total_amount,
            credit=0,
            description=f'فاتورة شراء #{purchase.invoice_number}'
        )
        
        # سطر المورد (دائن)
        JournalEntryLine.objects.create(
            company=purchase.company,
            journal_entry=entry,
            account=supplier_account,
            debit=0,
            credit=purchase.total_amount,
            description=f'فاتورة شراء #{purchase.invoice_number}'
        )
        
        entry.is_posted = True
        entry.posted_at = timezone.now()
        entry.posted_by = purchase.created_by
        entry.save()
        
    except Exception as e:
        pass

def create_payment_journal_entry(payment, payment_type='customer'):
    """إنشاء قيد محاسبي للدفعات"""
    try:
        cash_account = get_or_create_account('1001', 'النقدية', 'asset', payment.customer.company if payment_type == 'customer' else payment.supplier.company)
        
        if payment_type == 'customer':
            customer_account = get_or_create_customer_account(payment.customer)
            description = f'دفعة من العميل {payment.customer.name} - #{payment.payment_number}'
            
            entry = JournalEntry.objects.create(
                company=payment.customer.company,
                entry_type='voucher',
                transaction_type='voucher',
                description=description,
                reference_id=payment.id,
                reference_type='customer_payment',
                amount=payment.amount,
                total_amount=payment.amount,
                created_by=payment.created_by
            )
            
            # النقدية (مدين)
            JournalEntryLine.objects.create(
                company=payment.customer.company,
                journal_entry=entry,
                account=cash_account,
                debit=payment.amount,
                credit=0,
                description=description
            )
            
            # العميل (دائن)
            JournalEntryLine.objects.create(
                company=payment.customer.company,
                journal_entry=entry,
                account=customer_account,
                debit=0,
                credit=payment.amount,
                description=description
            )
            
        else:  # supplier payment
            supplier_account = get_or_create_supplier_account(payment.supplier)
            description = f'دفعة للمورد {payment.supplier.name} - #{payment.payment_number}'
            
            entry = JournalEntry.objects.create(
                company=payment.supplier.company,
                entry_type='voucher',
                transaction_type='voucher',
                description=description,
                reference_id=payment.id,
                reference_type='supplier_payment',
                amount=payment.amount,
                total_amount=payment.amount,
                created_by=payment.created_by
            )
            
            # المورد (مدين)
            JournalEntryLine.objects.create(
                company=payment.supplier.company,
                journal_entry=entry,
                account=supplier_account,
                debit=payment.amount,
                credit=0,
                description=description
            )
            
            # النقدية (دائن)
            JournalEntryLine.objects.create(
                company=payment.supplier.company,
                journal_entry=entry,
                account=cash_account,
                debit=0,
                credit=payment.amount,
                description=description
            )
        
        entry.is_posted = True
        entry.posted_at = timezone.now()
        entry.posted_by = payment.created_by
        entry.save()
        
    except Exception as e:
        pass

def get_or_create_customer_account(customer):
    """الحصول على أو إنشاء حساب العميل"""
    account_code = f'1201{customer.id:03d}'
    account, created = Account.objects.get_or_create(
        company=customer.company,
        account_code=account_code,
        defaults={
            'name': f'العميل - {customer.name}',
            'account_type': 'asset',
            'balance': 0
        }
    )
    return account

def get_or_create_supplier_account(supplier):
    """الحصول على أو إنشاء حساب المورد"""
    account_code = f'2101{supplier.id:03d}'
    account, created = Account.objects.get_or_create(
        company=supplier.company,
        account_code=account_code,
        defaults={
            'name': f'المورد - {supplier.name}',
            'account_type': 'liability',
            'balance': 0
        }
    )
    return account

def get_or_create_account(code, name, account_type, company=None):
    """الحصول على أو إنشاء حساب عام"""
    # الحصول على الشركة الافتراضية إذا لم يتم تمريرها
    if not company:
        try:
            company = Company.objects.first()
            if not company:
                from datetime import date, timedelta
                company = Company.objects.create(
                    code='DEFAULT',
                    name='الشركة الافتراضية',
                    database_name='erp_default',
                    subscription_end=date.today() + timedelta(days=365)
                )
        except Exception:
            # في حالة عدم وجود شركات، إنشاء شركة افتراضية
            from datetime import date, timedelta
            company = Company.objects.create(
                code='DEFAULT',
                name='الشركة الافتراضية',
                database_name='erp_default',
                subscription_end=date.today() + timedelta(days=365)
            )
    
    account, created = Account.objects.get_or_create(
        company=company,
        account_code=code,
        defaults={
            'name': name,
            'account_type': account_type,
            'balance': 0
        }
    )
    return account

# إضافة دالة توليد رقم الفاتورة
def save(self, *args, **kwargs):
    if not self.invoice_number:
        self.invoice_number = self.generate_invoice_number()
    # مزامنة is_confirmed مع status
    if self.status == 'confirmed':
        self.is_confirmed = True
    elif self.status == 'draft':
        self.is_confirmed = False
    # تعيين قيم افتراضية للحقول الجديدة
    if not hasattr(self, 'journal_processed') or self.journal_processed is None:
        self.journal_processed = False
    if not hasattr(self, 'payment_method') or not self.payment_method:
        self.payment_method = 'cash'
    super(Sale, self).save(*args, **kwargs)

def generate_invoice_number(self):
    import datetime
    today = datetime.date.today()
    prefix = f"INV-{today.year}{today.month:02d}{today.day:02d}"
    last_invoice = Sale.objects.filter(invoice_number__startswith=prefix).order_by('-id').first()
    if last_invoice:
        last_number = int(last_invoice.invoice_number.split('-')[-1])
        new_number = last_number + 1
    else:
        new_number = 1
    return f"{prefix}-{new_number:04d}"

Sale.save = save
Sale.generate_invoice_number = generate_invoice_number

# نفس الشيء للمشتريات
def save_purchase(self, *args, **kwargs):
    if not self.invoice_number:
        self.invoice_number = self.generate_purchase_number()
    # تعيين قيم افتراضية للحقول الجديدة
    if not hasattr(self, 'journal_processed') or self.journal_processed is None:
        self.journal_processed = False
    super(Purchase, self).save(*args, **kwargs)

def generate_purchase_number(self):
    import datetime
    today = datetime.date.today()
    prefix = f"PUR-{today.year}{today.month:02d}{today.day:02d}"
    last_invoice = Purchase.objects.filter(invoice_number__startswith=prefix).order_by('-id').first()
    if last_invoice:
        last_number = int(last_invoice.invoice_number.split('-')[-1])
        new_number = last_number + 1
    else:
        new_number = 1
    return f"{prefix}-{new_number:04d}"

Purchase.save = save_purchase
Purchase.generate_purchase_number = generate_purchase_number

# دوال تحديث الأرصدة
def update_customer_balance(customer):
    """تحديث رصيد العميل في دفتر الأستاذ"""
    try:
        account = get_or_create_customer_account(customer)
        # حساب الرصيد من القيود
        from django.db.models import Sum
        debit_sum = JournalEntryLine.objects.filter(account=account).aggregate(Sum('debit'))['debit__sum'] or 0
        credit_sum = JournalEntryLine.objects.filter(account=account).aggregate(Sum('credit'))['credit__sum'] or 0
        account.balance = debit_sum - credit_sum
        account.save()
    except:
        pass

def update_supplier_balance(supplier):
    """تحديث رصيد المورد في دفتر الأستاذ"""
    try:
        account = get_or_create_supplier_account(supplier)
        from django.db.models import Sum
        debit_sum = JournalEntryLine.objects.filter(account=account).aggregate(Sum('debit'))['debit__sum'] or 0
        credit_sum = JournalEntryLine.objects.filter(account=account).aggregate(Sum('credit'))['credit__sum'] or 0
        account.balance = credit_sum - debit_sum
        account.save()
    except:
        pass

# إضافة دالة توليد رقم الإيصال لنقاط البيع
def save_pos_sale(self, *args, **kwargs):
    if not self.receipt_number:
        self.receipt_number = self.generate_receipt_number()
    super(POSSale, self).save(*args, **kwargs)

def generate_receipt_number(self):
    import datetime
    today = datetime.date.today()
    prefix = f"REC-{today.year}{today.month:02d}{today.day:02d}"
    last_receipt = POSSale.objects.filter(receipt_number__startswith=prefix).order_by('-id').first()
    if last_receipt:
        last_number = int(last_receipt.receipt_number.split('-')[-1])
        new_number = last_number + 1
    else:
        new_number = 1
    return f"{prefix}-{new_number:04d}"

POSSale.save = save_pos_sale
POSSale.generate_receipt_number = generate_receipt_number

# إضافة دالة توليد رقم أمر التصنيع
def save_manufacturing(self, *args, **kwargs):
    if not self.order_number:
        self.order_number = self.generate_order_number()
    super(ManufacturingOrder, self).save(*args, **kwargs)

def generate_order_number(self):
    import datetime
    today = datetime.date.today()
    prefix = f"MFG-{today.year}{today.month:02d}{today.day:02d}"
    last_order = ManufacturingOrder.objects.filter(order_number__startswith=prefix).order_by('-id').first()
    if last_order:
        last_number = int(last_order.order_number.split('-')[-1])
        new_number = last_number + 1
    else:
        new_number = 1
    return f"{prefix}-{new_number:04d}"

ManufacturingOrder.save = save_manufacturing
ManufacturingOrder.generate_order_number = generate_order_number



# إضافة حقول مفقودة للحضور
Attendance.add_to_class('overtime_hours', models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='ساعات إضافية'))
Attendance.add_to_class('created_by', models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_attendances', verbose_name='أنشئ بواسطة'))

# إضافة حقول مفقودة للراتب
Salary.add_to_class('overtime_amount', models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='مبلغ الساعات الإضافية'))

# إضافة حقول للتوافق مع الكود القديم
Sale.add_to_class('is_confirmed', models.BooleanField(default=False, verbose_name='مؤكدة'))
Sale.add_to_class('journal_processed', models.BooleanField(default=False, verbose_name='تم معالجة القيد المحاسبي'))
Sale.add_to_class('branch', models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='الفرع'))
Sale.add_to_class('warehouse', models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='المخزن'))
Sale.add_to_class('sales_rep', models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='rep_sales', verbose_name='مندوب المبيعات'))
Sale.add_to_class('payment_method', models.CharField(max_length=20, choices=[('cash', 'نقدي'), ('credit', 'آجل'), ('mixed', 'مختلط')], default='cash', verbose_name='طريقة الدفع'))

# إضافة حقول إضافية للعملاء
Customer.add_to_class('tax_number', models.CharField(max_length=50, blank=True, verbose_name='الرقم الضريبي'))
Customer.add_to_class('commercial_register', models.CharField(max_length=50, blank=True, verbose_name='السجل التجاري'))
Customer.add_to_class('contact_person', models.CharField(max_length=100, blank=True, verbose_name='الشخص المسؤول'))
Customer.add_to_class('payment_terms', models.CharField(max_length=50, blank=True, verbose_name='شروط الدفع'))
Customer.add_to_class('notes', models.TextField(blank=True, verbose_name='ملاحظات'))

# إضافة حقول للمشتريات
Purchase.add_to_class('journal_processed', models.BooleanField(default=False, verbose_name='تم معالجة القيد المحاسبي'))
Purchase.add_to_class('branch', models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='الفرع'))
Purchase.add_to_class('warehouse', models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='المخزن'))

# مساعدات النظام
def generate_barcode():
    import time, random
    return f"{str(int(time.time()))[-6:]}{random.randint(100, 999)}"

def format_currency(amount, symbol='ر.س'):
    return f"{amount:,.2f} {symbol}"

# نموذج القيود اليومية
class JournalEntry(CompanyFilterMixin, models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='الشركة', db_index=True)
    
    objects = CompanyManager()
    ENTRY_TYPES = [
        ('sale', 'بيع'),
        ('purchase', 'شراء'),
        ('return', 'مرتجع'),
        ('salary', 'راتب'),
        ('expense', 'مصروف'),
        ('voucher', 'سند'),
        ('adjustment', 'تسوية'),
        ('depreciation', 'إهلاك'),
        ('inventory', 'جرد'),
    ]
    
    entry_number = models.CharField(max_length=50, unique=True, verbose_name='رقم القيد')
    entry_type = models.CharField(max_length=20, choices=ENTRY_TYPES, verbose_name='نوع القيد')
    transaction_type = models.CharField(max_length=20, choices=ENTRY_TYPES, default='voucher', verbose_name='نوع المعاملة')
    description = models.TextField(verbose_name='الوصف')
    reference_id = models.IntegerField(null=True, blank=True, verbose_name='رقم المرجع')
    reference_type = models.CharField(max_length=50, null=True, blank=True, verbose_name='نوع المرجع')
    amount = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name='المبلغ')
    total_amount = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name='المبلغ الإجمالي')
    is_posted = models.BooleanField(default=False, verbose_name='مرحل')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='تاريخ الإنشاء')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='أنشئ بواسطة')
    posted_at = models.DateTimeField(null=True, blank=True, verbose_name='تاريخ الترحيل')
    posted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='posted_entries', verbose_name='رحل بواسطة')
    
    class Meta:
        verbose_name = 'قيد يومية'
        verbose_name_plural = 'القيود اليومية'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"قيد #{self.entry_number} - {self.description}"
    
    def save(self, *args, **kwargs):
        if not self.entry_number:
            self.entry_number = self.generate_entry_number()
        super().save(*args, **kwargs)
    
    def generate_entry_number(self):
        import datetime
        today = datetime.date.today()
        prefix = f"JE-{today.year}{today.month:02d}{today.day:02d}"
        last_entry = JournalEntry.objects.filter(entry_number__startswith=prefix).order_by('-id').first()
        if last_entry:
            last_number = int(last_entry.entry_number.split('-')[-1])
            new_number = last_number + 1
        else:
            new_number = 1
        return f"{prefix}-{new_number:04d}"

class JournalEntryLine(CompanyFilterMixin, models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='الشركة', db_index=True)
    
    objects = CompanyManager()
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='lines')
    account = models.ForeignKey('Account', on_delete=models.CASCADE)
    debit = models.DecimalField(max_digits=15, decimal_places=3, default=0)
    credit = models.DecimalField(max_digits=15, decimal_places=3, default=0)
    description = models.CharField(max_length=255)
    
    class Meta:
        verbose_name = 'سطر قيد يومية'
        verbose_name_plural = 'أسطر القيود اليومية'
    
    def __str__(self):
        return f"{self.account.name} - مدين: {self.debit} - دائن: {self.credit}"

# نموذج دفعات العملاء
class CustomerPayment(CompanyFilterMixin, models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='الشركة', db_index=True)
    
    objects = CompanyManager()
    PAYMENT_METHODS = [
        ('cash', 'نقدي'),
        ('bank', 'بنكي'),
        ('check', 'شيك'),
        ('card', 'بطاقة'),
    ]
    
    payment_number = models.CharField(max_length=50, unique=True, verbose_name='رقم الدفعة')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name='العميل')
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='المبلغ')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='cash', verbose_name='طريقة الدفع')
    reference_number = models.CharField(max_length=100, blank=True, verbose_name='رقم المرجع')
    notes = models.TextField(blank=True, verbose_name='ملاحظات')
    payment_date = models.DateField(default=timezone.now, verbose_name='تاريخ الدفع')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='تاريخ الإنشاء')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='أنشئ بواسطة')
    
    class Meta:
        verbose_name = 'دفعة عميل'
        verbose_name_plural = 'دفعات العملاء'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"دفعة #{self.payment_number} - {self.customer.name}"
    
    def save(self, *args, **kwargs):
        if not self.payment_number:
            self.payment_number = self.generate_payment_number()
        super().save(*args, **kwargs)
    
    def generate_payment_number(self):
        import datetime
        today = datetime.date.today()
        prefix = f"PAY-{today.year}{today.month:02d}{today.day:02d}"
        last_payment = CustomerPayment.objects.filter(payment_number__startswith=prefix).order_by('-id').first()
        if last_payment:
            last_number = int(last_payment.payment_number.split('-')[-1])
            new_number = last_number + 1
        else:
            new_number = 1
        return f"{prefix}-{new_number:04d}"

class SupplierPayment(CompanyFilterMixin, models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='الشركة', db_index=True)
    
    objects = CompanyManager()
    PAYMENT_METHODS = [
        ('cash', 'نقدي'),
        ('bank', 'بنكي'),
        ('check', 'شيك'),
        ('card', 'بطاقة'),
    ]
    
    payment_number = models.CharField(max_length=50, unique=True, verbose_name='رقم الدفعة')
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, verbose_name='المورد')
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='المبلغ')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='cash', verbose_name='طريقة الدفع')
    reference_number = models.CharField(max_length=100, blank=True, verbose_name='رقم المرجع')
    notes = models.TextField(blank=True, verbose_name='ملاحظات')
    payment_date = models.DateField(default=timezone.now, verbose_name='تاريخ الدفع')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='تاريخ الإنشاء')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='أنشئ بواسطة')
    
    class Meta:
        verbose_name = 'دفعة مورد'
        verbose_name_plural = 'دفعات الموردين'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"دفعة #{self.payment_number} - {self.supplier.name}"
    
    def save(self, *args, **kwargs):
        if not self.payment_number:
            self.payment_number = self.generate_payment_number()
        super().save(*args, **kwargs)
    
    def generate_payment_number(self):
        import datetime
        today = datetime.date.today()
        prefix = f"SPY-{today.year}{today.month:02d}{today.day:02d}"
        last_payment = SupplierPayment.objects.filter(payment_number__startswith=prefix).order_by('-id').first()
        if last_payment:
            last_number = int(last_payment.payment_number.split('-')[-1])
            new_number = last_number + 1
        else:
            new_number = 1
        return f"{prefix}-{new_number:04d}"
