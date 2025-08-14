from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Company, Product, Purchase, Sale, Customer, Supplier, Branch, Warehouse, UserProfile, Setting, POSSession, POSSale, ManufacturingOrder, Attendance, Salary, Permission

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active', 'subscription_end')
    list_filter = ('is_active', 'subscription_type')
    search_fields = ('name', 'code')
    ordering = ('name',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'barcode', 'category', 'company', 'is_active')
    list_filter = ('category', 'company', 'is_active')
    search_fields = ('name', 'barcode', 'category')
    ordering = ('name',)

@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'supplier', 'total_amount', 'status', 'created_by', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('invoice_number', 'supplier__name')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'customer', 'total_amount', 'status', 'created_by', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('invoice_number', 'customer__name')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email', 'credit_limit', 'address', 'opening_balance')

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email', 'address', 'opening_balance')

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'company')

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'branch')

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'company', 'default_branch', 'default_warehouse', 'is_active')
    list_filter = ('company', 'default_branch', 'is_active')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    ordering = ('user__username',)

@admin.register(Setting)
class SettingAdmin(admin.ModelAdmin):
    list_display = ('setting_display', 'value_display', 'category_display', 'scope_display', 'type_display', 'updated_at')
    list_filter = ('category', 'setting_type', 'is_system', 'is_global', 'company', 'branch')
    search_fields = ('key', 'value', 'description')
    list_per_page = 25
    ordering = ('category', 'key')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('معلومات الإعداد الأساسية', {
            'fields': ('key', 'value', 'setting_type', 'category', 'description'),
            'classes': ('wide',)
        }),
        ('النطاق والصلاحيات', {
            'fields': ('company', 'branch', 'is_global', 'is_system', 'is_required'),
            'classes': ('collapse',)
        }),
        ('إعدادات متقدمة', {
            'fields': ('default_value', 'validation_rules'),
            'classes': ('collapse',)
        }),
        ('معلومات النظام', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('company', 'branch', 'created_by')
    
    def setting_display(self, obj):
        icon = obj.get_category_icon(obj.category)
        return f"{icon} {obj.key}"
    setting_display.short_description = '🔑 مفتاح الإعداد'
    setting_display.admin_order_field = 'key'
    
    def value_display(self, obj):
        return obj.get_display_value()
    value_display.short_description = '💾 القيمة'
    
    def category_display(self, obj):
        icon = obj.get_category_icon(obj.category)
        return f"{icon} {obj.category}"
    category_display.short_description = '📋 الفئة'
    category_display.admin_order_field = 'category'
    
    def scope_display(self, obj):
        if obj.is_global:
            return '🌍 عام'
        elif obj.company and obj.branch:
            return f'🏢 {obj.company.name} - 🏦 {obj.branch.name}'
        elif obj.company:
            return f'🏢 {obj.company.name}'
        else:
            return '🌍 غير محدد'
    scope_display.short_description = '🎯 النطاق'
    
    def type_display(self, obj):
        type_icons = {
            'string': '📝',
            'integer': '🔢',
            'decimal': '📊',
            'boolean': '✅',
            'json': '📦',
            'file': '📁',
            'image': '🖼️',
            'color': '🎨',
            'email': '📧',
            'url': '🔗',
            'phone': '📞'
        }
        icon = type_icons.get(obj.setting_type, '📋')
        return f"{icon} {obj.get_setting_type_display()}"
    type_display.short_description = '🔍 النوع'
    type_display.admin_order_field = 'setting_type'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def get_list_display_links(self, request, list_display):
        return ('setting_display',)
    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        
        # إحصائيات الإعدادات
        from django.db.models import Count
        stats = {
            'total_settings': self.get_queryset(request).count(),
            'by_category': dict(self.get_queryset(request).values_list('category').annotate(Count('category'))),
            'by_type': dict(self.get_queryset(request).values_list('setting_type').annotate(Count('setting_type'))),
            'system_settings': self.get_queryset(request).filter(is_system=True).count(),
            'global_settings': self.get_queryset(request).filter(is_global=True).count(),
        }
        extra_context['settings_stats'] = stats
        
        return super().changelist_view(request, extra_context)
    
    class Media:
        css = {
            'all': ('admin/css/settings_admin.css',)
        }
        js = ('admin/js/settings_admin.js',)

@admin.register(POSSession)
class POSSessionAdmin(admin.ModelAdmin):
    list_display = ('session_number', 'cashier', 'status', 'opened_at')

@admin.register(POSSale)
class POSSaleAdmin(admin.ModelAdmin):
    list_display = ('receipt_number', 'session', 'total_amount', 'payment_method')

@admin.register(ManufacturingOrder)
class ManufacturingOrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'product', 'quantity', 'status')

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'date', 'check_in', 'check_out', 'status')

@admin.register(Salary)
class SalaryAdmin(admin.ModelAdmin):
    list_display = ('employee', 'month', 'year', 'net_salary', 'status')

@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'screen', 'can_view', 'can_add', 'can_edit', 'can_delete', 'can_confirm', 'can_print')
    list_filter = ('screen', 'can_view', 'can_add', 'can_edit', 'can_delete')
    search_fields = ('user__username', 'screen')
    ordering = ('user__username', 'screen')
    
    fieldsets = (
        ('المستخدم والشاشة', {
            'fields': ('user', 'screen')
        }),
        ('الصلاحيات الأساسية', {
            'fields': ('can_view', 'can_add', 'can_edit', 'can_delete')
        }),
        ('صلاحيات إضافية', {
            'fields': ('can_confirm', 'can_print', 'can_export'),
            'classes': ('collapse',)
        }),
        ('النطاق', {
            'fields': ('branch', 'warehouse'),
            'classes': ('collapse',)
        }),
    )
