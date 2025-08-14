# إصلاح العلاقات والمفاتيح الأجنبية
from django.db import models

class RelationshipsFix:
    """
    إصلاح العلاقات المفقودة في النماذج
    """
    
    # إضافة هذه العلاقات لنموذج Sale
    class SaleModelFix:
        # العلاقات المفقودة
        sales_rep = models.ForeignKey('SalesRep', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='مندوب المبيعات')
        branch = models.ForeignKey('Branch', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='الفرع')
        warehouse = models.ForeignKey('Warehouse', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='المخزن')
        
        # حقول الدفع
        payment_method = models.CharField(max_length=20, choices=[
            ('cash', 'نقدي'),
            ('credit', 'آجل'),
            ('mixed', 'مختلط')
        ], default='cash', verbose_name='طريقة الدفع')
        
        paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='المبلغ المدفوع')
        due_date = models.DateField(null=True, blank=True, verbose_name='تاريخ الاستحقاق')
        
        # حقول التأكيد
        confirmed_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='confirmed_sales', verbose_name='أكد بواسطة')
        confirmed_at = models.DateTimeField(null=True, blank=True, verbose_name='تاريخ التأكيد')
    
    # إضافة هذه العلاقات لنموذج Purchase
    class PurchaseModelFix:
        # العلاقات المفقودة
        branch = models.ForeignKey('Branch', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='الفرع')
        warehouse = models.ForeignKey('Warehouse', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='المخزن')
        
        # حقول الدفع
        paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='المبلغ المدفوع')
        due_date = models.DateField(null=True, blank=True, verbose_name='تاريخ الاستحقاق')
        
        # حقول التأكيد
        confirmed_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='confirmed_purchases', verbose_name='أكد بواسطة')
        confirmed_at = models.DateTimeField(null=True, blank=True, verbose_name='تاريخ التأكيد')