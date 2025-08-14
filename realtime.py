# مدير التحديث اللحظي
import time
import json
from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

class RealtimeManager:
    """مدير التحديث اللحظي"""
    
    CACHE_KEY = 'realtime_updates'
    
    @staticmethod
    def add_update(update_type, data, timestamp=None):
        """إضافة تحديث جديد"""
        if timestamp is None:
            timestamp = int(time.time())
        
        update = {
            'type': update_type,
            'data': data,
            'timestamp': timestamp
        }
        
        # الحصول على التحديثات الحالية
        updates = cache.get(RealtimeManager.CACHE_KEY, [])
        updates.append(update)
        
        # الاحتفاظ بآخر 100 تحديث فقط
        if len(updates) > 100:
            updates = updates[-100:]
        
        # حفظ التحديثات
        cache.set(RealtimeManager.CACHE_KEY, updates, 3600)  # ساعة واحدة
    
    @staticmethod
    def get_updates(since_timestamp=0):
        """الحصول على التحديثات منذ وقت معين"""
        updates = cache.get(RealtimeManager.CACHE_KEY, [])
        return [update for update in updates if update['timestamp'] > since_timestamp]
    
    @staticmethod
    def clear_updates():
        """مسح جميع التحديثات"""
        cache.delete(RealtimeManager.CACHE_KEY)
    
    @staticmethod
    def notify_product_update(product):
        """إشعار بتحديث منتج"""
        RealtimeManager.add_update('product_update', {
            'id': product.id,
            'name': product.name,
            'stock': float(getattr(product, 'stock', 0))
        })
    
    @staticmethod
    def notify_sale_created(sale):
        """إشعار بإنشاء فاتورة بيع"""
        RealtimeManager.add_update('sale_created', {
            'id': sale.id,
            'invoice_number': sale.invoice_number,
            'customer': sale.customer.name,
            'total_amount': float(sale.total_amount)
        })
    
    @staticmethod
    def notify_stock_low(product, warehouse, current_stock):
        """إشعار بانخفاض المخزون"""
        RealtimeManager.add_update('stock_low', {
            'product_id': product.id,
            'product_name': product.name,
            'warehouse': warehouse.name if warehouse else '',
            'current_stock': float(current_stock)
        })

# إشارات للتحديث اللحظي
@receiver(post_save, sender='core.Product')
def product_saved(sender, instance, **kwargs):
    RealtimeManager.notify_product_update(instance)

@receiver(post_save, sender='core.Sale')
def sale_saved(sender, instance, created, **kwargs):
    if created:
        RealtimeManager.notify_sale_created(instance)