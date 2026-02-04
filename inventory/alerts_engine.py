"""
Alerts Engine for intelligent inventory risk detection.

Provides:
1. Risk Detection - Identifies understock and overstock situations
2. Natural Language Explanations - Generates explainable alert messages
3. Risk Level Assessment - Categorizes risk as Low, Medium, or High
4. Actionable Recommendations - Suggests next steps for each alert
"""

import logging
from datetime import timedelta
from django.utils import timezone
from decimal import Decimal

logger = logging.getLogger(__name__)


class AlertsEngine:
    """
    Intelligent alerts system with natural language explanations.
    
    Alert Types:
    - UNDERSTOCK: Inventory too low, risk of stockout
    - OVERSTOCK: Inventory too high, excess holding costs
    
    Risk Levels:
    - LOW: Monitor but no immediate action needed
    - MEDIUM: Should monitor closely, plan action
    - HIGH: Requires urgent attention and action
    """
    
    RISK_THRESHOLDS = {
        'understock': {
            'high': 0.5,      # Stock is 50% or less of 7-day forecast
            'medium': 0.75,   # Stock is 75% or less of 7-day forecast
        },
        'overstock': {
            'high': 6.0,      # Stock is 6x or more than 7-day forecast
            'medium': 4.0,    # Stock is 4x or more than 7-day forecast
        }
    }
    
    @staticmethod
    def detect_alerts(product, daily_demand_forecast, forecast_7days):
        """
        Detect and create alerts for inventory risks.
        
        Args:
            product: Product instance
            daily_demand_forecast: Predicted daily demand (float)
            forecast_7days: Sum of predicted demand for next 7 days (float)
            
        Returns:
            list: Alert data dictionaries with type, risk_level, and explanation
        """
        alerts = []
        current_stock = product.current_stock
        
        # --- Understock Risk Detection ---
        if current_stock < forecast_7days:
            risk_ratio = float(current_stock) / float(forecast_7days) if forecast_7days > 0 else 0
            
            if risk_ratio <= AlertsEngine.RISK_THRESHOLDS['understock']['high']:
                risk_level = 'high'
            elif risk_ratio <= AlertsEngine.RISK_THRESHOLDS['understock']['medium']:
                risk_level = 'medium'
            else:
                risk_level = 'low'
            
            alert = {
                'alert_type': 'understock',
                'risk_level': risk_level,
                'forecasted_demand_7d': float(forecast_7days),
                'explanation': AlertsEngine.generate_understock_explanation(
                    product, current_stock, daily_demand_forecast, forecast_7days, risk_level
                )
            }
            alerts.append(alert)
        
        # --- Overstock Risk Detection ---
        if current_stock > (forecast_7days * AlertsEngine.RISK_THRESHOLDS['overstock']['medium']):
            if current_stock >= (forecast_7days * AlertsEngine.RISK_THRESHOLDS['overstock']['high']):
                risk_level = 'high'
            else:
                risk_level = 'medium'
            
            alert = {
                'alert_type': 'overstock',
                'risk_level': risk_level,
                'forecasted_demand_7d': float(forecast_7days),
                'explanation': AlertsEngine.generate_overstock_explanation(
                    product, current_stock, daily_demand_forecast, forecast_7days, risk_level
                )
            }
            alerts.append(alert)
        
        return alerts
    
    @staticmethod
    def generate_understock_explanation(product, current_stock, daily_demand, forecast_7days, risk_level):
        """
        Generate natural language explanation for understock alert.
        
        Args:
            product: Product instance
            current_stock: Current stock quantity (int)
            daily_demand: Predicted daily demand (float)
            forecast_7days: Forecasted demand for next 7 days (float)
            risk_level: 'low', 'medium', or 'high' (str)
            
        Returns:
            str: Detailed explanation message
        """
        days_until_stockout = float(current_stock) / (daily_demand + 0.1)  # Avoid division by zero
        
        base_msg = f"Stock level ({current_stock} units) is low. "
        
        if risk_level == 'high':
            verb = "CRITICAL"
            action = "URGENT REORDER REQUIRED"
            msg = (
                f"{verb} inventory shortage detected for {product.name}. "
                f"Current stock ({current_stock} units) will be depleted in approximately "
                f"{int(days_until_stockout)} days at current demand levels "
                f"(forecast: {float(forecast_7days):.1f} units/week). "
                f"Lead time is {product.lead_time_days} days. "
                f"⚠️ {action} to prevent stockout."
            )
        elif risk_level == 'medium':
            msg = (
                f"Moderate understock risk for {product.name}. "
                f"Current inventory ({current_stock} units) covers approximately "
                f"{float(forecast_7days):.0f} units of weekly demand (forecast). "
                f"With a {product.lead_time_days}-day lead time, consider placing "
                f"an order soon to maintain service levels."
            )
        else:  # low
            msg = (
                f"Low inventory detected for {product.name}. "
                f"Current stock ({current_stock} units) is approaching recommended levels. "
                f"Monitor closely and prepare to reorder if sales trend continues."
            )
        
        return msg
    
    @staticmethod
    def generate_overstock_explanation(product, current_stock, daily_demand, forecast_7days, risk_level):
        """
        Generate natural language explanation for overstock alert.
        
        Args:
            product: Product instance
            current_stock: Current stock quantity (int)
            daily_demand: Predicted daily demand (float)
            forecast_7days: Forecasted demand for next 7 days (float)
            risk_level: 'low', 'medium', or 'high' (str)
            
        Returns:
            str: Detailed explanation message
        """
        coverage_days = float(current_stock) / (daily_demand + 0.1) if daily_demand > 0 else 999
        excess_ratio = float(current_stock) / (forecast_7days + 0.1) if forecast_7days > 0 else 1
        
        if risk_level == 'high':
            verb = "CRITICAL"
            action = "IMMEDIATE ACTION NEEDED"
            msg = (
                f"{verb} excess inventory for {product.name}. "
                f"Current stock ({current_stock} units) exceeds 6 months of forecasted demand. "
                f"Holding cost is building up. "
                f"⚠️ {action}: Consider promotional discounts, bundling offers, "
                f"or adjusting future orders to clear excess inventory."
            )
        elif risk_level == 'medium':
            msg = (
                f"Excess inventory detected for {product.name}. "
                f"Current stock ({current_stock} units) is {excess_ratio:.1f}x the weekly forecast. "
                f"Stock covers {int(coverage_days)} days of expected sales. "
                f"Consider reducing incoming orders to optimize warehouse space and reduce holding costs."
            )
        else:  # low (shouldn't normally reach here)
            msg = (
                f"Higher-than-average inventory for {product.name}. "
                f"Current stock ({current_stock} units) is {excess_ratio:.1f}x the weekly forecast. "
                f"Monitor and adjust ordering if pattern continues."
            )
        
        return msg
    
    @staticmethod
    def generate_reorder_recommendation(product, daily_demand_forecast, eoq):
        """
        Generate actionable reorder recommendation.
        
        Args:
            product: Product instance
            daily_demand_forecast: Predicted daily demand (float)
            eoq: Economic Order Quantity (int)
            
        Returns:
            str: Recommendation message
        """
        reorder_point = int((daily_demand_forecast * product.lead_time_days) + product.safety_stock)
        
        return (
            f"For {product.name}: "
            f"Reorder when stock reaches {reorder_point} units. "
            f"Recommended order quantity: {eoq} units. "
            f"This balances ordering frequency against holding costs."
        )
    
    @staticmethod
    def get_alert_summary(alerts):
        """
        Generate a summary of all active alerts.
        
        Args:
            alerts: List of alert dictionaries
            
        Returns:
            str: Summary text
        """
        if not alerts:
            return "✓ No inventory alerts. All products are in good standing."
        
        understock_count = sum(1 for a in alerts if a['alert_type'] == 'understock')
        overstock_count = sum(1 for a in alerts if a['alert_type'] == 'overstock')
        high_risk_count = sum(1 for a in alerts if a['risk_level'] == 'high')
        
        summary = f"Active Alerts: {len(alerts)} total\n"
        if understock_count > 0:
            summary += f"  • {understock_count} understock alert(s)\n"
        if overstock_count > 0:
            summary += f"  • {overstock_count} overstock alert(s)\n"
        if high_risk_count > 0:
            summary += f"  ⚠️ {high_risk_count} HIGH RISK alert(s) requiring immediate attention"
        
        return summary


class DemandAnalyzer:
    """
    Analyze demand patterns and provide insights.
    """
    
    @staticmethod
    def analyze_trend(product, days_lookback=30):
        """
        Analyze sales trend (increasing, decreasing, stable).
        
        Args:
            product: Product instance
            days_lookback: Historical days to analyze (int)
            
        Returns:
            dict: Trend analysis with direction, rate, and forecast
        """
        from inventory.models import SalesRecord
        
        today = timezone.now().date()
        lookback_date = today - timedelta(days=days_lookback)
        
        sales = SalesRecord.objects.filter(
            product=product,
            sale_date__gte=lookback_date
        ).order_by('sale_date').values_list('quantity_sold', flat=True)
        
        if len(sales) < 7:
            return {'trend': 'insufficient_data', 'message': 'Not enough sales history'}
        
        sales_list = list(sales)
        
        # Split into two halves and compare
        mid = len(sales_list) // 2
        first_half_avg = sum(sales_list[:mid]) / len(sales_list[:mid])
        second_half_avg = sum(sales_list[mid:]) / len(sales_list[mid:])
        
        if second_half_avg > first_half_avg * 1.1:
            trend = 'increasing'
            rate = ((second_half_avg - first_half_avg) / first_half_avg) * 100
        elif second_half_avg < first_half_avg * 0.9:
            trend = 'decreasing'
            rate = ((first_half_avg - second_half_avg) / first_half_avg) * 100
        else:
            trend = 'stable'
            rate = 0
        
        return {
            'trend': trend,
            'rate_pct': float(rate),
            'first_period_avg': float(first_half_avg),
            'second_period_avg': float(second_half_avg),
            'latest_average': sum(sales_list[-7:]) / 7 if len(sales_list) >= 7 else float(sales_list[-1])
        }
