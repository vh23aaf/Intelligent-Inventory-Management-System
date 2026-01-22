"""
Django forms for data entry in Intelligent Inventory Management System.
Forms are designed to be user-friendly and self-explanatory for small business users.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import Product, SalesRecord


class CustomUserCreationForm(UserCreationForm):
    """
    Custom user registration form with email.
    """
    email = forms.EmailField(
        max_length=254,
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    first_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})
        self.fields['password1'].help_text = None
        self.fields['password2'].help_text = None


class CustomAuthenticationForm(AuthenticationForm):
    """Custom login form with styling."""
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )


class ProductForm(forms.ModelForm):
    """
    Form for adding/editing products.
    User-friendly field organization with helpful labels and validation.
    """
    class Meta:
        model = Product
        fields = ['name', 'category', 'sku', 'price', 'current_stock', 'lead_time_days', 'safety_stock']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Wireless Mouse',
                'help_text': 'Product name'
            }),
            'category': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Electronics, Office Supplies',
                'help_text': 'Product category for organization'
            }),
            'sku': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., SKU-12345',
                'help_text': 'Stock Keeping Unit (unique identifier)'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'help_text': 'Unit price in currency'
            }),
            'current_stock': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0',
                'help_text': 'Current inventory count'
            }),
            'lead_time_days': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '7',
                'help_text': 'Days between order and delivery'
            }),
            'safety_stock': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0',
                'help_text': 'Buffer stock for demand variability (system-recommended)'
            }),
        }
    
    def clean(self):
        """Validate form data."""
        cleaned_data = super().clean()
        price = cleaned_data.get('price')
        if price and price <= 0:
            raise forms.ValidationError("Price must be greater than zero.")
        return cleaned_data


class SalesEntryForm(forms.ModelForm):
    """
    Simple form for recording daily sales.
    Minimal input required - only quantity sold and date.
    """
    product = forms.ModelChoiceField(
        queryset=Product.objects.none(),  # Will be populated in view
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Select Product'
    )
    
    class Meta:
        model = SalesRecord
        fields = ['product', 'quantity_sold', 'sale_date']
        widgets = {
            'quantity_sold': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0',
                'min': '0',
                'help_text': 'Units sold'
            }),
            'sale_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'help_text': 'Date of sale'
            }),
        }
    
    def __init__(self, user, *args, **kwargs):
        """
        Initialize form with user-specific product queryset.
        
        Args:
            user: Current authenticated user
        """
        super().__init__(*args, **kwargs)
        self.fields['product'].queryset = Product.objects.filter(owner=user).order_by('name')
    
    def clean_quantity_sold(self):
        """Validate quantity is positive."""
        qty = self.cleaned_data.get('quantity_sold')
        if qty and qty < 0:
            raise forms.ValidationError("Quantity sold cannot be negative.")
        return qty


class BulkSalesEntryForm(forms.Form):
    """
    Form for entering multiple sales records at once (e.g., end-of-day summary).
    Allows user to quickly log sales for multiple products.
    """
    sale_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'help_text': 'Date for all sales in this entry'
        })
    )
    
    def __init__(self, user, *args, **kwargs):
        """Initialize form with dynamic product fields."""
        super().__init__(*args, **kwargs)
        products = Product.objects.filter(owner=user).order_by('name')
        
        for product in products:
            field_name = f'product_{product.id}'
            self.fields[field_name] = forms.IntegerField(
                required=False,
                initial=0,
                widget=forms.NumberInput(attrs={
                    'class': 'form-control',
                    'placeholder': '0',
                    'min': '0',
                }),
                label=f'{product.name} ({product.sku or "No SKU"})'
            )


class ProductFilterForm(forms.Form):
    """
    Form for filtering products on dashboard.
    Allows users to view specific categories or search by name.
    """
    RISK_CHOICES = [
        ('', 'All Risk Levels'),
        ('high', 'High Risk Only'),
        ('medium', 'Medium Risk Only'),
        ('low', 'Low Risk Only'),
    ]
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search product name or SKU...',
        }),
        label='Search'
    )
    
    category = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Filter by category...',
        }),
        label='Category'
    )
    
    risk_level = forms.ChoiceField(
        required=False,
        choices=RISK_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Risk Level'
    )
    
    sort_by = forms.ChoiceField(
        required=False,
        choices=[
            ('name', 'Name (A-Z)'),
            ('-updated_at', 'Recently Updated'),
            ('current_stock', 'Low Stock First'),
            ('-current_stock', 'High Stock First'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Sort By'
    )
