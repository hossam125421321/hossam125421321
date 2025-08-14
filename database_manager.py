# -*- coding: utf-8 -*-
"""
مدير قواعد البيانات المتعددة
"""
import os
import sqlite3
from django.conf import settings
from django.core.management import execute_from_command_line
from django.db import connection
from django.contrib.auth.models import User
from .models import Company, Branch, Warehouse, UserProfile

class DatabaseManager:
    """مدير قواعد البيانات المتعددة"""
    
    @staticmethod
    def create_company_database(company_code, company_name, admin_data):
        """إنشاء قاعدة بيانات جديدة للشركة"""
        try:
            # إنشاء اسم قاعدة البيانات
            db_name = f"erp_{company_code.lower()}.db"
            db_path = os.path.join(settings.BASE_DIR, 'databases', db_name)
            
            # إنشاء مجلد قواعد البيانات
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            
            # إنشاء قاعدة البيانات الجديدة
            conn = sqlite3.connect(db_path)
            conn.close()
            
            # تحديث إعدادات Django مؤقتاً
            original_db = settings.DATABASES['default']['NAME']
            settings.DATABASES['default']['NAME'] = db_path
            
            # تشغيل migrations على قاعدة البيانات الجديدة
            os.system(f'python manage.py migrate --database=default')
            
            # إنشاء الشركة والبيانات الأساسية
            DatabaseManager._create_company_data(company_code, company_name, admin_data)
            
            # إرجاع إعدادات قاعدة البيانات الأصلية
            settings.DATABASES['default']['NAME'] = original_db
            
            return {
                'success': True,
                'database_path': db_path,
                'database_name': db_name
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def _create_company_data(company_code, company_name, admin_data):
        """إنشاء البيانات الأساسية للشركة"""
        from datetime import date, timedelta
        
        # إنشاء الشركة
        company = Company.objects.create(
            code=company_code,
            name=company_name,
            database_name=f"erp_{company_code.lower()}.db",
            is_active=True,
            subscription_end=date.today() + timedelta(days=365)
        )
        
        # إنشاء المستخدم المدير
        admin_user = User.objects.create_user(
            username=admin_data['username'],
            password=admin_data['password'],
            first_name=admin_data['first_name'],
            last_name=admin_data['last_name'],
            email=admin_data['email'],
            is_active=True,
            is_staff=True,
            is_superuser=True
        )
        
        # إنشاء الفرع الرئيسي
        main_branch = Branch.objects.create(
            company=company,
            name='الفرع الرئيسي',
            code='MAIN',
            address=admin_data.get('address', ''),
            manager=admin_user,
            is_active=True
        )
        
        # إنشاء المخزن الرئيسي
        main_warehouse = Warehouse.objects.create(
            branch=main_branch,
            name='المخزن الرئيسي',
            code='MAIN_WH',
            is_active=True
        )
        
        # إنشاء ملف المستخدم
        UserProfile.objects.create(
            user=admin_user,
            company=company,
            default_branch=main_branch,
            default_warehouse=main_warehouse,
            is_active=True
        )
        
        return {
            'company': company,
            'admin_user': admin_user,
            'branch': main_branch,
            'warehouse': main_warehouse
        }
    
    @staticmethod
    def switch_database(company_code):
        """تبديل قاعدة البيانات"""
        try:
            db_name = f"erp_{company_code.lower()}.db"
            db_path = os.path.join(settings.BASE_DIR, 'databases', db_name)
            
            if os.path.exists(db_path):
                settings.DATABASES['default']['NAME'] = db_path
                connection.close()
                return True
            return False
        except:
            return False
    
    @staticmethod
    def get_available_companies():
        """الحصول على الشركات المتاحة"""
        try:
            databases_dir = os.path.join(settings.BASE_DIR, 'databases')
            if not os.path.exists(databases_dir):
                return []
            
            companies = []
            for file in os.listdir(databases_dir):
                if file.startswith('erp_') and file.endswith('.db'):
                    company_code = file.replace('erp_', '').replace('.db', '').upper()
                    
                    # تبديل قاعدة البيانات مؤقتاً للحصول على اسم الشركة
                    original_db = settings.DATABASES['default']['NAME']
                    settings.DATABASES['default']['NAME'] = os.path.join(databases_dir, file)
                    
                    try:
                        company = Company.objects.filter(code=company_code).first()
                        if company:
                            companies.append({
                                'code': company.code,
                                'name': company.name,
                                'database_file': file
                            })
                    except:
                        pass
                    finally:
                        settings.DATABASES['default']['NAME'] = original_db
            
            return companies
        except:
            return []