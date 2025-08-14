"""
دوال مساعدة محسنة للنظام
"""
from django.http import JsonResponse
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal, InvalidOperation
import logging

logger = logging.getLogger(__name__)

def safe_decimal(value, default=0):
    """تحويل آمن للأرقام العشرية"""
    try:
        if value is None or value == '':
            return Decimal(str(default))
        
        # التحقق من القيم الخطيرة
        str_value = str(value).lower()
        if any(x in str_value for x in ['nan', 'inf', 'infinity']):
            return Decimal(str(default))
        
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal(str(default))

def safe_int(value, default=0):
    """تحويل آمن للأرقام الصحيحة"""
    try:
        if value is None or value == '':
            return default
        return int(float(str(value)))
    except (ValueError, TypeError):
        return default

def json_response(data=None, success=True, message='', status=200):
    """استجابة JSON موحدة"""
    response_data = {
        'success': success,
        'message': message,
        'data': data or {}
    }
    return JsonResponse(response_data, status=status)

def handle_error(request, error, redirect_url=None):
    """معالجة موحدة للأخطاء"""
    error_message = str(error) if error else 'حدث خطأ غير متوقع'
    
    # تسجيل الخطأ
    logger.error(f"Error in {request.path}: {error_message}")
    
    # إضافة رسالة للمستخدم
    messages.error(request, error_message)
    
    # إرجاع JSON للطلبات AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return json_response(success=False, message=error_message, status=400)
    
    return None

def validate_required_fields(data, required_fields):
    """التحقق من الحقول المطلوبة"""
    missing_fields = []
    for field in required_fields:
        if field not in data or not data[field]:
            missing_fields.append(field)
    
    if missing_fields:
        raise ValidationError(f"الحقول التالية مطلوبة: {', '.join(missing_fields)}")

def format_currency(amount, currency_symbol='د.ك'):
    """تنسيق العملة"""
    try:
        amount = safe_decimal(amount)
        return f"{amount:,.3f} {currency_symbol}"
    except:
        return f"0.000 {currency_symbol}"

def get_current_time():
    """الحصول على الوقت الحالي مع المنطقة الزمنية"""
    return timezone.now()

def paginate_queryset(queryset, page_number, per_page=20):
    """تقسيم النتائج إلى صفحات"""
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    
    paginator = Paginator(queryset, per_page)
    
    try:
        page = paginator.page(page_number)
    except PageNotAnInteger:
        page = paginator.page(1)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)
    
    return page