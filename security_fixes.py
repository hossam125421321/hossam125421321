"""
إصلاحات الأمان للنظام
"""
import os
from django.utils.html import escape
from django.core.exceptions import ValidationError
from pathlib import Path

def sanitize_path(user_path, base_path):
    """تنظيف المسارات لمنع Path Traversal"""
    try:
        # تحويل إلى Path objects
        base = Path(base_path).resolve()
        target = (base / user_path).resolve()
        
        # التأكد من أن المسار داخل المجلد المسموح
        if not str(target).startswith(str(base)):
            raise ValidationError("مسار غير مسموح")
        
        return str(target)
    except:
        raise ValidationError("مسار غير صحيح")

def validate_numeric_input(value):
    """التحقق من صحة المدخلات الرقمية"""
    try:
        if isinstance(value, str):
            if 'nan' in value.lower() or 'inf' in value.lower():
                raise ValidationError("قيمة رقمية غير صحيحة")
        
        float_val = float(value)
        if str(float_val).lower() in ['nan', 'inf', '-inf']:
            raise ValidationError("قيمة رقمية غير صحيحة")
        
        return float_val
    except (ValueError, TypeError):
        raise ValidationError("قيمة رقمية غير صحيحة")

def sanitize_html_input(text):
    """تنظيف النصوص من XSS"""
    if text:
        return escape(str(text))
    return text

def validate_file_upload(file):
    """التحقق من صحة الملفات المرفوعة"""
    allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.pdf', '.xlsx', '.csv']
    max_size = 10 * 1024 * 1024  # 10MB
    
    if file.size > max_size:
        raise ValidationError("حجم الملف كبير جداً")
    
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in allowed_extensions:
        raise ValidationError("نوع الملف غير مسموح")
    
    return True