from .models import Company, Setting

def global_settings(request):
    """إضافة الإعدادات العامة لجميع القوالب"""
    context = {}
    user_permissions = {}
    
    # معلومات الشركة الحالية
    if hasattr(request, 'company') and request.company:
        context.update({
            'company_name': request.company.name,
            'company_logo_url': request.company.logo.url if request.company.logo else None,
            'company_address': request.company.address,
            'company_phone': request.company.phone,
            'company_email': request.company.email,
        })
    else:
        # قيم افتراضية
        context.update({
            'company_name': 'نظام ERP',
            'company_logo_url': None,
            'company_address': '',
            'company_phone': '',
            'company_email': '',
        })
    
    # جلب صلاحيات المستخدم
    if hasattr(request, 'user') and request.user.is_authenticated:
        try:
            from .models import Permission
            company = getattr(request, 'company', None)
            if company:
                permissions = Permission.objects.filter(
                    user=request.user,
                    company=company
                )
                
                for permission in permissions:
                    if permission.screen not in user_permissions:
                        user_permissions[permission.screen] = []
                    
                    actions = []
                    if permission.can_view: actions.append('view')
                    if permission.can_add: actions.append('add')
                    if permission.can_edit: actions.append('edit')
                    if permission.can_delete: actions.append('delete')
                    if permission.can_confirm: actions.append('confirm')
                    if permission.can_print: actions.append('print')
                    if permission.can_export: actions.append('export')
                    
                    user_permissions[permission.screen] = actions
        except:
            pass
    
    # الإعدادات العامة (مفلترة حسب الشركة)
    try:
        settings_dict = {}
        company = getattr(request, 'company', None)
        
        if company:
            # الحصول على إعدادات الشركة الحالية
            for setting in Setting.objects.filter(company=company):
                settings_dict[setting.key] = setting.get_value()
        else:
            # الإعدادات العامة
            for setting in Setting.objects.filter(is_global=True):
                settings_dict[setting.key] = setting.get_value()
        
        context.update({
            'currency_symbol': settings_dict.get('currency_symbol', 'د.ك'),
            'theme_color': settings_dict.get('theme_color', 'blue'),
            'system_settings': settings_dict,
        })
    except:
        context.update({
            'currency_symbol': 'د.ك',
            'theme_color': 'blue',
            'system_settings': {},
        })
    
    context['user_permissions'] = user_permissions
    return context