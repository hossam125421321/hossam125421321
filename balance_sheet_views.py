from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from datetime import date
from .models import Account, Sale, Purchase
from .decorators import subscription_required, permission_required

@login_required
@subscription_required
@permission_required('accounts', 'view')
def balance_sheet(request):
    """عرض الميزانية العمومية"""
    
    # جلب الأصول
    assets = Account.objects.filter(account_type='asset').order_by('account_code')
    total_assets = assets.aggregate(Sum('balance'))['balance__sum'] or 0
    
    # جلب الخصوم
    liabilities = Account.objects.filter(account_type='liability').order_by('account_code')
    total_liabilities = liabilities.aggregate(Sum('balance'))['balance__sum'] or 0
    
    # جلب حقوق الملكية
    equity_accounts = Account.objects.filter(account_type='equity').order_by('account_code')
    total_equity_accounts = equity_accounts.aggregate(Sum('balance'))['balance__sum'] or 0
    
    # حساب صافي الربح/الخسارة
    total_revenue = Account.objects.filter(account_type='revenue').aggregate(Sum('balance'))['balance__sum'] or 0
    total_expenses = Account.objects.filter(account_type='expense').aggregate(Sum('balance'))['balance__sum'] or 0
    net_income = total_revenue - total_expenses
    
    # إجمالي حقوق الملكية (بما في ذلك صافي الربح)
    total_equity = total_equity_accounts + net_income
    
    # إجمالي الخصوم وحقوق الملكية
    total_liabilities_equity = total_liabilities + total_equity
    
    # فحص التوازن
    is_balanced = abs(total_assets - total_liabilities_equity) < 0.01
    balance_difference = total_assets - total_liabilities_equity
    
    # إحصائيات
    total_accounts = Account.objects.count()
    
    # الحصول على العملة من الإعدادات
    from .views import get_setting
    currency_symbol = get_setting('currency_symbol', 'د.ك')
    
    context = {
        'assets': assets,
        'liabilities': liabilities,
        'equity_accounts': equity_accounts,
        'total_assets': float(total_assets),
        'total_liabilities': float(total_liabilities),
        'total_equity': float(total_equity),
        'total_liabilities_equity': float(total_liabilities_equity),
        'net_income': float(net_income),
        'is_balanced': is_balanced,
        'balance_difference': float(balance_difference),
        'total_accounts': total_accounts,
        'report_date': date.today(),
        'currency_symbol': currency_symbol,
    }
    
    return render(request, 'balance_sheet.html', context)