"""
URLs للنظام
"""
from django.urls import path
from . import views
from .balance_sheet_views import balance_sheet
from . import permission_views
from .company_setup_views import setup_company

urlpatterns = [
    # المصادقة
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('setup-company/', setup_company, name='setup_company'),
    
    # لوحة التحكم
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # المنتجات
    path('products/', views.products, name='products'),
    path('products/add/', views.add_product, name='add_product'),
    path('products/edit/<int:product_id>/', views.edit_product, name='edit_product'),
    path('products/view/<int:product_id>/', views.view_product, name='view_product'),
    path('products/delete/<int:product_id>/', views.delete_product, name='delete_product'),
    path('products/duplicate/<int:product_id>/', views.duplicate_product, name='duplicate_product'),
    path('products/export/', views.export_products, name='export_products'),
    path('products/import/', views.import_products_page, name='import_products_page'),
    path('products/template/', views.download_products_template, name='download_products_template'),
    path('products/barcode/<int:product_id>/', views.print_barcode, name='print_barcode'),
    
    # العملاء
    path('customers/', views.customers_list, name='customers'),
    path('customers/add/', views.add_customer, name='add_customer'),
    path('customers/edit/<int:customer_id>/', views.edit_customer, name='edit_customer'),
    path('customers/view/<int:customer_id>/', views.view_customer, name='view_customer'),
    path('customers/delete/<int:customer_id>/', views.delete_customer, name='delete_customer'),
    path('customers/export/', views.export_customers, name='export_customers'),
    path('customers/import/', views.import_customers, name='import_customers'),
    path('customers/statement/<int:customer_id>/', views.customer_statement, name='customer_statement'),
    
    # المبيعات
    path('sales/', views.sales_list, name='sales'),
    path('sales/invoices/', views.invoices_management, name='invoices_management'),
    path('sales/add/', views.add_sale, name='add_sale'),
    path('sales/confirm/<int:sale_id>/', views.confirm_invoice, name='confirm_invoice'),
    path('sales/cancel/<int:sale_id>/', views.cancel_invoice, name='cancel_invoice'),
    path('sales/delete/<int:sale_id>/', views.delete_sale, name='delete_sale'),
    
    # المشتريات
    path('purchases/', views.purchases_list, name='purchases'),
    path('purchases/add/', views.add_purchase, name='add_purchase'),
    path('purchases/view/<int:purchase_id>/', views.view_purchase, name='view_purchase'),
    path('purchases/edit/<int:purchase_id>/', views.edit_purchase, name='edit_purchase'),
    path('purchases/delete/<int:purchase_id>/', views.delete_purchase, name='delete_purchase'),
    path('purchases/confirm/<int:purchase_id>/', views.confirm_purchase, name='confirm_purchase'),
    path('purchases/cancel/<int:purchase_id>/', views.cancel_purchase, name='cancel_purchase'),
    path('purchases/print/<int:purchase_id>/', views.print_purchase, name='print_purchase'),
    path('purchases/export/', views.export_purchases, name='export_purchases'),
    
    # الموردين
    path('suppliers/', views.suppliers_list, name='suppliers'),
    path('suppliers/add/', views.add_supplier, name='add_supplier'),
    path('suppliers/edit/<int:supplier_id>/', views.edit_supplier, name='edit_supplier'),
    path('suppliers/view/<int:supplier_id>/', views.view_supplier, name='view_supplier'),
    path('suppliers/delete/<int:supplier_id>/', views.delete_supplier, name='delete_supplier'),
    path('suppliers/export/', views.export_suppliers, name='export_suppliers'),
    path('suppliers/statement/<int:supplier_id>/', views.supplier_statement, name='supplier_statement'),
    
    # المخزون
    path('stock/', views.stock_list, name='stock'),
    path('stock/adjust/', views.adjust_stock, name='adjust_stock'),
    path('stock/add/<int:product_id>/', views.add_stock, name='add_stock'),
    path('stock/export/', views.export_stock, name='export_stock'),
    
    # المحاسبة
    path('accounts/', views.accounts, name='accounts'),
    path('accounts/add/', views.add_account, name='add_account'),
    path('accounts/edit/<int:account_id>/', views.edit_account, name='edit_account'),
    path('accounts/delete/<int:account_id>/', views.delete_account, name='delete_account'),
    path('accounts/tree/', views.accounting_tree, name='accounting_tree'),
    path('accounts/customers/', views.customer_accounts, name='customer_accounts'),
    path('accounts/suppliers/', views.supplier_accounts, name='supplier_accounts'),
    path('accounts/sales/', views.sales_accounts, name='sales_accounts'),
    path('accounts/purchases/', views.purchase_accounts, name='purchase_accounts'),
    path('accounts/summary/', views.accounts_summary, name='accounts_summary'),
    path('accounts/ledger/<int:account_id>/', views.account_ledger, name='account_ledger'),
    path('accounts/trial-balance/', views.trial_balance, name='trial_balance'),
    path('accounts/balance-sheet/', balance_sheet, name='balance_sheet'),
    path('accounts/journal-entries/', views.journal_entries_list, name='journal_entries'),
    path('accounts/journal-entries/add/', views.add_journal_entry, name='add_journal_entry'),
    path('accounts/vouchers/', views.vouchers_list, name='vouchers'),
    path('accounts/vouchers/add/', views.add_voucher, name='add_voucher'),
    
    # التقارير
    path('reports/', views.reports_center, name='reports'),
    path('reports/add/', views.add_report, name='add_report'),
    path('reports/income-statement/', views.income_statement_report, name='income_statement_report'),
    path('accounts/income-statement/', views.income_statement_report, name='income_statement'),
    
    # الإعدادات
    path('settings/', views.settings_page, name='settings'),
    path('settings/add/', views.add_setting, name='add_setting'),
    
    # المستخدمين والصلاحيات
    path('users/', views.users_list, name='users'),
    path('users/add/', views.add_user, name='add_user'),
    path('users/edit/<int:user_id>/', views.edit_user, name='edit_user'),
    path('users/delete/<int:user_id>/', views.delete_user, name='delete_user'),
    path('permissions/', views.permissions_management, name='permissions'),
    path('permissions/dashboard/', permission_views.permissions_dashboard, name='permissions_dashboard'),
    path('permissions/users/', permission_views.users_permissions_list, name='users_permissions_list'),
    path('permissions/update/', views.update_permission, name='update_permission'),
    path('permissions/update-user/', permission_views.update_user_permissions, name='update_user_permissions'),
    path('permissions/user/<int:user_id>/', permission_views.user_permissions_detail, name='user_permissions_detail'),
    path('permissions/template/<int:user_id>/<str:template_name>/', permission_views.apply_permission_template, name='apply_permission_template'),
    path('permissions/export/', permission_views.export_permissions, name='export_permissions'),
    
    # الموظفين
    path('employees/', views.employees_list, name='employees'),
    path('employees/add/', views.add_employee, name='add_employee'),
    
    # مناديب المبيعات
    path('sales-reps/', views.sales_reps_list, name='sales_reps'),
    path('sales-reps/add/', views.add_sales_rep, name='add_sales_rep'),
    path('sales-reps/edit/<int:rep_id>/', views.edit_sales_rep, name='edit_sales_rep'),
    path('sales-reps/delete/<int:rep_id>/', views.delete_sales_rep, name='delete_sales_rep'),
    path('sales-reps/export/', views.export_sales_reps, name='export_sales_reps'),
    
    # الحضور والانصراف
    path('attendance/', views.attendance_list, name='attendance'),
    path('attendance/add/', views.add_attendance, name='add_attendance'),
    path('attendance/edit/<int:attendance_id>/', views.edit_attendance, name='edit_attendance'),
    path('attendance/delete/<int:attendance_id>/', views.delete_attendance, name='delete_attendance'),
    path('attendance/export/', views.export_attendance, name='export_attendance'),
    
    # الرواتب
    path('salaries/', views.salaries_list, name='salaries'),
    path('salaries/add/', views.add_salary, name='add_salary'),
    path('salaries/edit/<int:salary_id>/', views.edit_salary, name='edit_salary'),
    path('salaries/delete/<int:salary_id>/', views.delete_salary, name='delete_salary'),
    path('salaries/confirm/<int:salary_id>/', views.confirm_salary, name='confirm_salary'),
    path('salaries/pay/<int:salary_id>/', views.pay_salary, name='pay_salary'),
    path('salaries/generate/', views.generate_salaries, name='generate_salaries'),
    path('salaries/bulk-pay/', views.bulk_pay_salaries, name='bulk_pay_salaries'),
    path('salaries/print/<int:salary_id>/', views.print_salary_slip, name='print_salary_slip'),
    path('salaries/export/', views.export_salaries, name='export_salaries'),
    
    # دفعات العملاء
    path('customer-payments/', views.customer_payments_list, name='customer_payments'),
    path('customer-payments/add/', views.add_customer_payment, name='add_customer_payment'),
    
    # الفروع والمخازن
    path('branches/', views.branches_list, name='branches'),
    path('branches/add/', views.add_branch, name='add_branch'),
    path('warehouses/', views.warehouses_list, name='warehouses'),
    path('warehouses/add/', views.add_warehouse, name='add_warehouse'),
    
    # التصنيع
    path('manufacturing/', views.manufacturing_list, name='manufacturing'),
    
    # نقاط البيع
    path('pos/', views.pos, name='pos'),
    path('pos/open-session/', views.pos_open_session, name='pos_open_session'),
    path('pos/start-session/', views.pos_open_session, name='start_pos_session'),
    path('pos/close-session/<int:session_id>/', views.pos_close_session, name='pos_close_session'),
    path('pos/session-report/<int:session_id>/', views.pos_session_report, name='pos_session_report'),
    path('pos/sale/', views.pos_sale, name='pos_sale'),
    path('pos/sale-screen/<int:session_id>/', views.pos_sale, name='pos_sale_screen'),
    
    # APIs
    path('api/search-products/', views.search_products_api, name='search_products_api'),
    path('api/product-details/<int:product_id>/', views.get_product_details_api, name='get_product_details_api'),
    path('api/quick-add-product/', views.quick_add_product_api, name='quick_add_product_api'),
    path('api/update-setting/', views.update_setting_ajax, name='update_setting_ajax'),
    path('api/get-setting/<str:key>/', views.get_setting_ajax, name='get_setting_ajax'),
    path('api/get-all-settings/', views.get_all_settings_ajax, name='get_all_settings_ajax'),
    path('api/customer-invoices/<int:customer_id>/', views.get_customer_invoices, name='get_customer_invoices'),
    path('api/customer-returns/<int:customer_id>/', views.get_customer_returns, name='get_customer_returns'),
    path('api/customer-payments/<int:customer_id>/', views.get_customer_payments, name='get_customer_payments'),
    path('api/customer-summary/<int:customer_id>/', views.get_customer_summary, name='get_customer_summary'),
    path('api/salary-details/<int:salary_id>/', views.salary_details, name='salary_details'),
    path('api/product-movements/<int:product_id>/', views.get_product_movements, name='get_product_movements'),
    path('api/adjust-stock/', views.adjust_stock_api, name='adjust_stock_api'),
]