"""
URL routing for the inventory application.
"""

from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Authentication
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    
    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),
    
    # Products
    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('products/add/', views.ProductCreateView.as_view(), name='product_create'),
    path('products/<int:pk>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('products/<int:pk>/edit/', views.ProductUpdateView.as_view(), name='product_update'),
    path('products/<int:pk>/delete/', views.ProductDeleteView.as_view(), name='product_delete'),
    
    # Sales
    path('sales/entry/', views.SalesEntryView.as_view(), name='sales_entry'),
    path('sales/history/', views.SalesHistoryView.as_view(), name='sales_history'),
    
    # API endpoints for AJAX/dashboard updates
    path('api/product/<int:pk>/forecast/', views.ProductForecastAPIView.as_view(), name='api_forecast'),
    path('api/product/<int:pk>/alerts/', views.ProductAlertsAPIView.as_view(), name='api_alerts'),
]
