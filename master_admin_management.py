# نظام إدارة صاحب البرنامج الشامل
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction
from datetime import date, timedelta
import os

from .models import Company, UserProfile
from .master_admin_models import (
    MasterAdmin, CompanySubscription, CompanyPayment, SystemSettings,
    CompanyDatabase, SystemAuditLog, CompanyUsageStats
)

class MasterAdminManager:
    """مدير نظام صاحب البرنامج"""
    
    @staticmethod
    def create_master_admin(username, password, full_name, email, phone):
        """إنشاء صاحب البرنامج الرئيسي"""
        try:
            with transaction.atomic():
                # إنشاء المستخدم
                user = User.objects.create_superuser(
                    username=username,
                    email=email,
                    password=password,
                    first_name=full_name.split()[0] if full_name else '',
                    last_name=' '.join(full_name.split()[1:]) if len(full_name.split()) > 1 else ''
                )
                
                # إنشاء ملف صاحب البرنامج
                master_admin = MasterAdmin.objects.create(
                    user=user,
                    full_name=full_name,
                    phone=phone,
                    email=email,
                    is_super_admin=True
                )
                
                # إنشاء الإعدادات الأساسية
                MasterAdminManager.create_default_settings()
                
                return master_admin
        except Exception as e:
            raise Exception(f"خطأ في إنشاء صاحب البرنامج: {str(e)}")
    
    @staticmethod
    def create_default_settings():
        """إنشاء الإعدادات الافتراضية للنظام"""
        default_settings = {
            'system_name': 'نظام إدارة الموارد المتقدم',
            'company_name': 'شركة تطوير البرمجيات',
            'support_email': 'support@erp-system.com',
            'support_phone': '+965-12345678',
            'backup_frequency': 'daily',
            'max_file_size_mb': '50',
            'session_timeout_minutes': '60',
            'maintenance_mode': 'false',
            'auto_backup': 'true',
            'email_notifications': 'true',
            'sms_notifications': 'false',
            'default_subscription_type': 'basic',
            'trial_period_days': '30',
            'max_companies': '1000',
            'max_users_per_company': '100',
            'storage_limit_gb': '10',
            'api_rate_limit': '1000',
            'password_expiry_days': '90',
            'login_attempts_limit': '5',
            'data_retention_months': '24',
        }
        
        for key, value in default_settings.items():
            SystemSettings.objects.get_or_create(
                key=key,
                defaults={
                    'value': value,
                    'description': f'إعداد {key}',
                    'setting_type': 'string',
                    'is_system': True
                }
            )
    
    @staticmethod
    def create_company_subscription(company, subscription_type='basic', months=1):
        """إنشاء اشتراك للشركة"""
        # تحديد رسوم الاشتراك
        subscription_fees = {
            'basic': {
                'monthly': 50, 'yearly': 500,
                'max_users': 5, 'max_branches': 1, 'max_warehouses': 3,
                'storage_gb': 1, 'features': ['basic_reports', 'inventory']
            },
            'standard': {
                'monthly': 100, 'yearly': 1000,
                'max_users': 15, 'max_branches': 3, 'max_warehouses': 10,
                'storage_gb': 5, 'features': ['basic_reports', 'inventory', 'pos', 'accounting']
            },
            'premium': {
                'monthly': 200, 'yearly': 2000,
                'max_users': 50, 'max_branches': 10, 'max_warehouses': 25,
                'storage_gb': 20, 'features': ['all_reports', 'inventory', 'pos', 'accounting', 'manufacturing', 'hr']
            },
            'enterprise': {
                'monthly': 500, 'yearly': 5000,
                'max_users': 200, 'max_branches': 50, 'max_warehouses': 100,
                'storage_gb': 100, 'features': ['all_features', 'api_access', 'custom_reports', 'multi_currency']
            }
        }
        
        fees = subscription_fees.get(subscription_type, subscription_fees['basic'])
        
        # حساب التواريخ
        start_date = date.today()
        end_date = start_date + timedelta(days=30 * months)
        
        # إنشاء الاشتراك
        subscription = CompanySubscription.objects.create(
            company=company,
            subscription_type=subscription_type,
            start_date=start_date,
            end_date=end_date,
            monthly_fee=fees['monthly'],
            yearly_fee=fees['yearly'],
            max_users=fees['max_users'],
            max_branches=fees['max_branches'],
            max_warehouses=fees['max_warehouses'],
            storage_limit_gb=fees['storage_gb'],
            features={
                'enabled_features': fees['features'],
                'pos_enabled': 'pos' in fees['features'],
                'manufacturing_enabled': 'manufacturing' in fees['features'],
                'hr_enabled': 'hr' in fees['features'],
                'api_enabled': 'api_access' in fees['features'],
            },
            payment_status='pending',
            is_active=True
        )
        
        # تحديث معلومات الشركة
        company.subscription_end = end_date
        company.subscription_type = subscription_type
        company.max_users = fees['max_users']
        company.max_branches = fees['max_branches']
        company.max_warehouses = fees['max_warehouses']
        company.storage_limit_gb = fees['storage_gb']
        company.features = subscription.features
        company.save()
        
        return subscription
    
    @staticmethod
    def process_payment(subscription, amount, payment_method='cash', reference_number=''):
        """معالجة دفعة الاشتراك"""
        payment = CompanyPayment.objects.create(
            subscription=subscription,
            amount=amount,
            payment_method=payment_method,
            reference_number=reference_number,
            payment_date=date.today(),
            is_confirmed=False
        )
        
        return payment
    
    @staticmethod
    def confirm_payment(payment, confirmed_by):
        """تأكيد الدفعة"""
        payment.is_confirmed = True
        payment.confirmed_by = confirmed_by
        payment.save()
        
        # تحديث حالة الاشتراك
        subscription = payment.subscription
        subscription.payment_status = 'paid'
        subscription.save()
        
        # تسجيل في سجل المراجعة
        SystemAuditLog.objects.create(
            user=confirmed_by,
            company=subscription.company,
            action_type='payment',
            model_name='CompanyPayment',
            object_id=payment.id,
            description=f'تأكيد دفعة #{payment.payment_number} بمبلغ {payment.amount}'
        )
    
    @staticmethod
    def create_company_database(company):
        """إنشاء قاعدة بيانات للشركة"""
        database_name = f"erp_{company.code.lower()}"
        
        # إنشاء مجلد قواعد البيانات إذا لم يكن موجوداً
        os.makedirs('databases', exist_ok=True)
        
        # نسخ قاعدة البيانات الأساسية
        import shutil
        source_db = 'db.sqlite3'
        target_db = f'databases/{database_name}.db'
        
        if os.path.exists(source_db):
            shutil.copy2(source_db, target_db)
        
        # حفظ معلومات قاعدة البيانات
        db_info = CompanyDatabase.objects.create(
            company=company,
            database_name=database_name,
            database_size_mb=0,
            backup_frequency='weekly',
            is_active=True
        )
        
        # تحديث معلومات الشركة
        company.database_name = database_name
        company.save()
        
        return db_info
    
    @staticmethod
    def collect_usage_statistics():
        """جمع إحصائيات الاستخدام اليومية"""
        from django.db.models import Sum, Count
        
        today = date.today()
        
        for company in Company.objects.filter(is_active=True):
            try:
                # حساب الإحصائيات
                active_users = UserProfile.objects.filter(
                    company=company,
                    is_active=True,
                    user__last_login__date=today
                ).count()
                
                # إحصائيات المبيعات (إذا كانت متاحة)
                total_sales = 0
                total_invoices = 0
                try:
                    from .models import Sale
                    sales_data = Sale.objects.filter(
                        company=company,
                        created_at__date=today
                    ).aggregate(
                        total=Sum('total_amount'),
                        count=Count('id')
                    )
                    total_sales = sales_data['total'] or 0
                    total_invoices = sales_data['count'] or 0
                except:
                    pass
                
                # حساب حجم قاعدة البيانات
                database_size = 0
                try:
                    db_path = f'databases/{company.database_name}.db'
                    if os.path.exists(db_path):
                        database_size = os.path.getsize(db_path) / (1024 * 1024)  # بالميجابايت
                except:
                    pass
                
                # حفظ الإحصائيات
                CompanyUsageStats.objects.update_or_create(
                    company=company,
                    date=today,
                    defaults={
                        'active_users': active_users,
                        'total_sales': total_sales,
                        'total_invoices': total_invoices,
                        'database_size_mb': database_size,
                        'storage_used_mb': database_size,
                    }
                )
                
            except Exception as e:
                print(f"خطأ في جمع إحصائيات الشركة {company.name}: {str(e)}")
    
    @staticmethod
    def check_expiring_subscriptions():
        """فحص الاشتراكات المنتهية قريباً"""
        from .master_admin_models import SystemNotification
        
        # الاشتراكات التي تنتهي خلال 7 أيام
        next_week = date.today() + timedelta(days=7)
        expiring_subscriptions = CompanySubscription.objects.filter(
            end_date__lte=next_week,
            end_date__gte=date.today(),
            is_active=True
        )
        
        for subscription in expiring_subscriptions:
            days_remaining = (subscription.end_date - date.today()).days
            
            # إنشاء إشعار
            SystemNotification.objects.get_or_create(
                title=f'انتهاء اشتراك {subscription.company.name}',
                message=f'سينتهي اشتراك شركة {subscription.company.name} خلال {days_remaining} أيام',
                notification_type='subscription_expiry',
                is_global=False,
                priority='high' if days_remaining <= 3 else 'medium',
                defaults={'expires_at': subscription.end_date}
            )
    
    @staticmethod
    def create_backup_for_company(company, backup_type='full'):
        """إنشاء نسخة احتياطية للشركة"""
        from .master_admin_models import CompanyBackup
        import shutil
        from datetime import datetime
        
        try:
            # إنشاء مجلد النسخ الاحتياطية
            os.makedirs('backups', exist_ok=True)
            
            # اسم النسخة الاحتياطية
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"backup_{company.code}_{timestamp}"
            backup_path = f"backups/{backup_name}.db"
            
            # نسخ قاعدة البيانات
            source_db = f"databases/{company.database_name}.db"
            if os.path.exists(source_db):
                shutil.copy2(source_db, backup_path)
                
                # حساب حجم الملف
                file_size = os.path.getsize(backup_path) / (1024 * 1024)  # بالميجابايت
                
                # حفظ معلومات النسخة
                backup = CompanyBackup.objects.create(
                    company=company,
                    backup_name=backup_name,
                    file_path=backup_path,
                    file_size_mb=file_size,
                    backup_type=backup_type,
                    is_automated=True
                )
                
                # تحديث آخر نسخة احتياطية
                try:
                    db_info = CompanyDatabase.objects.get(company=company)
                    db_info.last_backup = datetime.now()
                    db_info.save()
                except CompanyDatabase.DoesNotExist:
                    pass
                
                return backup
            else:
                raise Exception(f"لم يتم العثور على قاعدة بيانات الشركة: {source_db}")
                
        except Exception as e:
            raise Exception(f"خطأ في إنشاء النسخة الاحتياطية: {str(e)}")
    
    @staticmethod
    def cleanup_old_backups(days_to_keep=30):
        """تنظيف النسخ الاحتياطية القديمة"""
        from .master_admin_models import CompanyBackup
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        old_backups = CompanyBackup.objects.filter(created_at__lt=cutoff_date)
        
        for backup in old_backups:
            try:
                # حذف الملف
                if os.path.exists(backup.file_path):
                    os.remove(backup.file_path)
                
                # حذف السجل
                backup.delete()
            except Exception as e:
                print(f"خطأ في حذف النسخة الاحتياطية {backup.backup_name}: {str(e)}")
    
    @staticmethod
    def get_system_statistics():
        """الحصول على إحصائيات النظام العامة"""
        from django.db.models import Sum, Count, Avg
        
        stats = {
            'companies': {
                'total': Company.objects.count(),
                'active': Company.objects.filter(is_active=True).count(),
                'trial': Company.objects.filter(subscription_type='trial').count(),
                'premium': Company.objects.filter(subscription_type__in=['premium', 'enterprise']).count(),
            },
            'users': {
                'total': User.objects.count(),
                'active': User.objects.filter(is_active=True).count(),
                'superusers': User.objects.filter(is_superuser=True).count(),
            },
            'subscriptions': {
                'active': CompanySubscription.objects.filter(is_active=True, end_date__gte=date.today()).count(),
                'expired': CompanySubscription.objects.filter(end_date__lt=date.today()).count(),
                'expiring_soon': CompanySubscription.objects.filter(
                    end_date__lte=date.today() + timedelta(days=7),
                    end_date__gte=date.today()
                ).count(),
            },
            'revenue': {
                'total': CompanyPayment.objects.filter(is_confirmed=True).aggregate(
                    total=Sum('amount'))['total'] or 0,
                'this_month': CompanyPayment.objects.filter(
                    is_confirmed=True,
                    payment_date__month=date.today().month,
                    payment_date__year=date.today().year
                ).aggregate(total=Sum('amount'))['total'] or 0,
            },
            'storage': {
                'total_used': CompanyUsageStats.objects.filter(
                    date=date.today()
                ).aggregate(total=Sum('storage_used_mb'))['total'] or 0,
                'average_per_company': CompanyUsageStats.objects.filter(
                    date=date.today()
                ).aggregate(avg=Avg('storage_used_mb'))['avg'] or 0,
            }
        }
        
        return stats

# أوامر إدارية
class Command(BaseCommand):
    help = 'أوامر إدارة صاحب البرنامج'
    
    def add_arguments(self, parser):
        parser.add_argument('action', type=str, help='العملية المطلوبة')
        parser.add_argument('--username', type=str, help='اسم المستخدم')
        parser.add_argument('--password', type=str, help='كلمة المرور')
        parser.add_argument('--name', type=str, help='الاسم الكامل')
        parser.add_argument('--email', type=str, help='البريد الإلكتروني')
        parser.add_argument('--phone', type=str, help='رقم الهاتف')
    
    def handle(self, *args, **options):
        action = options['action']
        
        if action == 'create_master_admin':
            self.create_master_admin(options)
        elif action == 'collect_stats':
            self.collect_statistics()
        elif action == 'check_subscriptions':
            self.check_subscriptions()
        elif action == 'create_backups':
            self.create_backups()
        elif action == 'cleanup_backups':
            self.cleanup_backups()
        else:
            self.stdout.write(self.style.ERROR(f'عملية غير معروفة: {action}'))
    
    def create_master_admin(self, options):
        try:
            master_admin = MasterAdminManager.create_master_admin(
                username=options['username'],
                password=options['password'],
                full_name=options['name'],
                email=options['email'],
                phone=options['phone']
            )
            self.stdout.write(
                self.style.SUCCESS(f'تم إنشاء صاحب البرنامج: {master_admin.full_name}')
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'خطأ: {str(e)}'))
    
    def collect_statistics(self):
        try:
            MasterAdminManager.collect_usage_statistics()
            self.stdout.write(self.style.SUCCESS('تم جمع الإحصائيات بنجاح'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'خطأ في جمع الإحصائيات: {str(e)}'))
    
    def check_subscriptions(self):
        try:
            MasterAdminManager.check_expiring_subscriptions()
            self.stdout.write(self.style.SUCCESS('تم فحص الاشتراكات بنجاح'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'خطأ في فحص الاشتراكات: {str(e)}'))
    
    def create_backups(self):
        try:
            companies = Company.objects.filter(is_active=True)
            for company in companies:
                MasterAdminManager.create_backup_for_company(company)
            self.stdout.write(self.style.SUCCESS(f'تم إنشاء {companies.count()} نسخة احتياطية'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'خطأ في إنشاء النسخ الاحتياطية: {str(e)}'))
    
    def cleanup_backups(self):
        try:
            MasterAdminManager.cleanup_old_backups()
            self.stdout.write(self.style.SUCCESS('تم تنظيف النسخ الاحتياطية القديمة'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'خطأ في تنظيف النسخ الاحتياطية: {str(e)}'))