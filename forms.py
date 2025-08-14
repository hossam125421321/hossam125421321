from django import forms
from django.contrib.auth.models import User
from django.db import models
from .models import (
    CostCenter, Product, Customer, Supplier, Sale, Purchase, 
    Company, Branch, Warehouse, Employee, SalesRep, Attendance, Salary
)

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'barcode', 'category', 'unit', 'description', 'image']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم المنتج'}),
            'barcode': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'الباركود'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'unit': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'image': forms.FileInput(attrs={'class': 'form-control'})
        }

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['name', 'phone', 'email', 'address', 'credit_limit', 'opening_balance']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم العميل'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'رقم الهاتف'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'البريد الإلكتروني'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'credit_limit': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'opening_balance': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
        }

class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'phone', 'email', 'address', 'opening_balance']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم المورد'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'رقم الهاتف'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'البريد الإلكتروني'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'opening_balance': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
        }

class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ['name', 'code', 'subscription_end', 'subscription_type', 'logo']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم الشركة'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'كود الشركة'}),
            'subscription_end': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'subscription_type': forms.Select(attrs={'class': 'form-control'}),
            'logo': forms.FileInput(attrs={'class': 'form-control'})
        }

class BranchForm(forms.ModelForm):
    class Meta:
        model = Branch
        fields = ['company', 'name', 'code', 'address', 'manager']
        widgets = {
            'company': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم الفرع'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'كود الفرع'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'manager': forms.Select(attrs={'class': 'form-control'})
        }

class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = ['branch', 'name', 'code']
        widgets = {
            'branch': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم المخزن'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'كود المخزن'})
        }

class UserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم المستخدم'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'البريد الإلكتروني'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'الاسم الأول'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'الاسم الأخير'})
        }

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ['user', 'national_id', 'phone', 'address', 'birth_date', 'hire_date', 
                 'department', 'position', 'basic_salary', 'overtime_rate', 'employment_status', 
                 'employment_type', 'branch', 'fingerprint_id']
        widgets = {
            'user': forms.Select(attrs={'class': 'form-control'}),
            'national_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'رقم الهوية'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'رقم الهاتف'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'birth_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'hire_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'department': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'القسم'}),
            'position': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'المنصب'}),
            'basic_salary': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'overtime_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'employment_status': forms.Select(attrs={'class': 'form-control'}),
            'employment_type': forms.Select(attrs={'class': 'form-control'}),
            'branch': forms.Select(attrs={'class': 'form-control'}),
            'fingerprint_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'معرف البصمة'})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # إظهار المستخدمين الذين ليس لديهم ملف موظف
        if self.instance.pk:
            # في حالة التعديل، أضف المستخدم الحالي للخيارات
            self.fields['user'].queryset = User.objects.filter(
                models.Q(employee__isnull=True) | models.Q(pk=self.instance.user.pk)
            )
        else:
            # في حالة الإضافة، أظهر المستخدمين بدون ملف موظف فقط
            self.fields['user'].queryset = User.objects.filter(employee__isnull=True)
        
        # تحسين عرض المستخدمين
        self.fields['user'].empty_label = "اختر مستخدم"

class SalesRepForm(forms.ModelForm):
    class Meta:
        model = SalesRep
        fields = ['employee', 'commission_rate', 'target_amount', 'is_active']
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-control'}),
            'commission_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'target_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # إظهار الموظفين الذين ليسوا مندوبي مبيعات
        if self.instance.pk:
            self.fields['employee'].queryset = Employee.objects.filter(
                models.Q(salesrep__isnull=True) | models.Q(pk=self.instance.employee.pk)
            )
        else:
            self.fields['employee'].queryset = Employee.objects.filter(salesrep__isnull=True)
        
        # تحسين عرض الموظفين
        self.fields['employee'].empty_label = "اختر موظف"

class AttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ['employee', 'date', 'check_in', 'check_out', 'status', 'notes']
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'check_in': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'check_out': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
        }

class SalaryForm(forms.ModelForm):
    class Meta:
        model = Salary
        fields = ['employee', 'month', 'year', 'basic_salary', 'allowances', 'deductions', 
                 'overtime_hours', 'overtime_rate', 'status', 'notes']
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-control'}),
            'month': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '12'}),
            'year': forms.NumberInput(attrs={'class': 'form-control'}),
            'basic_salary': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'allowances': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'deductions': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'overtime_hours': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'overtime_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
        }

class CostCenterForm(forms.ModelForm):
    class Meta:
        model = CostCenter
        fields = ['name', 'code', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم مركز التكلفة'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'كود مركز التكلفة'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }