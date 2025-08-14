# نماذج إدارة صاحب البرنامج الرئيسية
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal
import uuid
from datetime import date, timedelta

class MasterAdmin(models.Model):
    """صاحب البرنامج الرئيسي"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name='المستخدم')
    full_name = models.CharField(max_length=200, verbose_name='الاسم الكامل')
    phone = models.CharField(max_length=20, verbose_name='رقم الهاتف')
    email = models.EmailField(verbose_name='البريد الإلكتروني')
    is_super_admin = models.BooleanField(default=True, verbose_name='مدير عام')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='تاريخ الإنشاء')
    
    class Meta:
        verbose_name = 'صاحب البرنامج'
        verbose_name_plural = 'أصحاب البرنامج'
    
    def __str__(self):
        return self.full_name

class CompanySubscription(models.Model):
    """اشتراكات الشركات"""
    SUBSCRIPTION_TYPES = [
        ('basic', 'أساسي'),
        ('standard', 'قياسي'),
        ('premium', 'متميز'),
        ('enterprise', 'مؤسسي'),
    ]
    
    PAYMENT_STATUS = [
        ('pending', 'في الانتظار'),
        ('paid', 'مدفوع'),
        ('overdue', 'متأخر'),
        ('cancelled', 'ملغي'),
    ]
    
    company = models.ForeignKey('Company', on_delete=models.CASCADE, verbose_name='الشركة')
    subscription_type = models.CharField(max_length=20, choices=SUBSCRIPTION_TYPES, verbose_name='نوع الاشتراك')
    start_date = models.DateField(verbose_name='تاريخ البداية')
    end_date = models.DateField(verbose_name='تاريخ الانتهاء')
    monthly_fee = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='الرسوم الشهرية')
    yearly_fee = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='الرسوم السنوية')
    max_users = models.IntegerField(default=5, verbose_name='الحد الأقصى للمستخدمين')
    max_branches = models.IntegerField(default=1, verbose_name='الحد الأقصى للفروع')
    max_warehouses = models.IntegerField(default=3, verbose_name='الحد الأقصى للمخازن')
    storage_limit_gb = models.IntegerField(default=1, verbose_name='حد التخزين (جيجا)')
    features = models.JSONField(default=dict, verbose_name='الميزات المتاحة')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending', verbose_name='حالة الدفع')
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    auto_renew = models.BooleanField(default=False, verbose_name='تجديد تلقائي')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='تاريخ الإنشاء')
    
    class Meta:
        verbose_name = 'اشتراك شركة'
        verbose_name_plural = 'اشتراكات الشركات'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.company.name} - {self.get_subscription_type_display()}"
    
    @property
    def is_expired(self):
        return self.end_date < date.today()
    
    @property
    def days_remaining(self):
        if self.is_expired:
            return 0
        return (self.end_date - date.today()).days
    
    def extend_subscription(self, months=1):
        """تمديد الاشتراك"""
        if self.is_expired:
            self.start_date = date.today()
            self.end_date = date.today() + timedelta(days=30 * months)
        else:
            self.end_date += timedelta(days=30 * months)
        self.save()

class CompanyPayment(models.Model):
    """دفعات الشركات"""
    PAYMENT_METHODS = [
        ('cash', 'نقدي'),
        ('bank_transfer', 'تحويل بنكي'),
        ('credit_card', 'بطاقة ائتمان'),
        ('check', 'شيك'),
    ]
    
    subscription = models.ForeignKey(CompanySubscription, on_delete=models.CASCADE, verbose_name='الاشتراك')
    payment_number = models.CharField(max_length=50, unique=True, verbose_name='رقم الدفعة')
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='المبلغ')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, verbose_name='طريقة الدفع')
    payment_date = models.DateField(default=date.today, verbose_name='تاريخ الدفع')
    reference_number = models.CharField(max_length=100, blank=True, verbose_name='رقم المرجع')
    notes = models.TextField(blank=True, verbose_name='ملاحظات')
    is_confirmed = models.BooleanField(default=False, verbose_name='مؤكد')
    confirmed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='أكد بواسطة')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='تاريخ الإنشاء')
    
    class Meta:
        verbose_name = 'دفعة شركة'
        verbose_name_plural = 'دفعات الشركات'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"دفعة #{self.payment_number} - {self.subscription.company.name}"
    
    def save(self, *args, **kwargs):
        if not self.payment_number:
            self.payment_number = self.generate_payment_number()
        super().save(*args, **kwargs)
    
    def generate_payment_number(self):
        today = date.today()
        prefix = f"PAY-{today.year}{today.month:02d}{today.day:02d}"
        last_payment = CompanyPayment.objects.filter(payment_number__startswith=prefix).order_by('-id').first()
        if last_payment:
            last_number = int(last_payment.payment_number.split('-')[-1])
            new_number = last_number + 1
        else:
            new_number = 1
        return f"{prefix}-{new_number:04d}"

class SystemSettings(models.Model):
    """إعدادات النظام العامة"""
    SETTING_TYPES = [
        ('string', 'نص'),
        ('integer', 'رقم صحيح'),
        ('decimal', 'رقم عشري'),
        ('boolean', 'صح/خطأ'),
        ('json', 'JSON'),
    ]
    
    key = models.CharField(max_length=100, unique=True, verbose_name='المفتاح')
    value = models.TextField(verbose_name='القيمة')
    setting_type = models.CharField(max_length=20, choices=SETTING_TYPES, default='string', verbose_name='نوع الإعداد')
    description = models.CharField(max_length=255, verbose_name='الوصف')
    is_system = models.BooleanField(default=False, verbose_name='إعداد نظام')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='تاريخ الإنشاء')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')
    
    class Meta:
        verbose_name = 'إعداد النظام'
        verbose_name_plural = 'إعدادات النظام'
    
    def __str__(self):
        return f"{self.key} = {self.value}"
    
    def get_value(self):
        """الحصول على القيمة بالنوع المناسب"""
        if self.setting_type == 'boolean':
            return str(self.value).lower() in ['true', '1', 'yes', 'نعم']
        elif self.setting_type == 'integer':
            try:
                return int(self.value)
            except (ValueError, TypeError):
                return 0
        elif self.setting_type == 'decimal':
            try:
                return Decimal(str(self.value))
            except (ValueError, TypeError):
                return Decimal('0.0')
        elif self.setting_type == 'json':
            import json
            try:
                return json.loads(self.value)
            except (json.JSONDecodeError, TypeError):
                return {}
        else:
            return str(self.value)

class CompanyDatabase(models.Model):
    """قواعد بيانات الشركات"""
    company = models.OneToOneField('Company', on_delete=models.CASCADE, verbose_name='الشركة')
    database_name = models.CharField(max_length=100, unique=True, verbose_name='اسم قاعدة البيانات')
    database_size_mb = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='حجم قاعدة البيانات (ميجا)')
    last_backup = models.DateTimeField(null=True, blank=True, verbose_name='آخر نسخة احتياطية')
    backup_frequency = models.CharField(max_length=20, choices=[
        ('daily', 'يومي'),
        ('weekly', 'أسبوعي'),
        ('monthly', 'شهري'),
    ], default='weekly', verbose_name='تكرار النسخ الاحتياطي')
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='تاريخ الإنشاء')
    
    class Meta:
        verbose_name = 'قاعدة بيانات الشركة'
        verbose_name_plural = 'قواعد بيانات الشركات'
    
    def __str__(self):
        return f"{self.company.name} - {self.database_name}"

class SystemAuditLog(models.Model):
    """سجل مراجعة النظام"""
    ACTION_TYPES = [
        ('create', 'إنشاء'),
        ('update', 'تحديث'),
        ('delete', 'حذف'),
        ('login', 'تسجيل دخول'),
        ('logout', 'تسجيل خروج'),
        ('payment', 'دفعة'),
        ('subscription', 'اشتراك'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='المستخدم')
    company = models.ForeignKey('Company', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='الشركة')
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES, verbose_name='نوع العملية')
    model_name = models.CharField(max_length=100, verbose_name='اسم النموذج')
    object_id = models.IntegerField(null=True, blank=True, verbose_name='معرف الكائن')
    description = models.TextField(verbose_name='الوصف')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='عنوان IP')
    user_agent = models.TextField(blank=True, verbose_name='معلومات المتصفح')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='تاريخ العملية')
    
    class Meta:
        verbose_name = 'سجل مراجعة'
        verbose_name_plural = 'سجلات المراجعة'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user} - {self.get_action_type_display()} - {self.model_name}"

class CompanyUsageStats(models.Model):
    """إحصائيات استخدام الشركات"""
    company = models.ForeignKey('Company', on_delete=models.CASCADE, verbose_name='الشركة')
    date = models.DateField(verbose_name='التاريخ')
    active_users = models.IntegerField(default=0, verbose_name='المستخدمين النشطين')
    total_sales = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='إجمالي المبيعات')
    total_purchases = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='إجمالي المشتريات')
    total_invoices = models.IntegerField(default=0, verbose_name='عدد الفواتير')
    database_size_mb = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='حجم قاعدة البيانات')
    storage_used_mb = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='التخزين المستخدم')
    
    class Meta:
        verbose_name = 'إحصائيات الاستخدام'
        verbose_name_plural = 'إحصائيات الاستخدام'
        unique_together = ['company', 'date']
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.company.name} - {self.date}"

class MasterWarehouse(models.Model):
    """مخازن صاحب البرنامج الرئيسية"""
    name = models.CharField(max_length=200, verbose_name='اسم المخزن')
    code = models.CharField(max_length=20, unique=True, verbose_name='كود المخزن')
    location = models.CharField(max_length=200, verbose_name='الموقع')
    manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='المدير')
    capacity = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='السعة')
    current_usage = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='الاستخدام الحالي')
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='تاريخ الإنشاء')
    
    class Meta:
        verbose_name = 'مخزن رئيسي'
        verbose_name_plural = 'المخازن الرئيسية'
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    @property
    def usage_percentage(self):
        if self.capacity > 0:
            return (self.current_usage / self.capacity) * 100
        return 0

class GlobalProduct(models.Model):
    """منتجات عامة لجميع الشركات"""
    name = models.CharField(max_length=200, verbose_name='اسم المنتج')
    barcode = models.CharField(max_length=50, unique=True, verbose_name='الباركود')
    category = models.CharField(max_length=100, verbose_name='الفئة')
    brand = models.CharField(max_length=100, verbose_name='الماركة')
    description = models.TextField(blank=True, verbose_name='الوصف')
    image = models.ImageField(upload_to='global_products/', blank=True, null=True, verbose_name='الصورة')
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='تاريخ الإنشاء')
    
    class Meta:
        verbose_name = 'منتج عام'
        verbose_name_plural = 'المنتجات العامة'
    
    def __str__(self):
        return self.name

class CompanyProductMapping(models.Model):
    """ربط المنتجات العامة بالشركات"""
    company = models.ForeignKey('Company', on_delete=models.CASCADE, verbose_name='الشركة')
    global_product = models.ForeignKey(GlobalProduct, on_delete=models.CASCADE, verbose_name='المنتج العام')
    local_product = models.ForeignKey('Product', on_delete=models.CASCADE, verbose_name='المنتج المحلي')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='السعر')
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='سعر التكلفة')
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='تاريخ الإنشاء')
    
    class Meta:
        verbose_name = 'ربط منتج'
        verbose_name_plural = 'ربط المنتجات'
        unique_together = ['company', 'global_product']
    
    def __str__(self):
        return f"{self.company.name} - {self.global_product.name}"

class SystemNotification(models.Model):
    """إشعارات النظام"""
    NOTIFICATION_TYPES = [
        ('subscription_expiry', 'انتهاء اشتراك'),
        ('payment_due', 'دفعة مستحقة'),
        ('system_update', 'تحديث النظام'),
        ('maintenance', 'صيانة'),
        ('security', 'أمان'),
    ]
    
    title = models.CharField(max_length=200, verbose_name='العنوان')
    message = models.TextField(verbose_name='الرسالة')
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES, verbose_name='نوع الإشعار')
    target_companies = models.ManyToManyField('Company', blank=True, verbose_name='الشركات المستهدفة')
    is_global = models.BooleanField(default=False, verbose_name='إشعار عام')
    is_read = models.BooleanField(default=False, verbose_name='مقروء')
    priority = models.CharField(max_length=10, choices=[
        ('low', 'منخفض'),
        ('medium', 'متوسط'),
        ('high', 'عالي'),
        ('urgent', 'عاجل'),
    ], default='medium', verbose_name='الأولوية')
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name='ينتهي في')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='تاريخ الإنشاء')
    
    class Meta:
        verbose_name = 'إشعار النظام'
        verbose_name_plural = 'إشعارات النظام'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title

class CompanyBackup(models.Model):
    """نسخ احتياطية للشركات"""
    company = models.ForeignKey('Company', on_delete=models.CASCADE, verbose_name='الشركة')
    backup_name = models.CharField(max_length=200, verbose_name='اسم النسخة')
    file_path = models.CharField(max_length=500, verbose_name='مسار الملف')
    file_size_mb = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='حجم الملف (ميجا)')
    backup_type = models.CharField(max_length=20, choices=[
        ('full', 'كامل'),
        ('incremental', 'تزايدي'),
        ('differential', 'تفاضلي'),
    ], default='full', verbose_name='نوع النسخة')
    is_automated = models.BooleanField(default=False, verbose_name='تلقائي')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='تاريخ الإنشاء')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='أنشئ بواسطة')
    
    class Meta:
        verbose_name = 'نسخة احتياطية'
        verbose_name_plural = 'النسخ الاحتياطية'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.company.name} - {self.backup_name}"

# إضافة حقول جديدة لنموذج الشركة الموجود
def extend_company_model():
    """إضافة حقول جديدة لنموذج الشركة"""
    from .models import Company
    
    # إضافة حقول إضافية
    Company.add_to_class('owner', models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_companies', verbose_name='المالك'))
    Company.add_to_class('max_users', models.IntegerField(default=5, verbose_name='الحد الأقصى للمستخدمين'))
    Company.add_to_class('max_branches', models.IntegerField(default=1, verbose_name='الحد الأقصى للفروع'))
    Company.add_to_class('max_warehouses', models.IntegerField(default=3, verbose_name='الحد الأقصى للمخازن'))
    Company.add_to_class('storage_limit_gb', models.IntegerField(default=1, verbose_name='حد التخزين (جيجا)'))
    Company.add_to_class('features', models.JSONField(default=dict, verbose_name='الميزات المتاحة'))
    Company.add_to_class('last_login', models.DateTimeField(null=True, blank=True, verbose_name='آخر تسجيل دخول'))
    Company.add_to_class('total_sales', models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='إجمالي المبيعات'))
    Company.add_to_class('total_users', models.IntegerField(default=0, verbose_name='عدد المستخدمين'))
    Company.add_to_class('status', models.CharField(max_length=20, choices=[
        ('active', 'نشط'),
        ('suspended', 'معلق'),
        ('expired', 'منتهي'),
        ('trial', 'تجريبي'),
    ], default='active', verbose_name='الحالة'))

# تشغيل دالة التوسيع
try:
    extend_company_model()
except:
    pass  # تجاهل الأخطاء في حالة عدم وجود النموذج