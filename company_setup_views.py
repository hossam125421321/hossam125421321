# -*- coding: utf-8 -*-
"""
Views إعداد الشركات الجديدة
"""
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from .database_manager import DatabaseManager
from .models import Company, Branch, Warehouse, UserProfile
from datetime import date, timedelta
import os
import sqlite3
from django.conf import settings

def setup_company(request):
    """صفحة إعداد شركة جديدة"""
    if request.method == 'POST':
        try:
            # جلب البيانات
            company_name = request.POST.get('company_name', '').strip()
            company_code = request.POST.get('company_code', '').strip().upper()
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            username = request.POST.get('username', '').strip()
            password = request.POST.get('password', '').strip()
            password_confirm = request.POST.get('password_confirm', '').strip()
            email = request.POST.get('email', '').strip()
            address = request.POST.get('address', '').strip()
            
            # التحقق من البيانات
            if not all([company_name, company_code, first_name, username, password]):
                messages.error(request, 'يرجى ملء جميع الحقول المطلوبة')
                return render(request, 'setup_company.html')
            
            if password != password_confirm:
                messages.error(request, 'كلمة المرور وتأكيد كلمة المرور غير متطابقتين')
                return render(request, 'setup_company.html')
            
            if len(password) < 6:
                messages.error(request, 'كلمة المرور يجب أن تكون 6 أحرف على الأقل')
                return render(request, 'setup_company.html')
            
            # التحقق من عدم تكرار كود الشركة
            if Company.objects.filter(code=company_code).exists():
                messages.error(request, f'كود الشركة "{company_code}" موجود بالفعل')
                return render(request, 'setup_company.html')
            
            # التحقق من عدم تكرار اسم المستخدم
            if User.objects.filter(username=username).exists():
                messages.error(request, f'اسم المستخدم "{username}" موجود بالفعل')
                return render(request, 'setup_company.html')
            
            # إنشاء قاعدة البيانات والشركة
            result = create_new_company_database(
                company_code=company_code,
                company_name=company_name,
                admin_data={
                    'username': username,
                    'password': password,
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': email,
                    'address': address
                }
            )
            
            if result['success']:
                messages.success(request, f'تم إنشاء الشركة "{company_name}" وقاعدة البيانات بنجاح!')
                
                # تسجيل دخول المستخدم الجديد
                user = authenticate(request, username=username, password=password)
                if user:
                    login(request, user)
                    request.session['company_code'] = company_code
                    return redirect('dashboard')
                else:
                    messages.success(request, 'تم إنشاء الشركة بنجاح، يمكنك الآن تسجيل الدخول')
                    return redirect('login')
            else:
                messages.error(request, f'خطأ في إنشاء الشركة: {result["error"]}')
                
        except Exception as e:
            messages.error(request, f'خطأ غير متوقع: {str(e)}')
    
    return render(request, 'setup_company.html')

def create_new_company_database(company_code, company_name, admin_data):
    """إنشاء قاعدة بيانات جديدة للشركة"""
    try:
        # إنشاء مجلد قواعد البيانات
        databases_dir = os.path.join(settings.BASE_DIR, 'databases')
        os.makedirs(databases_dir, exist_ok=True)
        
        # إنشاء قاعدة البيانات الجديدة
        db_name = f"erp_{company_code.lower()}.db"
        db_path = os.path.join(databases_dir, db_name)
        
        # التحقق من عدم وجود قاعدة البيانات
        if os.path.exists(db_path):
            return {'success': False, 'error': 'قاعدة البيانات موجودة بالفعل'}
        
        # نسخ قاعدة البيانات الرئيسية بدلاً من إنشاء قاعدة فارغة
        main_db_path = os.path.join(settings.BASE_DIR, 'db.sqlite3')
        if os.path.exists(main_db_path):
            import shutil
            shutil.copy2(main_db_path, db_path)
        else:
            # إنشاء قاعدة البيانات الفارغة كحل احتياطي
            conn = sqlite3.connect(db_path)
            conn.close()
            
            # حفظ إعدادات قاعدة البيانات الحالية
            original_db_name = settings.DATABASES['default']['NAME']
            
            # تبديل إلى قاعدة البيانات الجديدة
            settings.DATABASES['default']['NAME'] = db_path
            
            # تشغيل migrations لإنشاء جميع الجداول
            from django.core.management import call_command
            call_command('migrate', verbosity=0, interactive=False)
        
        # حفظ إعدادات قاعدة البيانات الحالية
        original_db_name = settings.DATABASES['default']['NAME']
        
        # تبديل إلى قاعدة البيانات الجديدة
        settings.DATABASES['default']['NAME'] = db_path
        
        # إنشاء البيانات الأساسية
        company = Company.objects.create(
            code=company_code,
            name=company_name,
            database_name=db_name,
            is_active=True,
            subscription_end=date.today() + timedelta(days=365)
        )
        
        # إنشاء المستخدم المدير في قاعدة البيانات الجديدة
        try:
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
        except Exception as e:
            if 'UNIQUE constraint failed' in str(e):
                raise Exception(f'اسم المستخدم "{admin_data["username"]}" موجود بالفعل')
            else:
                raise e
        
        # إضافة المستخدم إلى قاعدة البيانات الرئيسية أيضاً
        settings.DATABASES['default']['NAME'] = original_db_name
        try:
            main_user, created = User.objects.get_or_create(
                username=admin_data['username'],
                defaults={
                    'password': admin_user.password,
                    'first_name': admin_data['first_name'],
                    'last_name': admin_data['last_name'],
                    'email': admin_data['email'],
                    'is_active': True,
                    'is_staff': True,
                    'is_superuser': True
                }
            )
            # ربط المستخدم بالشركة في قاعدة البيانات الرئيسية
            UserProfile.objects.get_or_create(
                user=main_user,
                defaults={
                    'company': company,
                    'is_active': True
                }
            )
        except:
            pass
        
        # العودة إلى قاعدة البيانات الجديدة
        settings.DATABASES['default']['NAME'] = db_path
        
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
            company=company,
            branch=main_branch,
            name='المخزن الرئيسي',
            code='MAIN_WH',
            is_active=True
        )
        
        # إنشاء ملف المستخدم
        UserProfile.objects.get_or_create(
            user=admin_user,
            defaults={
                'company': company,
                'default_branch': main_branch,
                'default_warehouse': main_warehouse,
                'is_active': True
            }
        )
        
        # إعطاء صلاحيات المدير العام للمستخدم الرئيسي
        try:
            from .models import Permission
            screens = [
                'dashboard', 'products', 'customers', 'suppliers', 'sales_reps', 'sales', 'purchases',
                'stock', 'accounts', 'reports', 'settings', 'users', 'permissions',
                'companies', 'branches', 'warehouses', 'pos', 'manufacturing',
                'attendance', 'salaries', 'employees'
            ]
            
            for screen in screens:
                Permission.objects.get_or_create(
                    user=admin_user,
                    screen=screen,
                    company=company,
                    defaults={
                        'can_view': True,
                        'can_add': True,
                        'can_edit': True,
                        'can_delete': True,
                        'can_confirm': True,
                        'can_print': True,
                        'can_export': True,
                        'created_by': admin_user
                    }
                )
        except Exception as e:
            pass  # تجاهل أخطاء الصلاحيات
        
        # إرجاع إعدادات قاعدة البيانات الأصلية
        try:
            settings.DATABASES['default']['NAME'] = original_db_name
        except:
            settings.DATABASES['default']['NAME'] = os.path.join(settings.BASE_DIR, 'db.sqlite3')
        
        return {
            'success': True,
            'database_path': db_path,
            'company_code': company_code,
            'admin_username': admin_data['username']
        }
        
    except Exception as e:
        # إرجاع إعدادات قاعدة البيانات الأصلية في حالة الخطأ
        try:
            settings.DATABASES['default']['NAME'] = original_db_name
        except:
            pass
        
        # حذف قاعدة البيانات المعطوبة
        try:
            if os.path.exists(db_path):
                os.remove(db_path)
        except:
            pass
        
        return {
            'success': False,
            'error': str(e)
        }

def get_companies_list():
    """الحصول على قائمة الشركات المتاحة"""
    try:
        databases_dir = os.path.join(settings.BASE_DIR, 'databases')
        if not os.path.exists(databases_dir):
            return []
        
        companies = []
        for file in os.listdir(databases_dir):
            if file.startswith('erp_') and file.endswith('.db'):
                company_code = file.replace('erp_', '').replace('.db', '').upper()
                
                # قراءة اسم الشركة من قاعدة البيانات
                db_path = os.path.join(databases_dir, file)
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM core_company WHERE code = ?", (company_code,))
                    result = cursor.fetchone()
                    conn.close()
                    
                    if result:
                        companies.append({
                            'code': company_code,
                            'name': result[0]
                        })
                except:
                    continue
        
        return companies
    except:
        return []