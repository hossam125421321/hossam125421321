"""
مساعد الإعدادات - حل بسيط لحفظ الإعدادات
"""
import json
import os
from django.conf import settings

SETTINGS_FILE = os.path.join(settings.BASE_DIR, 'app_settings.json')

def save_setting(key, value):
    """حفظ إعداد في ملف JSON"""
    try:
        # قراءة الإعدادات الحالية
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                current_settings = json.load(f)
        else:
            current_settings = {}
        
        # تحديث الإعداد
        current_settings[key] = value
        
        # حفظ الإعدادات
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(current_settings, f, ensure_ascii=False, indent=2)
        
        return True
    except Exception as e:
        print(f"خطأ في حفظ الإعداد {key}: {e}")
        return False

def get_setting(key, default=None):
    """جلب إعداد من ملف JSON"""
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                current_settings = json.load(f)
                return current_settings.get(key, default)
        return default
    except Exception as e:
        print(f"خطأ في جلب الإعداد {key}: {e}")
        return default

def save_all_settings(settings_dict):
    """حفظ جميع الإعدادات دفعة واحدة"""
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings_dict, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"خطأ في حفظ الإعدادات: {e}")
        return False

def get_all_settings():
    """جلب جميع الإعدادات"""
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"خطأ في جلب الإعدادات: {e}")
        return {}

# الإعدادات الافتراضية
DEFAULT_SETTINGS = {
    'company_name': 'الفنار',
    'currency_symbol': 'د.ك',
    'default_tax_rate': '15',
    'decimal_places': '2',
    'theme_color': 'blue',
    'items_per_page': '25',
    'enable_notifications': 'true',
    'pos_receipt_width': '40',
    'pos_receipt_footer': 'شكراً لتعاملكم معنا',
    'allow_negative_stock': 'false',
    'enable_realtime': 'true',
    'pos_auto_print': 'false',
    'report_date_format': 'd/m/Y',
    'export_max_rows': '1000',
    'show_company_logo': 'true',
    'auto_backup_reports': 'false',
    'session_timeout': '30',
    'backup_count': '5',
    'debug_mode': 'false',
    'maintenance_mode': 'false'
}

def init_default_settings():
    """تهيئة الإعدادات الافتراضية"""
    current_settings = get_all_settings()
    updated = False
    
    for key, value in DEFAULT_SETTINGS.items():
        if key not in current_settings:
            current_settings[key] = value
            updated = True
    
    if updated:
        save_all_settings(current_settings)
    
    return current_settings