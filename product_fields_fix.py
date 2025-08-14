# إصلاح نموذج المنتجات لتطابق الشاشة
from django.db import models

class ProductFieldsFix:
    """
    التعديلات المطلوبة على نموذج Product
    """
    
    # إضافة هذه الحقول
    selling_price = models.DecimalField(max_digits=10, decimal_places=3, default=0, verbose_name='سعر البيع')
    min_stock = models.DecimalField(max_digits=10, decimal_places=3, default=10, verbose_name='الحد الأدنى للمخزون')
    max_stock = models.DecimalField(max_digits=10, decimal_places=3, default=1000, verbose_name='الحد الأقصى للمخزون')
    
    # حقول التتبع
    updated_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, related_name='updated_products', verbose_name='حدث بواسطة')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')
    
    # خاصية محسوبة لهامش الربح
    @property
    def profit_margin(self):
        if self.cost_price and self.cost_price > 0:
            return ((self.selling_price - self.cost_price) / self.cost_price) * 100
        return 0