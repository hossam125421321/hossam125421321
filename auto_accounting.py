from django.db import transaction
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from .models import *
from decimal import Decimal

class AutoAccountingEngine:
    """محرك المحاسبة التلقائي - يسجل القيود فورياً"""
    
    @staticmethod
    def create_journal_entry(entry_type, description, amount, lines_data, user, reference_id=None, reference_type=None):
        """إنشاء قيد محاسبي عام"""
        with transaction.atomic():
            try:
                entry = JournalEntry.objects.create(
                    entry_type=entry_type,
                    description=description,
                    reference_id=reference_id,
                    reference_type=reference_type,
                    total_amount=amount,
                    created_by=user,
                    is_posted=True,
                    posted_at=timezone.now(),
                    posted_by=user
                )
                
                for line_data in lines_data:
                    JournalEntryLine.objects.create(
                        journal_entry=entry,
                        account=line_data['account'],
                        debit=line_data.get('debit', 0),
                        credit=line_data.get('credit', 0),
                        description=line_data['description']
                    )
                
                # تحديث أرصدة الحسابات
                AutoAccountingEngine.update_account_balances(entry)
                return entry
            except Exception as e:
                print(f"خطأ في إنشاء القيد: {e}")
                return None
    
    @staticmethod
    def update_account_balances(entry):
        """تحديث أرصدة الحسابات"""
        for line in entry.lines.all():
            account = line.account
            if line.debit > 0:
                if account.account_type in ['asset', 'expense']:
                    account.balance += line.debit
                else:
                    account.balance -= line.debit
            if line.credit > 0:
                if account.account_type in ['liability', 'equity', 'revenue']:
                    account.balance += line.credit
                else:
                    account.balance -= line.credit
            account.save()
    
    @staticmethod
    def get_or_create_account(code, name, account_type):
        """الحصول على أو إنشاء حساب"""
        account, created = Account.objects.get_or_create(
            account_code=code,
            defaults={
                'name': name,
                'account_type': account_type,
                'balance': 0,
                'auto_update': True
            }
        )
        return account

# إشارات Django للتسجيل التلقائي
@receiver(post_save, sender=Sale)
def auto_sale_accounting(sender, instance, created, **kwargs):
    """تسجيل قيد البيع تلقائياً"""
    if instance.status == 'confirmed' and not getattr(instance, 'journal_processed', False):
        try:
            # حسابات البيع
            customer_account = AutoAccountingEngine.get_or_create_account(
                f'1201{instance.customer.id:03d}',
                f'العميل - {instance.customer.name}',
                'asset'
            )
            sales_account = AutoAccountingEngine.get_or_create_account('4001', 'مبيعات', 'revenue')
            cost_account = AutoAccountingEngine.get_or_create_account('5101', 'تكلفة البضاعة المباعة', 'expense')
            inventory_account = AutoAccountingEngine.get_or_create_account('1301', 'مخزون البضاعة', 'asset')
            
            # قيد البيع
            lines_data = [
                {
                    'account': customer_account,
                    'debit': instance.total_amount,
                    'credit': 0,
                    'description': f'فاتورة بيع #{instance.invoice_number}'
                },
                {
                    'account': sales_account,
                    'debit': 0,
                    'credit': instance.total_amount,
                    'description': f'إيرادات بيع #{instance.invoice_number}'
                }
            ]
            
            # حساب تكلفة البضاعة المباعة
            total_cost = 0
            for item in instance.items.all():
                cost_price = getattr(item.product, 'cost_price', 0) or 0
                item_cost = float(item.quantity) * float(cost_price)
                total_cost += item_cost
            
            if total_cost > 0:
                lines_data.extend([
                    {
                        'account': cost_account,
                        'debit': total_cost,
                        'credit': 0,
                        'description': f'تكلفة البضاعة المباعة #{instance.invoice_number}'
                    },
                    {
                        'account': inventory_account,
                        'debit': 0,
                        'credit': total_cost,
                        'description': f'تخفيض المخزون #{instance.invoice_number}'
                    }
                ])
            
            AutoAccountingEngine.create_journal_entry(
                'sale',
                f'فاتورة بيع #{instance.invoice_number} - {instance.customer.name}',
                instance.total_amount + total_cost,
                lines_data,
                instance.created_by,
                instance.id,
                'sale'
            )
            
            # تحديث رصيد العميل
            instance.customer.opening_balance += instance.total_amount
            instance.customer.save()
            
            # تعليم الفاتورة كمعالجة محاسبياً
            Sale.objects.filter(id=instance.id).update(journal_processed=True)
            
        except Exception as e:
            print(f"خطأ في معالجة قيد البيع: {e}")

@receiver(post_save, sender=Purchase)
def auto_purchase_accounting(sender, instance, created, **kwargs):
    """تسجيل قيد الشراء تلقائياً"""
    if instance.status == 'confirmed' and not getattr(instance, 'journal_processed', False):
        try:
            supplier_account = AutoAccountingEngine.get_or_create_account(
                f'2101{instance.supplier.id:03d}',
                f'المورد - {instance.supplier.name}',
                'liability'
            )
            inventory_account = AutoAccountingEngine.get_or_create_account('1301', 'مخزون البضاعة', 'asset')
            
            lines_data = [
                {
                    'account': inventory_account,
                    'debit': instance.total_amount,
                    'credit': 0,
                    'description': f'شراء بضاعة #{instance.invoice_number}'
                },
                {
                    'account': supplier_account,
                    'debit': 0,
                    'credit': instance.total_amount,
                    'description': f'شراء من {instance.supplier.name} #{instance.invoice_number}'
                }
            ]
            
            AutoAccountingEngine.create_journal_entry(
                'purchase',
                f'فاتورة شراء #{instance.invoice_number} - {instance.supplier.name}',
                instance.total_amount,
                lines_data,
                instance.created_by,
                instance.id,
                'purchase'
            )
            
            # تحديث رصيد المورد
            instance.supplier.opening_balance += instance.total_amount
            instance.supplier.save()
            
            Purchase.objects.filter(id=instance.id).update(journal_processed=True)
            
        except Exception as e:
            print(f"خطأ في معالجة قيد الشراء: {e}")

@receiver(post_save, sender=Salary)
def auto_salary_accounting(sender, instance, created, **kwargs):
    """تسجيل قيد الراتب تلقائياً"""
    if instance.status == 'confirmed':
        try:
            salary_account = AutoAccountingEngine.get_or_create_account('5201', 'رواتب الموظفين', 'expense')
            cash_account = AutoAccountingEngine.get_or_create_account('1001', 'النقدية', 'asset')
            
            lines_data = [
                {
                    'account': salary_account,
                    'debit': instance.net_salary,
                    'credit': 0,
                    'description': f'راتب {instance.employee.get_full_name()} - {instance.month}/{instance.year}'
                },
                {
                    'account': cash_account,
                    'debit': 0,
                    'credit': instance.net_salary,
                    'description': f'صرف راتب {instance.employee.get_full_name()}'
                }
            ]
            
            AutoAccountingEngine.create_journal_entry(
                'salary',
                f'راتب {instance.employee.get_full_name()} - {instance.month}/{instance.year}',
                instance.net_salary,
                lines_data,
                instance.created_by,
                instance.id,
                'salary'
            )
            
        except Exception as e:
            print(f"خطأ في معالجة قيد الراتب: {e}")

@receiver(post_save, sender=CustomerPayment)
def auto_customer_payment_accounting(sender, instance, created, **kwargs):
    """تسجيل قيد دفعة العميل تلقائياً"""
    if created:
        try:
            cash_account = AutoAccountingEngine.get_or_create_account('1001', 'النقدية', 'asset')
            customer_account = AutoAccountingEngine.get_or_create_account(
                f'1201{instance.customer.id:03d}',
                f'العميل - {instance.customer.name}',
                'asset'
            )
            
            lines_data = [
                {
                    'account': cash_account,
                    'debit': instance.amount,
                    'credit': 0,
                    'description': f'دفعة من {instance.customer.name} #{instance.payment_number}'
                },
                {
                    'account': customer_account,
                    'debit': 0,
                    'credit': instance.amount,
                    'description': f'تحصيل من {instance.customer.name}'
                }
            ]
            
            AutoAccountingEngine.create_journal_entry(
                'voucher',
                f'دفعة من العميل {instance.customer.name} - #{instance.payment_number}',
                instance.amount,
                lines_data,
                instance.created_by,
                instance.id,
                'customer_payment'
            )
            
            # تحديث رصيد العميل
            instance.customer.opening_balance -= instance.amount
            instance.customer.save()
            
        except Exception as e:
            print(f"خطأ في معالجة قيد دفعة العميل: {e}")

@receiver(post_save, sender=SupplierPayment)
def auto_supplier_payment_accounting(sender, instance, created, **kwargs):
    """تسجيل قيد دفعة المورد تلقائياً"""
    if created:
        try:
            cash_account = AutoAccountingEngine.get_or_create_account('1001', 'النقدية', 'asset')
            supplier_account = AutoAccountingEngine.get_or_create_account(
                f'2101{instance.supplier.id:03d}',
                f'المورد - {instance.supplier.name}',
                'liability'
            )
            
            lines_data = [
                {
                    'account': supplier_account,
                    'debit': instance.amount,
                    'credit': 0,
                    'description': f'دفع للمورد {instance.supplier.name}'
                },
                {
                    'account': cash_account,
                    'debit': 0,
                    'credit': instance.amount,
                    'description': f'دفعة للمورد {instance.supplier.name} #{instance.payment_number}'
                }
            ]
            
            AutoAccountingEngine.create_journal_entry(
                'voucher',
                f'دفعة للمورد {instance.supplier.name} - #{instance.payment_number}',
                instance.amount,
                lines_data,
                instance.created_by,
                instance.id,
                'supplier_payment'
            )
            
            # تحديث رصيد المورد
            instance.supplier.opening_balance -= instance.amount
            instance.supplier.save()
            
        except Exception as e:
            print(f"خطأ في معالجة قيد دفعة المورد: {e}")

@receiver(post_save, sender=SaleReturn)
def auto_sale_return_accounting(sender, instance, created, **kwargs):
    """تسجيل قيد مرتجع البيع تلقائياً"""
    if instance.status == 'confirmed':
        try:
            customer_account = AutoAccountingEngine.get_or_create_account(
                f'1201{instance.customer.id:03d}',
                f'العميل - {instance.customer.name}',
                'asset'
            )
            sales_return_account = AutoAccountingEngine.get_or_create_account('4002', 'مرتجعات مبيعات', 'revenue')
            inventory_account = AutoAccountingEngine.get_or_create_account('1301', 'مخزون البضاعة', 'asset')
            cost_account = AutoAccountingEngine.get_or_create_account('5101', 'تكلفة البضاعة المباعة', 'expense')
            
            lines_data = [
                {
                    'account': sales_return_account,
                    'debit': instance.total_amount,
                    'credit': 0,
                    'description': f'مرتجع بيع #{instance.return_number}'
                },
                {
                    'account': customer_account,
                    'debit': 0,
                    'credit': instance.total_amount,
                    'description': f'مرتجع من {instance.customer.name}'
                }
            ]
            
            # إضافة قيد إرجاع البضاعة للمخزون
            total_cost = 0
            for item in instance.items.all():
                cost_price = getattr(item.product, 'cost_price', 0) or 0
                item_cost = float(item.quantity) * float(cost_price)
                total_cost += item_cost
            
            if total_cost > 0:
                lines_data.extend([
                    {
                        'account': inventory_account,
                        'debit': total_cost,
                        'credit': 0,
                        'description': f'إرجاع بضاعة للمخزون #{instance.return_number}'
                    },
                    {
                        'account': cost_account,
                        'debit': 0,
                        'credit': total_cost,
                        'description': f'عكس تكلفة البضاعة المباعة #{instance.return_number}'
                    }
                ])
            
            AutoAccountingEngine.create_journal_entry(
                'return',
                f'مرتجع بيع #{instance.return_number} - {instance.customer.name}',
                instance.total_amount + total_cost,
                lines_data,
                instance.created_by,
                instance.id,
                'sale_return'
            )
            
        except Exception as e:
            print(f"خطأ في معالجة قيد مرتجع البيع: {e}")

@receiver(post_save, sender=PurchaseReturn)
def auto_purchase_return_accounting(sender, instance, created, **kwargs):
    """تسجيل قيد مرتجع الشراء تلقائياً"""
    if instance.status == 'confirmed':
        try:
            supplier_account = AutoAccountingEngine.get_or_create_account(
                f'2101{instance.supplier.id:03d}',
                f'المورد - {instance.supplier.name}',
                'liability'
            )
            inventory_account = AutoAccountingEngine.get_or_create_account('1301', 'مخزون البضاعة', 'asset')
            
            lines_data = [
                {
                    'account': supplier_account,
                    'debit': instance.total_amount,
                    'credit': 0,
                    'description': f'مرتجع شراء #{instance.return_number}'
                },
                {
                    'account': inventory_account,
                    'debit': 0,
                    'credit': instance.total_amount,
                    'description': f'مرتجع بضاعة للمورد {instance.supplier.name}'
                }
            ]
            
            AutoAccountingEngine.create_journal_entry(
                'return',
                f'مرتجع شراء #{instance.return_number} - {instance.supplier.name}',
                instance.total_amount,
                lines_data,
                instance.created_by,
                instance.id,
                'purchase_return'
            )
            
        except Exception as e:
            print(f"خطأ في معالجة قيد مرتجع الشراء: {e}")

# دالة إعداد الحسابات الأساسية
def setup_basic_accounts():
    """إعداد الحسابات الأساسية للنظام"""
    basic_accounts = [
        ('1001', 'النقدية', 'asset'),
        ('1002', 'البنك', 'asset'),
        ('1201', 'العملاء', 'asset'),
        ('1301', 'مخزون البضاعة', 'asset'),
        ('2101', 'الموردين', 'liability'),
        ('2201', 'رواتب مستحقة', 'liability'),
        ('3001', 'رأس المال', 'equity'),
        ('4001', 'مبيعات', 'revenue'),
        ('4002', 'مرتجعات مبيعات', 'revenue'),
        ('5001', 'مشتريات', 'expense'),
        ('5002', 'مرتجعات مشتريات', 'expense'),
        ('5101', 'تكلفة البضاعة المباعة', 'expense'),
        ('5201', 'رواتب الموظفين', 'expense'),
        ('5301', 'مصاريف عمومية', 'expense'),
    ]
    
    for code, name, account_type in basic_accounts:
        AutoAccountingEngine.get_or_create_account(code, name, account_type)