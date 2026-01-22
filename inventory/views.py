"""
Django views for Intelligent Inventory Management System.
Placeholder views - will be implemented in Module 2 (Data Entry).
"""

from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.contrib.auth.models import User
from django.contrib import messages

from .models import Product, SalesRecord, DemandForecast, InventoryAlert
from .forms import CustomUserCreationForm, CustomAuthenticationForm, ProductForm, SalesEntryForm, ProductFilterForm
import logging

logger = logging.getLogger(__name__)


# ==================== Authentication Views ====================

class RegisterView(CreateView):
    """User registration view."""
    model = User
    form_class = CustomUserCreationForm
    template_name = 'inventory/register.html'
    success_url = reverse_lazy('login')
    
    def form_valid(self, form):
        messages.success(self.request, 'Registration successful! Please log in.')
        return super().form_valid(form)


# ==================== Dashboard View ====================

class DashboardView(LoginRequiredMixin, TemplateView):
    """
    Main dashboard showing:
    - Overview of all products
    - Risk indicators
    - Recent alerts
    - Quick stats
    - Sales trends and analytics charts
    """
    template_name = 'inventory/dashboard.html'
    login_url = 'login'
    
    def get_context_data(self, **kwargs):
        from django.utils import timezone
        from datetime import timedelta
        import json
        from django.db.models import Sum, Count, Q
        
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # User's products
        products = Product.objects.filter(owner=user)
        context['products'] = products
        context['total_products'] = products.count()
        
        # Risk summary
        high_risk_alerts = InventoryAlert.objects.filter(
            product__owner=user,
            risk_level='high',
            acknowledged=False
        )
        context['high_risk_alerts'] = high_risk_alerts
        context['total_high_risk'] = high_risk_alerts.count()
        
        # Recent sales
        recent_sales = SalesRecord.objects.filter(
            product__owner=user
        ).select_related('product').order_by('-sale_date')[:10]
        context['recent_sales'] = recent_sales
        
        # Reorder recommendations
        reorder_needed = [p for p in products if p.get_reorder_recommendation()]
        context['reorder_needed'] = reorder_needed
        context['reorder_count'] = len(reorder_needed)
        
        # Sales trend (last 30 days)
        today = timezone.now().date()
        thirty_days_ago = today - timedelta(days=30)
        daily_sales = SalesRecord.objects.filter(
            product__owner=user,
            sale_date__gte=thirty_days_ago
        ).extra(select={'date': 'DATE(sale_date)'}).values('date').annotate(
            total_quantity=Sum('quantity_sold'),
            total_revenue=Sum('quantity_sold') * Sum('product__price')
        ).order_by('date')
        
        sales_dates = [str(s['date']) for s in daily_sales]
        sales_quantities = [s['total_quantity'] or 0 for s in daily_sales]
        context['sales_trend_dates'] = json.dumps(sales_dates)
        context['sales_trend_quantities'] = json.dumps(sales_quantities)
        
        # Category distribution
        category_sales = SalesRecord.objects.filter(
            product__owner=user
        ).values('product__category').annotate(
            total_quantity=Sum('quantity_sold'),
            count=Count('id')
        ).order_by('product__category')
        
        category_labels = [c['product__category'] for c in category_sales]
        category_quantities = [c['total_quantity'] or 0 for c in category_sales]
        context['category_labels'] = json.dumps(category_labels)
        context['category_quantities'] = json.dumps(category_quantities)
        
        # Top 5 selling products
        top_products = SalesRecord.objects.filter(
            product__owner=user
        ).values('product__name').annotate(
            total_sold=Sum('quantity_sold'),
            total_revenue=Sum('quantity_sold') * Sum('product__price')
        ).order_by('-total_sold')[:5]
        
        product_names = [p['product__name'] for p in top_products]
        product_quantities = [p['total_sold'] or 0 for p in top_products]
        context['top_products_names'] = json.dumps(product_names)
        context['top_products_quantities'] = json.dumps(product_quantities)
        
        # Stock levels by category
        stock_by_category = Product.objects.filter(
            owner=user
        ).values('category').annotate(
            total_stock=Sum('current_stock'),
            avg_stock=Sum('current_stock') / Count('id')
        ).order_by('category')
        
        stock_cat_labels = [s['category'] for s in stock_by_category]
        stock_levels = [s['total_stock'] or 0 for s in stock_by_category]
        context['stock_category_labels'] = json.dumps(stock_cat_labels)
        context['stock_category_levels'] = json.dumps(stock_levels)
        
        # Total revenue this month
        current_month_start = today.replace(day=1)
        monthly_sales = SalesRecord.objects.filter(
            product__owner=user,
            sale_date__gte=current_month_start
        ).aggregate(total=Sum('quantity_sold'))
        context['monthly_sales_volume'] = monthly_sales['total'] or 0
        
        return context


# ==================== Product Views ====================

class ProductListView(LoginRequiredMixin, ListView):
    """Display list of user's products with filtering and search."""
    model = Product
    template_name = 'inventory/product_list.html'
    context_object_name = 'products'
    paginate_by = 20
    login_url = 'login'
    
    def get_queryset(self):
        """Filter products by current user."""
        qs = Product.objects.filter(owner=self.request.user)
        
        # Apply search
        search = self.request.GET.get('search')
        if search:
            qs = qs.filter(name__icontains=search) | qs.filter(sku__icontains=search)
        
        # Apply category filter
        category = self.request.GET.get('category')
        if category:
            qs = qs.filter(category__icontains=category)
        
        # Apply sorting
        sort_by = self.request.GET.get('sort_by', '-updated_at')
        qs = qs.order_by(sort_by)
        
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = ProductFilterForm(self.request.GET or None)
        return context


class ProductDetailView(LoginRequiredMixin, DetailView):
    """
    Detailed view of a single product showing:
    - Current stock and reorder info
    - Historical sales
    - Demand forecast
    - Risk indicators
    """
    model = Product
    template_name = 'inventory/product_detail.html'
    context_object_name = 'product'
    login_url = 'login'
    
    def get_queryset(self):
        """Only show products belonging to current user."""
        return Product.objects.filter(owner=self.request.user)
    
    def get_context_data(self, **kwargs):
        import json
        context = super().get_context_data(**kwargs)
        product = self.object
        
        # Recent sales
        context['recent_sales'] = SalesRecord.objects.filter(
            product=product
        ).order_by('-sale_date')[:30]
        
        # Latest forecasts
        forecasts = DemandForecast.objects.filter(
            product=product
        ).order_by('forecast_date')[:14]
        context['forecasts'] = forecasts
        
        # Prepare forecast data for chart
        forecast_dates = [str(f.forecast_date) for f in forecasts]
        forecast_values = [float(f.predicted_demand) for f in forecasts]
        context['forecast_dates_json'] = json.dumps(forecast_dates)
        context['forecast_values_json'] = json.dumps(forecast_values)
        
        # Active alerts
        context['alerts'] = InventoryAlert.objects.filter(
            product=product,
            acknowledged=False
        ).order_by('-generated_at')
        
        return context


class ProductCreateView(LoginRequiredMixin, CreateView):
    """Create new product."""
    model = Product
    form_class = ProductForm
    template_name = 'inventory/product_form.html'
    login_url = 'login'
    success_url = reverse_lazy('product_list')
    
    def form_valid(self, form):
        form.instance.owner = self.request.user
        messages.success(self.request, f'Product "{form.instance.name}" added successfully!')
        logger.info(f"User {self.request.user.username} added product: {form.instance.name}")
        return super().form_valid(form)


class ProductUpdateView(LoginRequiredMixin, UpdateView):
    """Edit existing product."""
    model = Product
    form_class = ProductForm
    template_name = 'inventory/product_form.html'
    login_url = 'login'
    success_url = reverse_lazy('product_list')
    
    def get_queryset(self):
        """Only allow users to edit their own products."""
        return Product.objects.filter(owner=self.request.user)
    
    def form_valid(self, form):
        messages.success(self.request, f'Product "{form.instance.name}" updated successfully!')
        logger.info(f"User {self.request.user.username} updated product: {form.instance.name}")
        return super().form_valid(form)


class ProductDeleteView(LoginRequiredMixin, DeleteView):
    """Delete product."""
    model = Product
    template_name = 'inventory/product_confirm_delete.html'
    login_url = 'login'
    success_url = reverse_lazy('product_list')
    
    def get_queryset(self):
        """Only allow users to delete their own products."""
        return Product.objects.filter(owner=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        product_name = self.object.name
        logger.info(f"User {request.user.username} deleted product: {product_name}")
        messages.success(request, f'Product "{product_name}" deleted successfully.')
        return super().delete(request, *args, **kwargs)


# ==================== Sales Entry Views ====================

class SalesEntryView(LoginRequiredMixin, CreateView):
    """Form for recording daily sales."""
    model = SalesRecord
    form_class = SalesEntryForm
    template_name = 'inventory/sales_entry.html'
    login_url = 'login'
    success_url = reverse_lazy('sales_entry')
    
    def get_form_kwargs(self):
        """Pass user to form."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, 'Sale recorded successfully!')
        logger.info(f"User {self.request.user.username} recorded sale: {form.instance.product.name} - {form.instance.quantity_sold} units")
        return super().form_valid(form)


class SalesHistoryView(LoginRequiredMixin, ListView):
    """View sales history with filtering."""
    model = SalesRecord
    template_name = 'inventory/sales_history.html'
    context_object_name = 'sales'
    paginate_by = 50
    login_url = 'login'
    
    def get_queryset(self):
        """Get sales for current user's products."""
        qs = SalesRecord.objects.filter(
            product__owner=self.request.user
        ).select_related('product').order_by('-sale_date')
        
        # Apply product filter
        product_id = self.request.GET.get('product')
        if product_id:
            qs = qs.filter(product_id=product_id)
        
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['products'] = Product.objects.filter(owner=self.request.user)
        return context


# ==================== API Views (for AJAX dashboard updates) ====================

class ProductForecastAPIView(LoginRequiredMixin, View):
    """
    API endpoint returning forecast data for a product.
    Returns JSON with predicted demands for next 30 days.
    """
    login_url = 'login'
    
    def get(self, request, pk):
        try:
            product = Product.objects.get(id=pk, owner=request.user)
            forecasts = DemandForecast.objects.filter(
                product=product
            ).order_by('forecast_date').values('forecast_date', 'predicted_demand')
            
            return JsonResponse({
                'success': True,
                'product_name': product.name,
                'forecasts': list(forecasts)
            })
        except Product.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Product not found'}, status=404)


class ProductAlertsAPIView(LoginRequiredMixin, View):
    """
    API endpoint returning active alerts for a product.
    Returns JSON with alert details and risk levels.
    """
    login_url = 'login'
    
    def get(self, request, pk):
        try:
            product = Product.objects.get(id=pk, owner=request.user)
            alerts = InventoryAlert.objects.filter(
                product=product,
                acknowledged=False
            ).values('alert_type', 'risk_level', 'explanation', 'generated_at')
            
            return JsonResponse({
                'success': True,
                'product_name': product.name,
                'alerts': list(alerts),
                'alert_count': len(alerts)
            })
        except Product.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Product not found'}, status=404)
