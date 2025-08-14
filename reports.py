# مدير التقارير
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Sale, Purchase, Product, Customer, Supplier, ProductStock

class ReportsManager:
    """مدير التقارير"""
    
    @staticmethod
    def sales_report(start_date=None, end_date=None, branch=None, warehouse=None):
        """تقرير المبيعات"""
        try:
            sales = Sale.objects.filter(status='confirmed')
            
            if start_date:
                sales = sales.filter(created_at__date__gte=start_date)
            if end_date:
                sales = sales.filter(created_at__date__lte=end_date)
            
            # حساب الإجماليات
            total_sales = sales.aggregate(
                total_amount=Sum('total_amount'),
                total_count=Count('id')
            )
            
            # أفضل العملاء
            top_customers = Customer.objects.filter(
                sale__in=sales
            ).annotate(
                total_purchases=Sum('sale__total_amount')
            ).order_by('-total_purchases')[:10]
            
            # أفضل المنتجات
            top_products = Product.objects.filter(
                saleitem__sale__in=sales
            ).annotate(
                total_sold=Sum('saleitem__quantity'),
                total_revenue=Sum('saleitem__total_price')
            ).order_by('-total_revenue')[:10]
            
            return {
                'total_amount': total_sales['total_amount'] or 0,
                'total_count': total_sales['total_count'] or 0,
                'top_customers': top_customers,
                'top_products': top_products,
                'sales_list': sales.select_related('customer')[:50]
            }
        except Exception as e:
            print(f"خطأ في تقرير المبيعات: {e}")
            return {
                'total_amount': 0,
                'total_count': 0,
                'top_customers': [],
                'top_products': [],
                'sales_list': []
            }
    
    @staticmethod
    def inventory_report(warehouse=None):
        """تقرير المخزون"""
        try:
            stocks = ProductStock.objects.select_related('product', 'warehouse')
            
            if warehouse:
                stocks = stocks.filter(warehouse=warehouse)
            
            # إجماليات المخزون
            total_products = stocks.count()
            low_stock_count = stocks.filter(
                current_stock__lte=models.F('min_stock')
            ).count()
            
            # قيمة المخزون
            total_value = 0
            for stock in stocks:
                if hasattr(stock.product, 'price'):
                    total_value += float(stock.current_stock) * float(stock.product.price)
            
            return {
                'total_products': total_products,
                'low_stock_count': low_stock_count,
                'total_value': total_value,
                'stock_list': stocks[:100],
                'low_stock_items': stocks.filter(
                    current_stock__lte=models.F('min_stock')
                )[:20]
            }
        except Exception as e:
            print(f"خطأ في تقرير المخزون: {e}")
            return {
                'total_products': 0,
                'low_stock_count': 0,
                'total_value': 0,
                'stock_list': [],
                'low_stock_items': []
            }
    
    @staticmethod
    def profit_loss_report(start_date=None, end_date=None):
        """ت��رير الأرباح والخسائر"""
        try:
            # المبيعات
            sales = Sale.objects.filter(status='confirmed')
            if start_date:
                sales = sales.filter(created_at__date__gte=start_date)
            if end_date:
                sales = sales.filter(created_at__date__lte=end_date)
            
            total_sales = sales.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
            
            # المشتريات
            purchases = Purchase.objects.filter(status='confirmed')
            if start_date:
                purchases = purchases.filter(created_at__date__gte=start_date)
            if end_date:
                purchases = purchases.filter(created_at__date__lte=end_date)
            
            total_purchases = purchases.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
            
            # الربح الإجمالي
            gross_profit = total_sales - total_purchases
            
            return {
                'total_sales': total_sales,
                'total_purchases': total_purchases,
                'gross_profit': gross_profit,
                'profit_margin': (gross_profit / total_sales * 100) if total_sales > 0 else 0
            }
        except Exception as e:
            print(f"خطأ في تقرير الأرباح والخسائر: {e}")
            return {
                'total_sales': 0,
                'total_purchases': 0,
                'gross_profit': 0,
                'profit_margin': 0
            }
    
    @staticmethod
    def customer_statement(customer, start_date=None, end_date=None):
        """كشف حساب العميل"""
        try:
            sales = Sale.objects.filter(customer=customer)
            
            if start_date:
                sales = sales.filter(created_at__date__gte=start_date)
            if end_date:
                sales = sales.filter(created_at__date__lte=end_date)
            
            total_amount = sales.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
            paid_amount = sales.aggregate(Sum('paid_amount'))['paid_amount__sum'] or 0
            remaining_amount = total_amount - paid_amount
            
            return {
                'customer': customer,
                'total_amount': total_amount,
                'paid_amount': paid_amount,
                'remaining_amount': remaining_amount,
                'sales_list': sales.order_by('-created_at')
            }
        except Exception as e:
            print(f"خطأ في كشف حساب العميل: {e}")
            return {
                'customer': customer,
                'total_amount': 0,
                'paid_amount': 0,
                'remaining_amount': 0,
                'sales_list': []
            }