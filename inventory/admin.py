"""
Django admin configuration for Intelligent Inventory Management System.
Provides user-friendly interface for data management and model monitoring.
"""

from django.contrib import admin
from .models import Product, SalesRecord, DemandForecast, InventoryAlert, ModelEvaluation


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Admin interface for Product model."""
    list_display = ['name', 'category', 'current_stock', 'price', 'lead_time_days', 'owner', 'updated_at']
    list_filter = ['category', 'owner', 'created_at']
    search_fields = ['name', 'sku', 'category']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('owner', 'name', 'category', 'sku', 'price')
        }),
        ('Inventory Levels', {
            'fields': ('current_stock', 'lead_time_days', 'reorder_point', 'safety_stock')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Filter products by current user (non-superusers only see their own products)."""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(owner=request.user)


@admin.register(SalesRecord)
class SalesRecordAdmin(admin.ModelAdmin):
    """Admin interface for SalesRecord model."""
    list_display = ['product', 'quantity_sold', 'sale_date', 'revenue', 'created_at']
    list_filter = ['sale_date', 'product__category', 'product__owner']
    search_fields = ['product__name']
    readonly_fields = ['created_at', 'revenue']
    date_hierarchy = 'sale_date'
    
    def get_queryset(self, request):
        """Filter records by current user's products."""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(product__owner=request.user)


@admin.register(DemandForecast)
class DemandForecastAdmin(admin.ModelAdmin):
    """Admin interface for DemandForecast model."""
    list_display = ['product', 'forecast_date', 'predicted_demand', 'model_used', 'confidence_score', 'created_at']
    list_filter = ['model_used', 'forecast_date', 'product__owner']
    search_fields = ['product__name']
    readonly_fields = ['created_at', 'mae', 'rmse']
    date_hierarchy = 'forecast_date'
    fieldsets = (
        ('Forecast Information', {
            'fields': ('product', 'forecast_date', 'predicted_demand', 'model_used', 'confidence_score')
        }),
        ('Model Evaluation', {
            'fields': ('mae', 'rmse'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Filter forecasts by current user's products."""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(product__owner=request.user)


@admin.register(InventoryAlert)
class InventoryAlertAdmin(admin.ModelAdmin):
    """Admin interface for InventoryAlert model."""
    list_display = ['product', 'alert_type', 'risk_level', 'generated_at', 'acknowledged']
    list_filter = ['alert_type', 'risk_level', 'generated_at', 'product__owner']
    search_fields = ['product__name', 'explanation']
    readonly_fields = ['explanation', 'forecasted_demand_7d', 'current_stock', 'generated_at']
    actions = ['mark_as_acknowledged']
    date_hierarchy = 'generated_at'
    
    def mark_as_acknowledged(self, request, queryset):
        """Mark selected alerts as acknowledged."""
        updated = queryset.update(acknowledged=True)
        self.message_user(request, f'{updated} alert(s) marked as acknowledged.')
    mark_as_acknowledged.short_description = "Mark selected alerts as acknowledged"
    
    def get_queryset(self, request):
        """Filter alerts by current user's products."""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(product__owner=request.user)


@admin.register(ModelEvaluation)
class ModelEvaluationAdmin(admin.ModelAdmin):
    """Admin interface for ModelEvaluation model."""
    list_display = ['product', 'model_name', 'mae', 'rmse', 'r2_score', 'evaluation_date']
    list_filter = ['model_name', 'evaluation_date', 'product__owner']
    search_fields = ['product__name']
    readonly_fields = ['evaluation_date']
    date_hierarchy = 'evaluation_date'
    fieldsets = (
        ('Model Information', {
            'fields': ('product', 'model_name')
        }),
        ('Metrics', {
            'fields': ('mae', 'rmse', 'r2_score')
        }),
        ('Training Details', {
            'fields': ('train_test_split', 'training_samples', 'test_samples'),
            'classes': ('collapse',)
        }),
        ('Notes & Timestamps', {
            'fields': ('notes', 'evaluation_date'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Filter evaluations by current user's products."""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(product__owner=request.user)


# Customize admin site
admin.site.site_header = "Intelligent Inventory Management System"
admin.site.site_title = "Inventory Admin"
admin.site.index_title = "Welcome to Inventory Management"
