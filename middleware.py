# -*- coding: utf-8 -*-
"""
Middleware لإدارة قواعد البيانات المتعددة
"""
import os
from django.conf import settings
from django.db import connection
from django.shortcuts import redirect
from django.urls import reverse

class MultiDatabaseMiddleware:
    """Middleware لتبديل قواعد البيانات حسب الشركة"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # تبديل قاعدة البيانات حسب الشركة في الجلسة
        if request.user.is_authenticated and 'company_code' in request.session:
            company_code = request.session['company_code']
            self.switch_database(company_code)
        
        response = self.get_response(request)
        return response
    
    def switch_database(self, company_code):
        """تبديل قاعدة البيانات"""
        try:
            db_name = f"erp_{company_code.lower()}.db"
            db_path = os.path.join(settings.BASE_DIR, 'databases', db_name)
            
            if os.path.exists(db_path):
                current_db = settings.DATABASES['default']['NAME']
                if current_db != db_path:
                    settings.DATABASES['default']['NAME'] = db_path
                    connection.close()
        except Exception as e:
            pass


class CompanyMiddleware:
    """Middleware لإدارة الشركات"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # تبديل قاعدة البيانات حسب الشركة
        try:
            # إذا كان المستخدم مسجل دخول ولا يوجد company_code في الجلسة
            if (hasattr(request, 'user') and request.user.is_authenticated and 
                hasattr(request, 'session') and 'company_code' not in request.session):
                try:
                    from core.models import UserProfile
                    profile = UserProfile.objects.select_related('company').get(user=request.user, is_active=True)
                    if profile.company:
                        request.session['company_code'] = profile.company.code
                        request.session['company_id'] = profile.company.id
                        request.session['database_name'] = profile.company.database_name
                    else:
                        request.session['company_code'] = 'DEFAULT'
                except:
                    # إذا لم يوجد ملف للمستخدم، استخدم الشركة الافتراضية
                    request.session['company_code'] = 'DEFAULT'
            
            # التأكد من وجود company_code في الجلسة
            if not hasattr(request, 'session'):
                pass
            elif 'company_code' not in request.session:
                request.session['company_code'] = 'DEFAULT'
            
            if hasattr(request, 'session') and 'company_code' in request.session:
                company_code = request.session['company_code']
                db_name = f"erp_{company_code.lower()}.db"
                db_path = os.path.join(settings.BASE_DIR, 'databases', db_name)
                
                # التحقق من وجود قاعدة البيانات وأنها تحتوي على الجداول الأساسية
                if os.path.exists(db_path) and self.is_database_valid(db_path):
                    current_db = str(settings.DATABASES['default']['NAME'])
                    if current_db != str(db_path):
                        settings.DATABASES['default']['NAME'] = db_path
                        connection.close()
                else:
                    # إذا كانت قاعدة البيانات غير صالحة، إنشاؤها أو إصلاحها
                    self.fix_database(db_path)
        except Exception as e:
            # في حالة الخطأ، استخدام قاعدة البيانات الافتراضية
            pass
        
        response = self.get_response(request)
        return response
    
    def is_database_valid(self, db_path):
        """فحص صحة قاعدة البيانات"""
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # فحص وجود الجداول الأساسية
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='auth_user';")
            auth_exists = cursor.fetchone() is not None
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='core_company';")
            company_exists = cursor.fetchone() is not None
            
            conn.close()
            return auth_exists and company_exists
        except:
            return False
    
    def fix_database(self, db_path):
        """إصلاح قاعدة البيانات"""
        try:
            import shutil
            main_db = os.path.join(settings.BASE_DIR, 'db.sqlite3')
            if os.path.exists(main_db):
                # إنشاء مجلد قواعد البيانات إذا لم يكن موجوداً
                os.makedirs(os.path.dirname(db_path), exist_ok=True)
                # نسخ قاعدة البيانات الرئيسية
                shutil.copy2(main_db, db_path)
        except:
            pass