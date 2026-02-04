from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from inventory.models import Product, DemandForecast, SalesRecord, ModelEvaluation, InventoryAlert
from inventory.ml_engine import DemandForecaster, InventoryOptimizer
from inventory.alerts_engine import AlertsEngine, DemandAnalyzer
from django.db.models import Sum
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Generate demand forecasts for all products using ML models (Linear Regression + Random Forest)'

    def add_arguments(self, parser):
        parser.add_argument('--product_id', type=int, help='Generate forecasts only for a specific product ID')
        parser.add_argument('--days', type=int, default=14, help='Number of days to forecast (default: 14)')
        parser.add_argument('--clear', action='store_true', help='Clear existing forecasts before generating new ones')

    def handle(self, *args, **options):
        # Get products
        if options['product_id']:
            products = Product.objects.filter(id=options['product_id'])
            if not products.exists():
                self.stdout.write(self.style.ERROR(f'Product with ID {options["product_id"]} not found'))
                return
        else:
            products = Product.objects.all()
        
        if not products.exists():
            self.stdout.write(self.style.ERROR('No products found in the database'))
            return

        # Clear existing forecasts if requested
        if options['clear']:
            DemandForecast.objects.all().delete()
            self.stdout.write(self.style.WARNING('Cleared existing forecasts'))

        today = timezone.now().date()
        forecast_days = options['days']
        forecasts_created = 0
        alerts_created = 0
        models_trained = 0

        self.stdout.write(self.style.MIGRATE_HEADING('Generating ML-based demand forecasts...'))

        for product in products:
            try:
                # Initialize forecaster
                forecaster = DemandForecaster(product)
                
                # Train both models
                self.stdout.write(f'  Training models for {product.name}...')
                training_results = forecaster.train_models(days_lookback=90, test_size=0.2)
                
                if training_results.get('success'):
                    models_trained += 1
                    
                    # Store model evaluation metrics
                    for model_name, metrics in training_results.items():
                        if model_name != 'success' and 'error' not in metrics:
                            ModelEvaluation.objects.update_or_create(
                                product=product,
                                model_name=model_name,
                                defaults={
                                    'mae': metrics['mae'],
                                    'rmse': metrics['rmse'],
                                    'r2_score': metrics['r2'],
                                    'train_test_split': metrics['train_test_split'],
                                    'training_samples': metrics['train_samples'],
                                    'test_samples': metrics['test_samples'],
                                    'notes': f'Auto-trained on {metrics["train_samples"]} samples'
                                }
                            )
                    
                    # Generate forecasts for next N days
                    for day in range(1, forecast_days + 1):
                        forecast_date = today + timedelta(days=day)
                        
                        # Get predictions from both models
                        predictions = forecaster.predict_demand(forecast_date)
                        
                        # Create forecasts for each model
                        for model_name in ['linear_regression', 'random_forest', 'ensemble']:
                            if model_name in predictions:
                                predicted_demand = predictions[model_name]
                                confidence_score = predictions.get('confidence', 0.75)
                                
                                # Get evaluation metrics for this model
                                try:
                                    eval_metrics = ModelEvaluation.objects.get(
                                        product=product,
                                        model_name=model_name
                                    )
                                    mae = eval_metrics.mae
                                    rmse = eval_metrics.rmse
                                except ModelEvaluation.DoesNotExist:
                                    mae = None
                                    rmse = None
                                
                                # Create or update forecast
                                DemandForecast.objects.update_or_create(
                                    product=product,
                                    forecast_date=forecast_date,
                                    model_used=model_name,
                                    defaults={
                                        'predicted_demand': float(predicted_demand),
                                        'mae': mae,
                                        'rmse': rmse,
                                        'confidence_score': float(confidence_score)
                                    }
                                )
                                forecasts_created += 1
                    
                    self.stdout.write(self.style.SUCCESS(f'  ✓ Generated forecasts for {product.name}'))
                
                else:
                    self.stdout.write(self.style.WARNING(
                        f'  → Skipped {product.name}: Insufficient sales data for training'
                    ))
            
            except Exception as e:
                logger.error(f'Error processing product {product.name}: {str(e)}')
                self.stdout.write(self.style.ERROR(f'  ✗ Error processing {product.name}: {str(e)}'))

        # Generate/update alerts
        self.stdout.write(self.style.MIGRATE_HEADING('Generating inventory alerts...'))
        for product in products:
            try:
                # Get 7-day forecast
                next_7_days = DemandForecast.objects.filter(
                    product=product,
                    forecast_date__gte=today,
                    forecast_date__lt=today + timedelta(days=7),
                    model_used='ensemble'
                ).aggregate(total=Sum('predicted_demand'))
                
                forecast_7days = next_7_days.get('total') or 0
                
                # Get average daily forecast
                forecasts = DemandForecast.objects.filter(
                    product=product,
                    forecast_date__gte=today,
                    model_used='ensemble'
                )[:14]
                
                daily_demand_avg = sum(f.predicted_demand for f in forecasts) / len(forecasts) if forecasts else 5
                
                # Detect alerts
                alerts = AlertsEngine.detect_alerts(product, daily_demand_avg, forecast_7days)
                
                # Create alert records
                for alert in alerts:
                    InventoryAlert.objects.update_or_create(
                        product=product,
                        alert_type=alert['alert_type'],
                        defaults={
                            'risk_level': alert['risk_level'],
                            'explanation': alert['explanation'],
                            'forecasted_demand_7d': alert['forecasted_demand_7d'],
                            'current_stock': product.current_stock,
                            'acknowledged': False
                        }
                    )
                    if alerts:
                        alerts_created += 1
            
            except Exception as e:
                logger.error(f'Error creating alerts for {product.name}: {str(e)}')

        # Summary
        self.stdout.write(self.style.SUCCESS('\n✅ Forecast generation complete!'))
        self.stdout.write(self.style.WARNING(f'\nSummary:'))
        self.stdout.write(f'  - Products processed: {products.count()}')
        self.stdout.write(f'  - ML models trained: {models_trained}')
        self.stdout.write(f'  - Forecasts created: {forecasts_created}')
        self.stdout.write(f'  - Alerts generated: {alerts_created}')
