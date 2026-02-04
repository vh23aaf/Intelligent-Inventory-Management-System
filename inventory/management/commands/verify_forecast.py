from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Count
from datetime import timedelta

from inventory.models import Product, SalesRecord, DemandForecast
from inventory.ml_engine import DemandForecaster
from inventory.model_loader import best_model_loader


class Command(BaseCommand):
    help = 'Verify end-to-end forecasting for one product using the ML engine and saved model.'

    def add_arguments(self, parser):
        parser.add_argument('--product-id', type=int, help='ID of product to verify (optional)')

    def handle(self, *args, **options):
        self.stdout.write('Starting forecast verification...')

        # Show model loader status
        if best_model_loader.is_available():
            info = best_model_loader.get_model_info() or {}
            self.stdout.write(self.style.SUCCESS(f"Loaded pre-trained model: {info.get('name')} - MAE: {info.get('mae')}, R2: {info.get('r2')}"))
        else:
            self.stdout.write(self.style.WARNING('Pre-trained model not available; falling back to training per-product models.'))

        # Select product
        product = None
        if options.get('product_id'):
            try:
                product = Product.objects.get(id=options['product_id'])
            except Product.DoesNotExist:
                self.stdout.write(self.style.ERROR('Product with that id not found'))
                return

        if not product:
            # choose a product with at least 7 sales records
            product = Product.objects.annotate(sales_count=Count('sales_records')).filter(sales_count__gte=7).first()

        if not product:
            self.stdout.write(self.style.ERROR('No product with sufficient sales history (>=7) found. Please generate sales data.'))
            return

        self.stdout.write(f"Selected product: {product.id} - {product.name} (stock: {product.current_stock})")

        forecaster = DemandForecaster(product)

        # Train local models if needed and show evaluation
        metrics = forecaster.train_models()
        if not metrics.get('success'):
            self.stdout.write(self.style.WARNING('Per-product model training incomplete or insufficient data.'))
        else:
            self.stdout.write(self.style.SUCCESS('Trained per-product models. Metrics:'))
            for k, v in metrics.items():
                if k in ('linear_regression', 'random_forest') and isinstance(v, dict):
                    self.stdout.write(f" - {k}: MAE={v.get('mae')}, RMSE={v.get('rmse')}, R2={v.get('r2')}")

        # Generate 7-day forecasts and save DemandForecast rows
        today = timezone.now().date()
        saved = 0
        for d in range(1, 8):
            target = today + timedelta(days=d)
            preds = forecaster.predict_demand(target)
            # prefer ensemble if available
            pred_value = preds.get('ensemble') or preds.get('linear_regression') or preds.get('random_forest') or 0.0
            confidence = preds.get('confidence', 0.5)

            # Save as DemandForecast (ensemble)
            obj, created = DemandForecast.objects.update_or_create(
                product=product,
                forecast_date=target,
                model_used='ensemble',
                defaults={
                    'predicted_demand': float(pred_value),
                    'confidence_score': float(confidence),
                    'mae': metrics.get('linear_regression', {}).get('mae') if metrics.get('linear_regression') else None,
                    'rmse': metrics.get('linear_regression', {}).get('rmse') if metrics.get('linear_regression') else None,
                }
            )
            if created:
                saved += 1

            self.stdout.write(f"{target}: predicted={pred_value:.2f}, confidence={confidence:.2f}")

        self.stdout.write(self.style.SUCCESS(f"Saved {saved} new DemandForecast rows for product {product.id}"))
