"""
نظام ربط المخزون بالمحاسبة - محدث تلقائيًا
يحقق جرد مستمر مع تأثير لحظي على التقارير
"""

from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from .models import Product, JournalEntry, JournalEntryLine, Account, StockMovement

class InventoryAccountingManager:
    """مدير ربط المخزون بالحسابات - قيود يومية تلقائية"""
    
    @staticmethod
    def get_or_create_account(code, name, account_type):
        """إنشاء أو جلب حساب محاسبي"""
        account, created = Account.objects.get_or_create(
            account_code=code,
            defaults={
                'name': name,
                'account_type': account_type,
                'balance': 0
            }
        )
        return account
    
    @staticmethod
    @transaction.atomic
    def process_sale(sale_items, user):
        """معالجة البيع - خصم المخزون + قيود يومية"""
        total_cost = Decimal('0')
        total_revenue = Decimal('0')
        
        # الحسابات المطلوبة
        inventory_account = InventoryAccountingManager.get_or_create_account(
            '1301', 'مخزون البضاعة', 'asset'
        )
        cogs_account = InventoryAccountingManager.get_or_create_account(
            '5101', 'تكلفة البضاعة المباعة', 'expense'
        )
        sales_account = InventoryAccountingManager.get_or_create_account(
            '4001', 'المبيعات', 'revenue'
        )
        receivables_account = InventoryAccountingManager.get_or_create_account(
            '1201', 'العملاء', 'asset'
        )
        
        for item in sale_items:
            product = item.product
            quantity = item.quantity
            unit_price = item.unit_price
            cost_price = product.cost_price or Decimal('0')
            
            # تحديث المخزون فورًا
            product.stock = (product.stock or 0) - quantity
            product.save()
            
            # تسجيل حركة المخزون
            StockMovement.objects.create(
                product=product,
                movement_type='out',
                quantity=quantity,
                reference=f'بيع - فاتورة #{item.sale.invoice_number}',
                created_by=user
            )
            
            # حساب التكاليف والإيرادات
            item_cost = quantity * cost_price
            item_revenue = quantity * unit_price
            total_cost += item_cost
            total_revenue += item_revenue
        
        # إنشاء قيد المبيعات
        sales_entry = JournalEntry.objects.create(
            entry_type='sale',
            description=f'مبيعات - فاتورة #{sale_items[0].sale.invoice_number}',
            total_amount=total_revenue,
            created_by=user,
            is_posted=True,
            posted_at=timezone.now(),
            posted_by=user
        )
        
        # العملاء (مدين)
        JournalEntryLine.objects.create(
            journal_entry=sales_entry,
            account=receivables_account,
            debit=total_revenue,
            credit=0,
            description='مبيعات'
        )
        
        # المبيعات (دائن)
        JournalEntryLine.objects.create(
            journal_entry=sales_entry,
            account=sales_account,
            debit=0,
            credit=total_revenue,
            description='مبيعات'
        )
        
        # قيد تكلفة البضاعة المباعة
        if total_cost > 0:
            cogs_entry = JournalEntry.objects.create(
                entry_type='sale',
                description=f'تكلفة البضاعة المباعة - فاتورة #{sale_items[0].sale.invoice_number}',
                total_amount=total_cost,
                created_by=user,
                is_posted=True,
                posted_at=timezone.now(),
                posted_by=user
            )
            
            # تكلفة البضاعة المباعة (مدين)
            JournalEntryLine.objects.create(
                journal_entry=cogs_entry,
                account=cogs_account,
                debit=total_cost,
                credit=0,
                description='تكلفة البضاعة المباعة'
            )
            
            # مخزون البضاعة (دائن)
            JournalEntryLine.objects.create(
                journal_entry=cogs_entry,
                account=inventory_account,
                debit=0,
                credit=total_cost,
                description='تكلفة البضاعة المباعة'
            )
        
        return sales_entry
    
    @staticmethod
    @transaction.atomic
    def process_purchase(purchase_items, user):
        """معالجة الشراء - إضافة للمخزون + قيود يومية"""
        total_amount = Decimal('0')
        
        # الحسابات المطلوبة
        inventory_account = InventoryAccountingManager.get_or_create_account(
            '1301', 'مخزون البضاعة', 'asset'
        )
        payables_account = InventoryAccountingManager.get_or_create_account(
            '2101', 'الموردين', 'liability'
        )
        
        for item in purchase_items:
            product = item.product
            quantity = item.quantity
            unit_price = item.unit_price
            
            # تحديث المخزون فورًا
            product.stock = (product.stock or 0) + quantity
            product.cost_price = unit_price  # تحديث سعر التكلفة
            product.save()
            
            # تسجيل حركة المخزون
            StockMovement.objects.create(
                product=product,
                movement_type='in',
                quantity=quantity,
                reference=f'شراء - فاتورة #{item.purchase.invoice_number}',
                created_by=user
            )
            
            total_amount += quantity * unit_price
        
        # إنشاء قيد الشراء
        purchase_entry = JournalEntry.objects.create(
            entry_type='purchase',
            description=f'مشتريات - فاتورة #{purchase_items[0].purchase.invoice_number}',
            total_amount=total_amount,
            created_by=user,
            is_posted=True,
            posted_at=timezone.now(),
            posted_by=user
        )
        
        # مخزون البضاعة (مدين)
        JournalEntryLine.objects.create(
            journal_entry=purchase_entry,
            account=inventory_account,
            debit=total_amount,
            credit=0,
            description='مشتريات'
        )
        
        # الموردين (دائن)
        JournalEntryLine.objects.create(
            journal_entry=purchase_entry,
            account=payables_account,
            debit=0,
            credit=total_amount,
            description='مشتريات'
        )
        
        return purchase_entry
    
    @staticmethod
    @transaction.atomic
    def process_sale_return(return_items, user):
        """معالجة مرتجع البيع - عكس الحركة + قيد عكسي"""
        total_cost = Decimal('0')
        total_amount = Decimal('0')
        
        # الحسابات المطلوبة
        inventory_account = InventoryAccountingManager.get_or_create_account(
            '1301', 'مخزون البضاعة', 'asset'
        )
        cogs_account = InventoryAccountingManager.get_or_create_account(
            '5101', 'تكلفة البضاعة المباعة', 'expense'
        )
        sales_return_account = InventoryAccountingManager.get_or_create_account(
            '4002', 'مرتجعات المبيعات', 'revenue'
        )
        receivables_account = InventoryAccountingManager.get_or_create_account(
            '1201', 'العملاء', 'asset'
        )
        
        for item in return_items:
            product = item.product
            quantity = item.quantity
            unit_price = item.unit_price
            cost_price = product.cost_price or Decimal('0')
            
            # إرجاع الكمية للمخزون
            product.stock = (product.stock or 0) + quantity
            product.save()
            
            # تسجيل حركة المخزون
            StockMovement.objects.create(
                product=product,
                movement_type='return',
                quantity=quantity,
                reference=f'مرتجع بيع #{item.sale_return.return_number}',
                created_by=user
            )
            
            total_cost += quantity * cost_price
            total_amount += quantity * unit_price
        
        # قيد عكسي للمبيعات
        return_entry = JournalEntry.objects.create(
            entry_type='return',
            description=f'مرتجع بيع #{return_items[0].sale_return.return_number}',
            total_amount=total_amount,
            created_by=user,
            is_posted=True,
            posted_at=timezone.now(),
            posted_by=user
        )
        
        # مرتجعات المبيعات (مدين)
        JournalEntryLine.objects.create(
            journal_entry=return_entry,
            account=sales_return_account,
            debit=total_amount,
            credit=0,
            description='مرتجع بيع'
        )
        
        # العملاء (دائن)
        JournalEntryLine.objects.create(
            journal_entry=return_entry,
            account=receivables_account,
            debit=0,
            credit=total_amount,
            description='مرتجع بيع'
        )
        
        # قيد عكسي لتكلفة البضاعة
        if total_cost > 0:
            cost_entry = JournalEntry.objects.create(
                entry_type='return',
                description=f'عكس تكلفة البضاعة - مرتجع #{return_items[0].sale_return.return_number}',
                total_amount=total_cost,
                created_by=user,
                is_posted=True,
                posted_at=timezone.now(),
                posted_by=user
            )
            
            # مخزون البضاعة (مدين)
            JournalEntryLine.objects.create(
                journal_entry=cost_entry,
                account=inventory_account,
                debit=total_cost,
                credit=0,
                description='عكس تكلفة البضاعة'
            )
            
            # تكلفة البضاعة المباعة (دائن)
            JournalEntryLine.objects.create(
                journal_entry=cost_entry,
                account=cogs_account,
                debit=0,
                credit=total_cost,
                description='عكس تكلفة البضاعة'
            )
        
        return return_entry
    
    @staticmethod
    @transaction.atomic
    def process_inventory_adjustment(product, actual_quantity, user, notes=""):
        """معالجة الجرد - تسجيل الفروقات كخسارة أو ربح"""
        current_quantity = product.stock or 0
        difference = actual_quantity - current_quantity
        
        if difference == 0:
            return None  # لا يوجد فرق
        
        # تحديث المخزون
        product.stock = actual_quantity
        product.save()
        
        # الحسابات المطلوبة
        inventory_account = InventoryAccountingManager.get_or_create_account(
            '1301', 'مخزون البضاعة', 'asset'
        )
        
        if difference > 0:
            # زيادة في المخزون - ربح جرد
            adjustment_account = InventoryAccountingManager.get_or_create_account(
                '4003', 'أرباح الجرد', 'revenue'
            )
            movement_type = 'adjustment'
            description = f'ربح جرد - {product.name}'
        else:
            # نقص في المخزون - خسارة جرد
            adjustment_account = InventoryAccountingManager.get_or_create_account(
                '5102', 'خسائر الجرد', 'expense'
            )
            movement_type = 'adjustment'
            description = f'خسارة جرد - {product.name}'
            difference = abs(difference)
        
        # تسجيل حركة المخزون
        StockMovement.objects.create(
            product=product,
            movement_type=movement_type,
            quantity=difference,
            reference=f'جرد - {product.name}',
            notes=notes,
            created_by=user
        )
        
        # إنشاء قيد الجرد
        cost_value = difference * (product.cost_price or Decimal('0'))
        
        adjustment_entry = JournalEntry.objects.create(
            entry_type='adjustment',
            description=description,
            total_amount=cost_value,
            created_by=user,
            is_posted=True,
            posted_at=timezone.now(),
            posted_by=user
        )
        
        if actual_quantity > current_quantity:
            # ربح جرد
            # مخزون البضاعة (مدين)
            JournalEntryLine.objects.create(
                journal_entry=adjustment_entry,
                account=inventory_account,
                debit=cost_value,
                credit=0,
                description='ربح جرد'
            )
            
            # أرباح الجرد (دائن)
            JournalEntryLine.objects.create(
                journal_entry=adjustment_entry,
                account=adjustment_account,
                debit=0,
                credit=cost_value,
                description='ربح جرد'
            )
        else:
            # خسارة جرد
            # خسائر الجرد (مدين)
            JournalEntryLine.objects.create(
                journal_entry=adjustment_entry,
                account=adjustment_account,
                debit=cost_value,
                credit=0,
                description='خسارة جرد'
            )
            
            # مخزون البضاعة (دائن)
            JournalEntryLine.objects.create(
                journal_entry=adjustment_entry,
                account=inventory_account,
                debit=0,
                credit=cost_value,
                description='خسارة جرد'
            )
        
        return adjustment_entry



# إشارات Django للربط التلقائي
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender='core.SaleItem')
def auto_process_sale(sender, instance, created, **kwargs):
    """معالجة تلقائية للبيع عند الحفظ"""
    if created and instance.sale.status == 'confirmed':
        try:
            InventoryAccountingManager.process_sale([instance], instance.sale.created_by)
        except Exception as e:
            print(f"خطأ في معالجة البيع: {e}")

@receiver(post_save, sender='core.PurchaseItem')
def auto_process_purchase(sender, instance, created, **kwargs):
    """معالجة تلقائية للشراء عند الحفظ"""
    if created and instance.purchase.status == 'confirmed':
        try:
            InventoryAccountingManager.process_purchase([instance], instance.purchase.created_by)
        except Exception as e:
            print(f"خطأ في معالجة الشراء: {e}")

@receiver(post_save, sender='core.SaleReturnItem')
def auto_process_sale_return(sender, instance, created, **kwargs):
    """معالجة تلقائية لمرتجع البيع عند الحفظ"""
    if created and instance.sale_return.status == 'confirmed':
        try:
            InventoryAccountingManager.process_sale_return([instance], instance.sale_return.created_by)
        except Exception as e:
            print(f"خطأ في معالجة مرتجع البيع: {e}")

# إضافة الدوال الجديدة للكلاس
class InventoryAccountingManagerExtended(InventoryAccountingManager):
    @staticmethod
    @transaction.atomic
    def process_salary(salary, user):
        """معالجة الراتب - قيد محاسبي تلقائي"""
        # الحسابات المطلوبة
        salary_expense_account = InventoryAccountingManager.get_or_create_account(
            '5201', 'مصروف الرواتب', 'expense'
        )
        cash_account = InventoryAccountingManager.get_or_create_account(
            '1001', 'النقدية', 'asset'
        )
        
        # إنشاء قيد الراتب
        salary_entry = JournalEntry.objects.create(
            entry_type='salary',
            description=f'راتب {salary.employee.get_full_name()} - {salary.month}/{salary.year}',
            total_amount=salary.net_salary,
            created_by=user,
            is_posted=True,
            posted_at=timezone.now(),
            posted_by=user
        )
        
        # مصروف الرواتب (مدين)
        JournalEntryLine.objects.create(
            journal_entry=salary_entry,
            account=salary_expense_account,
            debit=salary.net_salary,
            credit=0,
            description=f'راتب {salary.employee.get_full_name()}'
        )
        
        # النقدية (دائن)
        JournalEntryLine.objects.create(
            journal_entry=salary_entry,
            account=cash_account,
            debit=0,
            credit=salary.net_salary,
            description=f'صرف راتب {salary.employee.get_full_name()}'
        )
        
        return salary_entry
    
    @staticmethod
    @transaction.atomic
    def process_customer_payment(payment, user):
        """معالجة دفعة العميل - قيد محاسبي تلقائي"""
        # الحسابات المطلوبة
        cash_account = InventoryAccountingManager.get_or_create_account(
            '1001', 'النقدية', 'asset'
        )
        receivables_account = InventoryAccountingManager.get_or_create_account(
            '1201', 'العملاء', 'asset'
        )
        
        # إنشاء قيد الدفعة
        payment_entry = JournalEntry.objects.create(
            entry_type='voucher',
            description=f'دفعة من العميل {payment.customer.name}',
            total_amount=payment.amount,
            created_by=user,
            is_posted=True,
            posted_at=timezone.now(),
            posted_by=user
        )
        
        # النقدية (مدين)
        JournalEntryLine.objects.create(
            journal_entry=payment_entry,
            account=cash_account,
            debit=payment.amount,
            credit=0,
            description=f'دفعة من {payment.customer.name}'
        )
        
        # العملاء (دائن)
        JournalEntryLine.objects.create(
            journal_entry=payment_entry,
            account=receivables_account,
            debit=0,
            credit=payment.amount,
            description=f'دفعة من {payment.customer.name}'
        )
        
        return payment_entry
    
    @staticmethod
    @transaction.atomic
    def process_supplier_payment(payment, user):
        """معالجة دفعة المورد - قيد محاسبي تلقائي"""
        # الحسابات المطلوبة
        cash_account = InventoryAccountingManager.get_or_create_account(
            '1001', 'النقدية', 'asset'
        )
        payables_account = InventoryAccountingManager.get_or_create_account(
            '2101', 'الموردين', 'liability'
        )
        
        # إنشاء قيد الدفعة
        payment_entry = JournalEntry.objects.create(
            entry_type='voucher',
            description=f'دفعة للمورد {payment.supplier.name}',
            total_amount=payment.amount,
            created_by=user,
            is_posted=True,
            posted_at=timezone.now(),
            posted_by=user
        )
        
        # الموردين (مدين)
        JournalEntryLine.objects.create(
            journal_entry=payment_entry,
            account=payables_account,
            debit=payment.amount,
            credit=0,
            description=f'دفعة للمورد {payment.supplier.name}'
        )
        
        # النقدية (دائن)
        JournalEntryLine.objects.create(
            journal_entry=payment_entry,
            account=cash_account,
            debit=0,
            credit=payment.amount,
            description=f'دفعة للمورد {payment.supplier.name}'
        )
        
        return payment_entry
    
    @staticmethod
    @transaction.atomic
    def process_sales_commission(sale, sales_rep, user):
        """معالجة عمولة المندوب - قيد محاسبي تلقائي"""
        if not hasattr(sales_rep, 'commission_rate') or sales_rep.commission_rate <= 0:
            return None
            
        commission_amount = sale.total_amount * (sales_rep.commission_rate / 100)
        
        # الحسابات المطلوبة
        commission_expense_account = InventoryAccountingManager.get_or_create_account(
            '5202', 'عمولات المبيعات', 'expense'
        )
        commission_payable_account = InventoryAccountingManager.get_or_create_account(
            '2102', 'عمولات مستحقة الدفع', 'liability'
        )
        
        # إنشاء قيد العمولة
        commission_entry = JournalEntry.objects.create(
            entry_type='expense',
            description=f'عمولة مندوب المبيعات - فاتورة #{sale.invoice_number}',
            total_amount=commission_amount,
            created_by=user,
            is_posted=True,
            posted_at=timezone.now(),
            posted_by=user
        )
        
        # عمولات المبيعات (مدين)
        JournalEntryLine.objects.create(
            journal_entry=commission_entry,
            account=commission_expense_account,
            debit=commission_amount,
            credit=0,
            description=f'عمولة مندوب المبيعات'
        )
        
        # عمولات مستحقة الدفع (دائن)
        JournalEntryLine.objects.create(
            journal_entry=commission_entry,
            account=commission_payable_account,
            debit=0,
            credit=commission_amount,
            description=f'عمولة مستحقة الدفع'
        )
        
        return commission_entry
    
    @staticmethod
    @transaction.atomic
    def update_account_balances():
        """تحديث أرصدة الحسابات من القيود"""
        from django.db.models import Sum
        
        for account in Account.objects.all():
            # حساب الرصيد من القيود
            debit_sum = JournalEntryLine.objects.filter(
                account=account, journal_entry__is_posted=True
            ).aggregate(Sum('debit'))['debit__sum'] or 0
            
            credit_sum = JournalEntryLine.objects.filter(
                account=account, journal_entry__is_posted=True
            ).aggregate(Sum('credit'))['credit__sum'] or 0
            
            # تحديث الرصيد حسب نوع الحساب
            if account.account_type in ['asset', 'expense']:
                account.balance = debit_sum - credit_sum
            else:  # liability, equity, revenue
                account.balance = credit_sum - debit_sum
            
            account.debit_balance = debit_sum
            account.credit_balance = credit_sum
            account.save()

# إضافة الدوال للكلاس الأصلي
InventoryAccountingManager.process_salary = staticmethod(lambda salary, user: InventoryAccountingManagerExtended.process_salary(salary, user))
InventoryAccountingManager.process_customer_payment = staticmethod(lambda payment, user: InventoryAccountingManagerExtended.process_customer_payment(payment, user))
InventoryAccountingManager.process_supplier_payment = staticmethod(lambda payment, user: InventoryAccountingManagerExtended.process_supplier_payment(payment, user))
InventoryAccountingManager.process_sales_commission = staticmethod(lambda sale, sales_rep, user: InventoryAccountingManagerExtended.process_sales_commission(sale, sales_rep, user))
InventoryAccountingManager.update_account_balances = staticmethod(lambda: InventoryAccountingManagerExtended.update_account_balances())

# إضافة الإشارات للعمليات الأخرى
@receiver(post_save, sender='core.Salary')
def auto_process_salary(sender, instance, created, **kwargs):
    """معالجة تلقائية للراتب عند التأكيد"""
    if instance.status == 'confirmed':
        try:
            InventoryAccountingManager.process_salary(instance, instance.created_by)
        except Exception as e:
            print(f"خطأ في معالجة الراتب: {e}")

@receiver(post_save, sender='core.CustomerPayment')
def auto_process_customer_payment(sender, instance, created, **kwargs):
    """معالجة تلقائية لدفعة العميل"""
    if created:
        try:
            InventoryAccountingManager.process_customer_payment(instance, instance.created_by)
        except Exception as e:
            print(f"خطأ في معالجة دفعة العميل: {e}")

@receiver(post_save, sender='core.SupplierPayment')
def auto_process_supplier_payment(sender, instance, created, **kwargs):
    """معالجة تلقائية لدفعة المورد"""
    if created:
        try:
            InventoryAccountingManager.process_supplier_payment(instance, instance.created_by)
        except Exception as e:
            print(f"خطأ في معالجة دفعة المورد: {e}")

@receiver(post_save, sender='core.Sale')
def auto_process_sales_commission(sender, instance, created, **kwargs):
    """معالجة تلقائية لعمولة المندوب عند تأكيد البيع"""
    if instance.status == 'confirmed' and hasattr(instance, 'sales_rep') and instance.sales_rep:
        try:
            # البحث عن مندوب المبيعات
            from .models import SalesRep
            sales_rep = SalesRep.objects.filter(user=instance.sales_rep).first()
            if sales_rep:
                InventoryAccountingManager.process_sales_commission(instance, sales_rep, instance.created_by)
        except Exception as e:
            print(f"خطأ في معالجة عمولة المندوب: {e}")