# إضافة الحقول المفقودة لنموذج العملاء
from django.db import models

# إضافة هذه الحقول لنموذج Customer
class CustomerFieldsFix:
    """
    الحقول المطلوب إضافتها لنموذج Customer لتطابق الشاشة
    """
    
    # إضافة هذه الحقول للنموذج
    tax_number = models.CharField(max_length=50, blank=True, verbose_name='الرقم الضريبي')
    commercial_record = models.CharField(max_length=50, blank=True, verbose_name='السجل التجاري')
    contact_person = models.CharField(max_length=100, blank=True, verbose_name='الشخص المسؤول')
    payment_terms = models.CharField(max_length=20, choices=[
        ('cash', 'نقدي'),
        ('30_days', '30 يوم'),
        ('60_days', '60 يوم'),
        ('90_days', '90 يوم'),
    ], blank=True, verbose_name='شروط الدفع')
    notes = models.TextField(blank=True, verbose_name='ملاحظات')
    
    # حقول التتبع
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, verbose_name='أنشئ بواسطة')
    updated_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, related_name='updated_customers', verbose_name='حدث بواسطة')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')