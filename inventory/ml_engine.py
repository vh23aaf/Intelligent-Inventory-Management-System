"""
ML Engine for demand forecasting and inventory decision-making.

This module provides:
1. Linear Regression Model - Simple baseline forecast
2. Random Forest Model - Advanced forecast with feature importance
3. Model Evaluation - MAE, RMSE, R² score calculation
4. Inventory Decision Logic - Reorder point and quantity calculations
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from datetime import timedelta
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class DemandForecaster:
    """
    Demand forecasting engine using multiple ML models.
    
    Features:
    - Trains on historical sales data
    - Generates predictions using Linear Regression and Random Forest
    - Evaluates model performance with MAE, RMSE, R²
    - Provides confidence scores
    """
    
    def __init__(self, product):
        """Initialize forecaster with a Product instance."""
        self.product = product
        self.lr_model = None
        self.rf_model = None
        self.scaler_mean = None
        self.scaler_std = None
        
    def prepare_data(self, days_lookback=90):
        """
        Prepare training data from historical sales.
        
        Args:
            days_lookback: Number of historical days to use for training
            
        Returns:
            X (feature array), y (target array), or None if insufficient data
        """
        from inventory.models import SalesRecord
        
        today = timezone.now().date()
        lookback_date = today - timedelta(days=days_lookback)
        
        # Get historical sales ordered by date
        sales = SalesRecord.objects.filter(
            product=self.product,
            sale_date__gte=lookback_date
        ).order_by('sale_date').values('sale_date', 'quantity_sold')
        
        if len(sales) < 7:  # Need at least 7 days for meaningful forecast
            logger.warning(f"Product {self.product.id} has insufficient sales data")
            return None, None
        
        # Convert to DataFrame
        df = pd.DataFrame(sales)
        df['sale_date'] = pd.to_datetime(df['sale_date'])
        
        # Fill missing dates with 0 sales
        date_range = pd.date_range(
            start=df['sale_date'].min(),
            end=df['sale_date'].max(),
            freq='D'
        )
        df = df.set_index('sale_date').reindex(date_range, fill_value=0).reset_index()
        df.columns = ['sale_date', 'quantity_sold']
        
        # Feature engineering
        df['day_of_week'] = df['sale_date'].dt.dayofweek
        df['day_of_month'] = df['sale_date'].dt.day
        df['week_of_year'] = df['sale_date'].dt.isocalendar().week
        
        # Rolling averages (lag features)
        df['ma_3days'] = df['quantity_sold'].rolling(window=3, min_periods=1).mean()
        df['ma_7days'] = df['quantity_sold'].rolling(window=7, min_periods=1).mean()
        
        # Shift-based features (previous day, week)
        df['prev_day_sales'] = df['quantity_sold'].shift(1).fillna(0)
        df['prev_week_sales'] = df['quantity_sold'].shift(7).fillna(0)
        
        # Drop rows with NaN in features
        feature_cols = ['day_of_week', 'day_of_month', 'week_of_year', 
                       'ma_3days', 'ma_7days', 'prev_day_sales', 'prev_week_sales']
        df = df.dropna(subset=feature_cols)
        
        if len(df) < 7:
            return None, None
        
        X = df[feature_cols].values.astype(np.float64)
        y = df['quantity_sold'].values.astype(np.float64)
        
        # Normalize features for better model performance
        self.scaler_mean = X.mean(axis=0)
        self.scaler_std = np.std(X, axis=0)
        # Add small epsilon to prevent division by zero
        self.scaler_std = np.where(self.scaler_std < 1e-8, 1.0, self.scaler_std)
        
        return X, y
    
    def train_models(self, days_lookback=90, test_size=0.2):
        """
        Train both Linear Regression and Random Forest models.
        
        Args:
            days_lookback: Historical days to use for training
            test_size: Proportion of data for testing (0.2 = 80/20 split)
            
        Returns:
            dict: Training metrics and model evaluation results
        """
        X, y = self.prepare_data(days_lookback)
        
        if X is None:
            logger.warning(f"Cannot train models for product {self.product.id}: insufficient data")
            return {'success': False, 'message': 'Insufficient sales data'}
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42
        )
        
        results = {}
        
        # --- Linear Regression Model ---
        try:
            self.lr_model = LinearRegression()
            self.lr_model.fit(X_train, y_train)
            
            y_pred_lr = self.lr_model.predict(X_test)
            y_pred_lr = np.maximum(y_pred_lr, 0)  # Ensure non-negative predictions
            
            results['linear_regression'] = {
                'mae': float(mean_absolute_error(y_test, y_pred_lr)),
                'rmse': float(np.sqrt(mean_squared_error(y_test, y_pred_lr))),
                'r2': float(r2_score(y_test, y_pred_lr)),
                'train_samples': len(X_train),
                'test_samples': len(X_test),
                'train_test_split': float(1 - test_size)
            }
        except Exception as e:
            logger.error(f"Linear Regression training failed: {str(e)}")
            results['linear_regression'] = {'error': str(e)}
        
        # --- Random Forest Model ---
        try:
            self.rf_model = RandomForestRegressor(
                n_estimators=50,
                max_depth=10,
                min_samples_split=5,
                random_state=42,
                n_jobs=-1
            )
            self.rf_model.fit(X_train, y_train)
            
            y_pred_rf = self.rf_model.predict(X_test)
            y_pred_rf = np.maximum(y_pred_rf, 0)  # Ensure non-negative predictions
            
            results['random_forest'] = {
                'mae': float(mean_absolute_error(y_test, y_pred_rf)),
                'rmse': float(np.sqrt(mean_squared_error(y_test, y_pred_rf))),
                'r2': float(r2_score(y_test, y_pred_rf)),
                'train_samples': len(X_train),
                'test_samples': len(X_test),
                'train_test_split': float(1 - test_size)
            }
        except Exception as e:
            logger.error(f"Random Forest training failed: {str(e)}")
            results['random_forest'] = {'error': str(e)}
        
        results['success'] = True
        return results
    
    def predict_demand(self, forecast_date):
        """
        Predict demand for a specific future date using both models.
        
        Args:
            forecast_date: Date to predict for (datetime.date)
            
        Returns:
            dict: Predictions from both models with confidence scores
        """
        # Prepare features for forecast date
        day_of_week = forecast_date.weekday()
        day_of_month = forecast_date.day
        week_of_year = forecast_date.isocalendar()[1]
        
        # Get recent sales for rolling averages
        today = timezone.now().date()
        lookback_date = today - timedelta(days=30)
        
        from inventory.models import SalesRecord
        recent_sales = list(SalesRecord.objects.filter(
            product=self.product,
            sale_date__gte=lookback_date
        ).order_by('-sale_date').values_list('quantity_sold', flat=True))
        
        if not recent_sales:
            # Fallback to simple average if no recent sales
            ma_3days = 0
            ma_7days = 0
            prev_day_sales = 0
            prev_week_sales = 0
        else:
            ma_3days = float(np.mean(recent_sales[:3])) if len(recent_sales) >= 3 else 0
            ma_7days = float(np.mean(recent_sales[:7])) if len(recent_sales) >= 7 else 0
            prev_day_sales = float(recent_sales[0])
            prev_week_sales = float(recent_sales[6]) if len(recent_sales) >= 7 else 0
        
        # Create feature vector
        features = np.array([[
            day_of_week,
            day_of_month,
            week_of_year,
            ma_3days,
            ma_7days,
            prev_day_sales,
            prev_week_sales
        ]])
        
        # Ensure models are trained
        if self.lr_model is None or self.rf_model is None:
            self.train_models()
        
        predictions = {}
        
        # Linear Regression prediction
        if self.lr_model is not None:
            lr_pred = float(max(0, self.lr_model.predict(features)[0]))
            predictions['linear_regression'] = lr_pred
        
        # Random Forest prediction
        if self.rf_model is not None:
            rf_pred = float(max(0, self.rf_model.predict(features)[0]))
            predictions['random_forest'] = rf_pred
        
        # Ensemble (average)
        if predictions:
            ensemble_pred = float(np.mean(list(predictions.values())))
            predictions['ensemble'] = ensemble_pred
        
        # Confidence score (higher R² = higher confidence)
        if self.rf_model is not None:
            # Use RF confidence as main confidence metric
            confidence = min(0.95, max(0.5, 0.5 + (0.45 * (self.rf_model.score(features, [1]) + 1) / 2)))
        else:
            confidence = 0.7
        
        predictions['confidence'] = float(confidence)
        
        return predictions


class InventoryOptimizer:
    """
    Inventory optimization logic for reorder points and quantities.
    
    Uses formulas:
    - Reorder Point = (Average Daily Demand × Lead Time) + Safety Stock
    - Economic Order Quantity (EOQ) = sqrt(2 × D × S / H)
      where D = annual demand, S = order cost, H = holding cost per unit
    """
    
    @staticmethod
    def calculate_reorder_point(product, daily_demand_forecast):
        """
        Calculate optimal reorder point.
        
        Formula: RP = (Average Daily Demand × Lead Time) + Safety Stock
        
        Args:
            product: Product instance
            daily_demand_forecast: Predicted daily demand (float)
            
        Returns:
            int: Optimal reorder point quantity
        """
        lead_time = product.lead_time_days
        safety_stock = product.safety_stock
        
        reorder_point = int((daily_demand_forecast * lead_time) + safety_stock)
        return max(1, reorder_point)  # Minimum 1 unit
    
    @staticmethod
    def calculate_economic_order_quantity(product, annual_demand, order_cost=50, holding_cost_per_unit=2):
        """
        Calculate Economic Order Quantity (EOQ).
        
        Formula: EOQ = sqrt(2 × D × S / H)
        - D: Annual demand (units)
        - S: Cost per order
        - H: Annual holding cost per unit
        
        Args:
            product: Product instance
            annual_demand: Predicted annual demand (units)
            order_cost: Fixed cost per order (default $50)
            holding_cost_per_unit: Annual holding cost per unit (default $2)
            
        Returns:
            int: Optimal order quantity
        """
        if annual_demand <= 0 or holding_cost_per_unit <= 0:
            return 10  # Default minimum order
        
        eoq = np.sqrt((2 * annual_demand * order_cost) / holding_cost_per_unit)
        return max(5, int(round(eoq)))
    
    @staticmethod
    def calculate_days_until_stockout(current_stock, daily_demand_forecast):
        """
        Calculate how many days until inventory runs out.
        
        Args:
            current_stock: Current stock level (units)
            daily_demand_forecast: Predicted daily demand (units/day)
            
        Returns:
            float: Days until stockout (or None if demand is 0)
        """
        if daily_demand_forecast <= 0:
            return float('inf')
        return float(current_stock) / float(daily_demand_forecast)
    
    @staticmethod
    def should_reorder(product, daily_demand_forecast):
        """
        Determine if product should be reordered immediately.
        
        Args:
            product: Product instance
            daily_demand_forecast: Predicted daily demand (float)
            
        Returns:
            bool: True if stock is at or below reorder point
        """
        reorder_point = InventoryOptimizer.calculate_reorder_point(product, daily_demand_forecast)
        return product.current_stock <= reorder_point
