# تحسين قاعدة البيانات - الفهارس والقيود
from django.db import models

class DatabaseOptimization:
    """
    إضافة الفهارس والقيود المطلوبة لتحسين الأداء
    """
    
    # فهارس مطلوبة
    REQUIRED_INDEXES = [
        # فهارس للبحث السريع
        ('core_product', ['name', 'barcode', 'category']),
        ('core_customer', ['name', 'phone']),
        ('core_supplier', ['name', 'phone']),
        ('core_sale', ['invoice_number', 'created_at', 'status']),
        ('core_purchase', ['invoice_number', 'created_at', 'status']),
        
        # فهارس للعلاقات
        ('core_sale', ['customer_id', 'sales_rep_id', 'branch_id']),
        ('core_purchase', ['supplier_id', 'branch_id']),
        ('core_saleitem', ['sale_id', 'product_id']),
        ('core_purchaseitem', ['purchase_id', 'product_id']),
        
        # فهارس للتواريخ
        ('core_sale', ['created_at']),
        ('core_purchase', ['created_at']),
        ('core_attendance', ['date', 'employee_id']),
        ('core_salary', ['month', 'year', 'employee_id']),
    ]
    
    # قيود التكامل
    INTEGRITY_CONSTRAINTS = [
        # قيود فريدة
        ('core_customer', ['company_id', 'phone']),  # رقم هاتف فريد لكل شركة
        ('core_supplier', ['company_id', 'phone']),  # رقم هاتف فريد لكل شركة
        ('core_product', ['company_id', 'barcode']),  # باركود فريد لكل شركة
        ('core_account', ['company_id', 'account_code']),  # كود حساب فريد لكل شركة
        
        # قيود التحقق
        ('core_sale', 'CHECK (total_amount >= 0)'),  # المبلغ الإجمالي لا يمكن أن يكون سالب
        ('core_purchase', 'CHECK (total_amount >= 0)'),  # المبلغ الإجمالي لا يمكن أن يكون سالب
        ('core_product', 'CHECK (price >= 0)'),  # السعر لا يمكن أن يكون سالب
        ('core_product', 'CHECK (stock >= 0)'),  # المخزون لا يمكن أن يكون سالب
    ]
    
    # مفاتيح أجنبية مطلوبة
    FOREIGN_KEYS = [
        # ربط جميع النماذج بالشركة
        ('core_customer', 'company_id', 'core_company', 'id'),
        ('core_supplier', 'company_id', 'core_company', 'id'),
        ('core_product', 'company_id', 'core_company', 'id'),
        ('core_sale', 'company_id', 'core_company', 'id'),
        ('core_purchase', 'company_id', 'core_company', 'id'),
        
        # ربط المبيعات والمشتريات بالفروع والمخازن
        ('core_sale', 'branch_id', 'core_branch', 'id'),
        ('core_sale', 'warehouse_id', 'core_warehouse', 'id'),
        ('core_purchase', 'branch_id', 'core_branch', 'id'),
        ('core_purchase', 'warehouse_id', 'core_warehouse', 'id'),
        
        # ربط المبيعات بمناديب المبيعات
        ('core_sale', 'sales_rep_id', 'core_salesrep', 'id'),
    ]