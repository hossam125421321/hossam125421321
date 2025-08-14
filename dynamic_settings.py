"""
نظام الإعدادات الديناميكي - إدارة الإعدادات مع التطبيق الفوري
"""

from django.core.cache import cache
from django.db import models
from django.utils import timezone
from decimal import Decimal
import json
import threading
from typing import Any, Optional, Dict, List

class DynamicSettingsManager:
    """
    مدير الإعدادات الديناميكي - يدير الإعدادات مع الكاش والتطبيق الفوري
    """
    
    CACHE_PREFIX = 'dynamic_setting_'
    CACHE_TIMEOUT = 3600  # ساعة واحدة
    
    # قفل للحماية من التداخل في العمليات المتزامنة
    _lock = threading.Lock()
    
    @classmethod
    def get_cache_key(cls, key: str, branch_id: Optional[int] = None) -> str:
        """إنشاء مفتاح الكاش للإعداد"""
        return f"{cls.CACHE_PREFIX}{branch_id or 'global'}_{key}"
    
    @classmethod
    def get(cls, key: str, branch=None, default: Any = None) -> Any:
        """
        الحصول على قيمة إعداد مع استخدام الكاش
        
        Args:
            key: مفتاح الإعداد
            branch: الفرع (اختياري)
            default: القيمة الافتراضية
            
        Returns:
            قيمة الإعداد أو القيمة الافتراضية
        """
        cache_key = cls.get_cache_key(key, branch.id if branch else None)
        
        # محاولة الحصول على القيمة من الكاش أولاً
        value = cache.get(cache_key)
        if value is not None:
            return value
        
        # إذا لم توجد في الكاش، جلبها من قاعدة البيانات
        with cls._lock:
            try:
                from .models import Setting
                
                # البحث عن الإعداد حسب الفرع أو الإعداد العام
                setting = Setting.objects.filter(
                    key=key
                ).filter(
                    models.Q(branch=branch) | models.Q(is_global=True)
                ).first()
                
                if setting:
                    value = setting.get_value()
                    # حفظ في الكاش
                    cache.set(cache_key, value, cls.CACHE_TIMEOUT)
                    return value
                    
            except Exception as e:
                print(f"خطأ في جلب الإعداد {key}: {str(e)}")
        
        return default
    
    @classmethod
    def set(cls, key: str, value: Any, branch=None, setting_type: str = 'string', 
            category: str = 'general', description: str = '') -> bool:
        """
        حفظ إعداد مع التطبيق الفوري
        
        Args:
            key: مفتاح الإعداد
            value: قيمة الإعداد
            branch: الفرع (اختياري)
            setting_type: نوع الإعداد
            category: فئة الإعداد
            description: وصف الإعداد
            
        Returns:
            True إذا تم الحفظ بنجاح، False في حالة الخطأ
        """
        with cls._lock:
            try:
                from .models import Setting
                
                # إنشاء أو تحديث الإعداد
                setting, created = Setting.objects.update_or_create(
                    key=key,
                    branch=branch,
                    defaults={
                        'value': str(value),
                        'setting_type': setting_type,
                        'category': category,
                        'description': description,
                        'is_global': branch is None,
                        'updated_at': timezone.now()
                    }
                )
                
                # تحديث الكاش فوراً
                cache_key = cls.get_cache_key(key, branch.id if branch else None)
                
                # تحويل القيمة حسب النوع
                processed_value = cls._process_value(value, setting_type)
                cache.set(cache_key, processed_value, cls.CACHE_TIMEOUT)
                
                # إرسال إشارة التحديث للنظام
                cls._broadcast_setting_change(key, processed_value, branch)
                
                return True
                
            except Exception as e:
                print(f"خطأ في حفظ الإعداد {key}: {str(e)}")
                return False
    
    @classmethod
    def get_multiple(cls, keys: List[str], branch=None, defaults: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        الحصول على عدة إعدادات دفعة واحدة
        
        Args:
            keys: قائمة مفاتيح الإعدادات
            branch: الفرع (اختياري)
            defaults: القيم الافتراضية
            
        Returns:
            قاموس بالإعدادات وقيمها
        """
        defaults = defaults or {}
        result = {}
        
        for key in keys:
            result[key] = cls.get(key, branch, defaults.get(key))
        
        return result
    
    @classmethod
    def set_multiple(cls, settings: Dict[str, Any], branch=None, 
                    setting_types: Dict[str, str] = None,
                    categories: Dict[str, str] = None) -> bool:
        """
        حفظ عدة إعدادات دفعة واحدة
        
        Args:
            settings: قاموس الإعدادات
            branch: الفرع (اختياري)
            setting_types: أنواع الإعدادات
            categories: فئات الإعدادات
            
        Returns:
            True إذا تم الحفظ بنجاح
        """
        setting_types = setting_types or {}
        categories = categories or {}
        
        success_count = 0
        
        for key, value in settings.items():
            setting_type = setting_types.get(key, 'string')
            category = categories.get(key, 'general')
            
            if cls.set(key, value, branch, setting_type, category):
                success_count += 1
        
        return success_count == len(settings)
    
    @classmethod
    def clear_cache(cls, key: Optional[str] = None, branch=None) -> None:
        """
        مسح الكاش للإعدادات
        
        Args:
            key: مفتاح إعداد محدد (اختياري)
            branch: الفرع (اختياري)
        """
        if key:
            # مسح إعداد محدد
            cache_key = cls.get_cache_key(key, branch.id if branch else None)
            cache.delete(cache_key)
        else:
            # مسح جميع إعدادات الفرع أو الإعدادات العامة
            pattern = f"{cls.CACHE_PREFIX}{branch.id if branch else 'global'}_*"
            # Django cache لا يدعم wildcard delete مباشرة
            # لذا نحتاج لمسح الكاش كاملاً أو استخدام Redis
            cache.clear()
    
    @classmethod
    def get_all_settings(cls, branch=None, category: Optional[str] = None) -> Dict[str, Any]:
        """
        الحصول على جميع الإعدادات
        
        Args:
            branch: الفرع (اختياري)
            category: فئة محددة (اختياري)
            
        Returns:
            قاموس بجميع الإعدادات
        """
        try:
            from .models import Setting
            
            queryset = Setting.objects.filter(
                models.Q(branch=branch) | models.Q(is_global=True)
            )
            
            if category:
                queryset = queryset.filter(category=category)
            
            settings = {}
            for setting in queryset:
                settings[setting.key] = setting.get_value()
            
            return settings
            
        except Exception as e:
            print(f"خطأ في جلب جميع الإعدادات: {str(e)}")
            return {}
    
    @classmethod
    def delete_setting(cls, key: str, branch=None) -> bool:
        """
        حذف إعداد
        
        Args:
            key: مفتاح الإعداد
            branch: الفرع (اختياري)
            
        Returns:
            True إذا تم الحذف بنجاح
        """
        with cls._lock:
            try:
                from .models import Setting
                
                # حذف من قاعدة البيانات
                deleted_count = Setting.objects.filter(
                    key=key,
                    branch=branch
                ).delete()[0]
                
                if deleted_count > 0:
                    # مسح من الكاش
                    cls.clear_cache(key, branch)
                    
                    # إرسال إشارة الحذف
                    cls._broadcast_setting_change(key, None, branch, deleted=True)
                    
                    return True
                
            except Exception as e:
                print(f"خطأ في حذف الإعداد {key}: {str(e)}")
        
        return False
    
    @classmethod
    def reset_to_defaults(cls, branch=None) -> bool:
        """
        إعادة تعيين الإعدادات للقيم الافتراضية
        
        Args:
            branch: الفرع (اختياري)
            
        Returns:
            True إذا تم الإعادة بنجاح
        """
        default_settings = cls._get_default_settings()
        
        try:
            # حذف الإعدادات الحالية
            from .models import Setting
            Setting.objects.filter(branch=branch, is_system=False).delete()
            
            # إعادة إنشاء الإعدادات الافتراضية
            success = cls.set_multiple(
                default_settings['values'],
                branch,
                default_settings['types'],
                default_settings['categories']
            )
            
            if success:
                # مسح الكاش
                cls.clear_cache(branch=branch)
            
            return success
            
        except Exception as e:
            print(f"خطأ في إعادة تعيين الإعدادات: {str(e)}")
            return False
    
    @classmethod
    def export_settings(cls, branch=None, format: str = 'json') -> Optional[str]:
        """
        تصدير الإعدادات
        
        Args:
            branch: الفرع (اختياري)
            format: تنسيق التصدير (json, yaml)
            
        Returns:
            البيانات المُصدرة كنص
        """
        try:
            settings = cls.get_all_settings(branch)
            
            if format.lower() == 'json':
                return json.dumps(settings, ensure_ascii=False, indent=2)
            elif format.lower() == 'yaml':
                try:
                    import yaml
                    return yaml.dump(settings, allow_unicode=True, default_flow_style=False)
                except ImportError:
                    print("مكتبة PyYAML غير مثبتة")
                    return None
            
        except Exception as e:
            print(f"خطأ في تصدير الإعدادات: {str(e)}")
        
        return None
    
    @classmethod
    def import_settings(cls, data: str, branch=None, format: str = 'json', 
                       overwrite: bool = False) -> bool:
        """
        استيراد الإعدادات
        
        Args:
            data: البيانات المُستوردة
            branch: الفرع (اختياري)
            format: تنسيق البيانات
            overwrite: استبدال الإعدادات الموجودة
            
        Returns:
            True إذا تم الاستيراد بنجاح
        """
        try:
            if format.lower() == 'json':
                settings = json.loads(data)
            elif format.lower() == 'yaml':
                try:
                    import yaml
                    settings = yaml.safe_load(data)
                except ImportError:
                    print("مكتبة PyYAML غير مثبتة")
                    return False
            else:
                return False
            
            if not overwrite:
                # تجاهل الإعدادات الموجودة
                existing_settings = cls.get_all_settings(branch)
                settings = {k: v for k, v in settings.items() if k not in existing_settings}
            
            return cls.set_multiple(settings, branch)
            
        except Exception as e:
            print(f"خطأ في استيراد الإعدادات: {str(e)}")
            return False
    
    @classmethod
    def _process_value(cls, value: Any, setting_type: str) -> Any:
        """معالجة القيمة حسب نوعها"""
        if setting_type == 'boolean':
            if isinstance(value, str):
                return value.lower() in ['true', '1', 'yes', 'on']
            return bool(value)
        elif setting_type == 'integer':
            try:
                return int(value)
            except (ValueError, TypeError):
                return 0
        elif setting_type == 'decimal':
            try:
                return Decimal(str(value))
            except (ValueError, TypeError):
                return Decimal('0.0')
        elif setting_type == 'json':
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return {}
            return value
        else:
            return str(value)
    
    @classmethod
    def _broadcast_setting_change(cls, key: str, value: Any, branch=None, deleted: bool = False):
        """إرسال إشارة تغيير الإعداد للنظام"""
        try:
            # يمكن إضافة نظام إشارات Django هنا
            # أو استخدام WebSocket للتحديث اللحظي
            from django.dispatch import Signal
            
            setting_changed = Signal()
            setting_changed.send(
                sender=cls,
                key=key,
                value=value,
                branch=branch,
                deleted=deleted
            )
            
        except Exception as e:
            print(f"خطأ في إرسال إشارة تغيير الإعداد: {str(e)}")
    
    @classmethod
    def _get_default_settings(cls) -> Dict[str, Dict[str, Any]]:
        """الحصول على الإعدادات الافتراضية"""
        return {
            'values': {
                'company_name': 'شركة ERP',
                'company_address': '',
                'company_phone': '',
                'currency_symbol': 'د.ك',
                'theme_color': 'blue',
                'items_per_page': '25',
                'date_format': 'd/m/Y',
                'print_logo': 'true',
                'print_header': '',
                'print_footer': 'شكراً لتعاملكم معنا',
                'thermal_printer_width': '80',
                'invoice_template': 'classic',
                'receipt_template': 'standard',
                'default_tax_rate': '15',
                'allow_negative_stock': 'false',
                'invoice_auto_confirm': 'false',
                'invoice_numbering': 'auto',
                'show_dashboard_stats': 'true',
                'show_product_images': 'true',
                'enable_notifications': 'true',
                'sidebar_collapsed': 'false',
            },
            'types': {
                'company_name': 'string',
                'company_address': 'string',
                'company_phone': 'string',
                'currency_symbol': 'string',
                'theme_color': 'string',
                'items_per_page': 'integer',
                'date_format': 'string',
                'print_logo': 'boolean',
                'print_header': 'string',
                'print_footer': 'string',
                'thermal_printer_width': 'string',
                'invoice_template': 'string',
                'receipt_template': 'string',
                'default_tax_rate': 'decimal',
                'allow_negative_stock': 'boolean',
                'invoice_auto_confirm': 'boolean',
                'invoice_numbering': 'string',
                'show_dashboard_stats': 'boolean',
                'show_product_images': 'boolean',
                'enable_notifications': 'boolean',
                'sidebar_collapsed': 'boolean',
            },
            'categories': {
                'company_name': 'company',
                'company_address': 'company',
                'company_phone': 'company',
                'currency_symbol': 'currency',
                'theme_color': 'display',
                'items_per_page': 'display',
                'date_format': 'display',
                'print_logo': 'printing',
                'print_header': 'printing',
                'print_footer': 'printing',
                'thermal_printer_width': 'printing',
                'invoice_template': 'printing',
                'receipt_template': 'printing',
                'default_tax_rate': 'invoice',
                'allow_negative_stock': 'invoice',
                'invoice_auto_confirm': 'invoice',
                'invoice_numbering': 'invoice',
                'show_dashboard_stats': 'display',
                'show_product_images': 'display',
                'enable_notifications': 'display',
                'sidebar_collapsed': 'display',
            }
        }


# دالة مساعدة للوصول السريع للإعدادات
def get_dynamic_setting(key: str, default: Any = None, branch=None) -> Any:
    """دالة مساعدة للحصول على إعداد ديناميكي"""
    return DynamicSettingsManager.get(key, branch, default)


def set_dynamic_setting(key: str, value: Any, branch=None, setting_type: str = 'string') -> bool:
    """دالة مساعدة لحفظ إعداد ديناميكي"""
    return DynamicSettingsManager.set(key, value, branch, setting_type)


# ديكوريتر للإعدادات المطلوبة
def require_setting(setting_key: str, default_value: Any = None):
    """
    ديكوريتر للتأكد من وجود إعداد معين
    
    Args:
        setting_key: مفتاح الإعداد المطلوب
        default_value: القيمة الافتراضية إذا لم يوجد الإعداد
    """
    def decorator(func):
        def wrapper(request, *args, **kwargs):
            setting_value = get_dynamic_setting(
                setting_key, 
                default_value, 
                getattr(request, 'current_branch', None)
            )
            
            # إضافة الإعداد لسياق الطلب
            if not hasattr(request, 'dynamic_settings'):
                request.dynamic_settings = {}
            request.dynamic_settings[setting_key] = setting_value
            
            return func(request, *args, **kwargs)
        return wrapper
    return decorator