"""
Database models for the Intelligent Inventory Management System.

Models:
- Product: Represents inventory items (name, category, price, stock, lead time)
- SalesRecord: Daily sales entries (product, quantity sold, date)
- DemandForecast: ML-generated predictions (product, forecast date, predicted demand)
- InventoryAlert: Risk indicators (overstock/understock detection with explanations)
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from datetime import timedelta
from django.utils import timezone


class Product(models.Model):
    """
    Product model representing individual inventory items.
    
    Fields:
    - owner: User who owns/manages this product
    - name: Product name
    - category: Product category for grouping
    - price: Unit price in currency
    - current_stock: Current inventory level
    - lead_time_days: Days between order and receipt
    - reorder_point: Minimum stock before reordering (auto-calculated or manual)
    - safety_stock: Buffer stock for demand variability
    - created_at: Timestamp of creation
    - updated_at: Timestamp of last update
    """
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=100, blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    current_stock = models.PositiveIntegerField(default=0)
    lead_time_days = models.PositiveIntegerField(default=7, help_text="Days between order placement and receipt")
    reorder_point = models.PositiveIntegerField(default=0, help_text="Minimum stock level to trigger reorder")
    safety_stock = models.PositiveIntegerField(default=0, help_text="Buffer stock for demand variability")
    sku = models.CharField(max_length=50, unique=True, null=True, blank=True, help_text="Stock Keeping Unit")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['owner', '-updated_at']),
            models.Index(fields=['current_stock']),
        ]
    
    def __str__(self):
        return f"{self.name} (Stock: {self.current_stock})"
    
    def get_reorder_recommendation(self):
        """
        Returns True if product should be reordered based on current stock vs reorder point.
        """
        return self.current_stock <= self.reorder_point


class SalesRecord(models.Model):
    """
    Daily sales transaction record.
    
    Fields:
    - product: Foreign key to Product
    - quantity_sold: Units sold on this date
    - sale_date: Date of the sale
    - revenue: Calculated field (quantity × product price)
    - created_at: When this record was entered into system
    
    Purpose: Feed historical sales data to ML models for demand forecasting.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='sales_records')
    quantity_sold = models.PositiveIntegerField(validators=[MinValueValidator(0)])
    sale_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-sale_date']
        indexes = [
            models.Index(fields=['product', 'sale_date']),
            models.Index(fields=['sale_date']),
        ]
        unique_together = ['product', 'sale_date']
    
    def __str__(self):
        return f"{self.product.name} - {self.quantity_sold} units on {self.sale_date}"
    
    @property
    def revenue(self):
        """Calculate revenue from this sale."""
        return self.quantity_sold * self.product.price


class DemandForecast(models.Model):
    """
    ML-generated demand predictions.
    
    Fields:
    - product: Foreign key to Product
    - forecast_date: Date being predicted
    - predicted_demand: ML model output (units)
    - model_used: Which model generated this ('linear_regression' or 'random_forest')
    - mae: Mean Absolute Error for this product's model
    - rmse: Root Mean Squared Error for this product's model
    - confidence_score: 0-1 score indicating prediction reliability
    - created_at: When forecast was generated
    
    Purpose: Store historical forecasts for dashboard display and model evaluation.
    """
    MODEL_CHOICES = [
        ('linear_regression', 'Linear Regression'),
        ('random_forest', 'Random Forest'),
        ('ensemble', 'Ensemble'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='demand_forecasts')
    forecast_date = models.DateField()
    predicted_demand = models.FloatField(validators=[MinValueValidator(0)])
    model_used = models.CharField(max_length=20, choices=MODEL_CHOICES, default='random_forest')
    mae = models.FloatField(null=True, blank=True, help_text="Mean Absolute Error for model evaluation")
    rmse = models.FloatField(null=True, blank=True, help_text="Root Mean Squared Error for model evaluation")
    confidence_score = models.FloatField(default=0.5, validators=[MinValueValidator(0), MinValueValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-forecast_date']
        indexes = [
            models.Index(fields=['product', 'forecast_date']),
            models.Index(fields=['forecast_date']),
        ]
        unique_together = ['product', 'forecast_date', 'model_used']
    
    def __str__(self):
        return f"{self.product.name} - {self.predicted_demand:.1f} units on {self.forecast_date} ({self.model_used})"


class InventoryAlert(models.Model):
    """
    Risk detection and inventory alerts.
    
    Fields:
    - product: Foreign key to Product
    - alert_type: 'understock' or 'overstock'
    - risk_level: 'low', 'medium', or 'high'
    - explanation: Natural language explanation of the risk
    - forecasted_demand_7d: Predicted demand for next 7 days
    - current_stock: Stock level when alert was generated
    - generated_at: When this alert was created
    - acknowledged: Whether user has seen/acknowledged this alert
    
    Purpose: Present explainable risk indicators on the dashboard.
    """
    ALERT_TYPE_CHOICES = [
        ('understock', 'Understock Risk'),
        ('overstock', 'Overstock Risk'),
    ]
    
    RISK_LEVEL_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='alerts')
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPE_CHOICES)
    risk_level = models.CharField(max_length=20, choices=RISK_LEVEL_CHOICES)
    explanation = models.TextField(help_text="Natural language explanation of the risk")
    forecasted_demand_7d = models.FloatField(help_text="7-day forecasted demand")
    current_stock = models.PositiveIntegerField(help_text="Stock level when alert generated")
    generated_at = models.DateTimeField(auto_now_add=True)
    acknowledged = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-risk_level', '-generated_at']
        indexes = [
            models.Index(fields=['product', '-generated_at']),
            models.Index(fields=['alert_type', 'risk_level']),
        ]
    
    def __str__(self):
        return f"{self.product.name} - {self.alert_type} ({self.risk_level})"
    
    @property
    def is_recent(self):
        """Check if alert was generated within last 24 hours."""
        return timezone.now() - self.generated_at < timedelta(hours=24)


class ModelEvaluation(models.Model):
    """
    Store model evaluation metrics for academic documentation.
    
    Fields:
    - product: Product for which model was evaluated
    - model_name: 'linear_regression' or 'random_forest'
    - mae: Mean Absolute Error
    - rmse: Root Mean Squared Error
    - r2_score: R-squared score (model fit quality)
    - train_test_split: Train/test split ratio used
    - evaluation_date: When evaluation was performed
    - training_samples: Number of samples used in training
    - test_samples: Number of samples used in testing
    
    Purpose: Track model performance over time for academic report and model selection.
    """
    MODEL_CHOICES = [
        ('linear_regression', 'Linear Regression'),
        ('random_forest', 'Random Forest'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='model_evaluations')
    model_name = models.CharField(max_length=50, choices=MODEL_CHOICES)
    mae = models.FloatField()
    rmse = models.FloatField()
    r2_score = models.FloatField()
    train_test_split = models.FloatField(default=0.8, help_text="Proportion used for training (e.g., 0.8 = 80/20)")
    training_samples = models.PositiveIntegerField()
    test_samples = models.PositiveIntegerField()
    evaluation_date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, help_text="Additional notes about evaluation")
    
    class Meta:
        ordering = ['-evaluation_date']
        indexes = [
            models.Index(fields=['product', 'model_name']),
        ]
    
    def __str__(self):
        return f"{self.product.name} - {self.model_name} (MAE: {self.mae:.2f}, RMSE: {self.rmse:.2f})"
