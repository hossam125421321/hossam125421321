"""
إشارات النظام المتكامل
===================

هذا الملف يحتوي على جميع الإشارات المسؤولة عن ربط العمليات تلقائياً.
الإشارات تعمل بشكل متزامن وآمن لضمان تكامل البيانات.

الوظائف الرئيسية:
- ربط البيع والشراء بالمخزون
- تحديث المحاسبة تلقائياً
- مراقبة المخزون المنخفض
- تسجيل حركات المخزون
"""

#from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db import transaction
from django.core.cache import cache
import logging

# إعداد نظام التسجيل
logger = logging.getLogger('erp_signals')

# تجنب الاستيراد الدائري
def get_models():
    """استيراد النماذج بشكل آمن لتجنب الاستيراد الدائري"""
    from .models import Sale, SaleItem, Purchase, PurchaseItem, Product, StockMovement, ProductStock, POSSaleItem
    return Sale, SaleItem, Purchase, PurchaseItem, Product, StockMovement, ProductStock, POSSaleItem

#@receiver(post_save, sender='core.Sale')
#def handle_sale_confirmation(sender, instance, **kwargs):
    """
    معالجة تأكيد فاتورة البيع
    
    يتم تشغيلها عند:
    - تأكيد فاتورة البيع (تغيير الحالة إلى confirmed)
    
    العمليات:
    1. تحديث المخزون لكل عنصر
    2. إنشاء حركات المخزون
    3. تحديث المحاسبة
    """
    if instance.status == 'confirmed' and hasattr(instance, '_just_confirmed'):
        try:
            with transaction.atomic():
                from .inventory import InventoryManager
                from .accounting import AccountingEngine
                
                # تحديث المخزون لكل عنصر
                for item in instance.items.all():
                    InventoryManager.update_stock(
                        product=item.product,
                        quantity=item.quantity,
                        movement_type='out',
                        reference=f'Sale #{instance.invoice_number}',
                        user=instance.created_by
                    )
                
                # تحديث المحاسبة
                AccountingEngine.create_sale_entries(instance)
                
                logger.info(f'تم تأكيد فاتورة البيع #{instance.invoice_number}')
                
        except Exception as e:
            logger.error(f'خطأ في تأكيد فاتورة البيع #{instance.invoice_number}: {str(e)}')
            raise


#@receiver(post_save, sender='core.Purchase')
#def handle_purchase_confirmation(sender, instance, **kwargs):
    """
    معالجة تأكيد فاتورة الشراء
    
    يتم تشغيلها عند:
    - تأكيد فاتورة الشراء (تغيير الحالة إلى confirmed)
    
    العمليات:
    1. تحديث المخزون لكل عنصر
    2. إنشاء حركات المخزون
    3. تحديث المحاسبة
    """
    if instance.status == 'confirmed' and hasattr(instance, '_just_confirmed'):
        try:
            with transaction.atomic():
                from .inventory import InventoryManager
                from .accounting import AccountingEngine
                
                # تحديث المخزون لكل عنصر
                for item in instance.items.all():
                    InventoryManager.update_stock(
                        product=item.product,
                        quantity=item.quantity,
                        movement_type='in',
                        reference=f'Purchase #{instance.invoice_number}',
                        user=instance.created_by
                    )
                
                # تحديث المحاسبة
                AccountingEngine.create_purchase_entries(instance)
                
                logger.info(f'تم تأكيد فاتورة الشراء #{instance.invoice_number}')
                
        except Exception as e:
            logger.error(f'خطأ في تأكيد فاتورة الشراء #{instance.invoice_number}: {str(e)}')
            raise

#@receiver(post_save, sender='core.POSSaleItem')
#def handle_pos_sale(sender, instance, created, **kwargs):
    """
    معالجة مبيعات نقاط البيع
    
    يتم تشغيلها عند:
    - إضافة عنصر جديد لمبيعات نقاط البيع
    
    العمليات:
    1. تحديث المخزون فوراً
    2. إنشاء حركة مخزون
    """
    if created:
        try:
            with transaction.atomic():
                from .inventory import InventoryManager
                
                InventoryManager.update_stock(
                    product=instance.product,
                    quantity=instance.quantity,
                    movement_type='out',
                    reference=f'POS Sale #{instance.sale.receipt_number}',
                    user=instance.sale.session.cashier
                )
                
                logger.info(f'تم تحديث المخزون لمبيعات نقاط البيع #{instance.sale.receipt_number}')
                
        except Exception as e:
            logger.error(f'خطأ في تحديث مخزون نقاط البيع: {str(e)}')
            raise

#@receiver(post_save, sender='core.ProductStock')
#def monitor_low_stock(sender, instance, **kwargs):
    """
    مراقبة المخزون المنخفض
    
    يتم تشغيلها عند:
    - تحديث مخزون المنتج
    
    العمليات:
    1. فحص إذا كان المخزون أقل من الحد الأدنى
    2. إنشاء تنبيه في الكاش
    """
    try:
        if instance.current_stock <= instance.min_stock:
            cache.set(
                f'low_stock_{instance.product.id}_{instance.warehouse.id}',
                {
                    'product_name': instance.product.name,
                    'current_stock': float(instance.current_stock),
                    'min_stock': float(instance.min_stock),
                    'warehouse': instance.warehouse.name
                },
                3600  # ساعة واحدة
            )
            logger.warning(f'مخزون منخفض: {instance.product.name} في {instance.warehouse.name}')
            
    except Exception as e:
        logger.error(f'خطأ في مراقبة المخزون المنخفض: {str(e)}')