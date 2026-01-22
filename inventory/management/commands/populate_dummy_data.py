"""
Management command to populate dummy data for testing.
Creates realistic products, sales records, and inventory alerts.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from inventory.models import Product, SalesRecord, InventoryAlert
from datetime import datetime, timedelta
import random

class Command(BaseCommand):
    help = 'Populate database with dummy data for testing'

    def add_arguments(self, parser):
        parser.add_argument('--user', type=str, default='admin', help='Username to associate products with')
        parser.add_argument('--clear', action='store_true', help='Clear existing data before adding new data')

    def handle(self, *args, **options):
        username = options['user']
        
        # Get or create user
        try:
            user = User.objects.get(username=username)
            self.stdout.write(self.style.SUCCESS(f'Using existing user: {username}'))
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User {username} does not exist'))
            return

        # Clear existing data if requested
        if options['clear']:
            Product.objects.filter(owner=user).delete()
            InventoryAlert.objects.filter(product__owner=user).delete()
            self.stdout.write(self.style.WARNING('Cleared existing products, sales, and alerts'))

        # Sample products with realistic data
        products_data = [
            {'name': 'Wireless Mouse', 'category': 'Electronics', 'sku': 'WM-001', 'price': 24.99, 'stock': 150, 'lead_time': 7, 'safety_stock': 20},
            {'name': 'USB-C Cable', 'category': 'Electronics', 'sku': 'UC-001', 'price': 12.99, 'stock': 300, 'lead_time': 5, 'safety_stock': 50},
            {'name': 'Mechanical Keyboard', 'category': 'Electronics', 'sku': 'MK-001', 'price': 89.99, 'stock': 45, 'lead_time': 10, 'safety_stock': 10},
            {'name': 'Monitor Stand', 'category': 'Office Supplies', 'sku': 'MS-001', 'price': 34.99, 'stock': 80, 'lead_time': 7, 'safety_stock': 15},
            {'name': 'Desk Lamp', 'category': 'Office Supplies', 'sku': 'DL-001', 'price': 44.99, 'stock': 60, 'lead_time': 7, 'safety_stock': 10},
            {'name': 'Webcam HD', 'category': 'Electronics', 'sku': 'WC-001', 'price': 59.99, 'stock': 35, 'lead_time': 7, 'safety_stock': 8},
            {'name': 'Notebook A4 (Pack)', 'category': 'Office Supplies', 'sku': 'NB-001', 'price': 8.99, 'stock': 250, 'lead_time': 3, 'safety_stock': 50},
            {'name': 'Pen Set (50 pcs)', 'category': 'Office Supplies', 'sku': 'PS-001', 'price': 15.99, 'stock': 180, 'lead_time': 3, 'safety_stock': 30},
            {'name': 'Wireless Headphones', 'category': 'Electronics', 'sku': 'WH-001', 'price': 79.99, 'stock': 28, 'lead_time': 7, 'safety_stock': 5},
            {'name': 'USB Hub', 'category': 'Electronics', 'sku': 'UH-001', 'price': 29.99, 'stock': 95, 'lead_time': 5, 'safety_stock': 20},
            {'name': 'Screen Protector', 'category': 'Electronics', 'sku': 'SP-001', 'price': 9.99, 'stock': 400, 'lead_time': 3, 'safety_stock': 100},
            {'name': 'Phone Case', 'category': 'Electronics', 'sku': 'PC-001', 'price': 19.99, 'stock': 200, 'lead_time': 5, 'safety_stock': 40},
            {'name': 'Portable Charger', 'category': 'Electronics', 'sku': 'PC-002', 'price': 34.99, 'stock': 70, 'lead_time': 7, 'safety_stock': 12},
            {'name': 'Mouse Pad', 'category': 'Office Supplies', 'sku': 'MP-001', 'price': 14.99, 'stock': 120, 'lead_time': 4, 'safety_stock': 25},
            {'name': 'HDMI Cable', 'category': 'Electronics', 'sku': 'HC-001', 'price': 11.99, 'stock': 180, 'lead_time': 5, 'safety_stock': 30},
        ]

        # Create products
        created_products = []
        for prod_data in products_data:
            product, created = Product.objects.get_or_create(
                owner=user,
                sku=prod_data['sku'],
                defaults={
                    'name': prod_data['name'],
                    'category': prod_data['category'],
                    'price': prod_data['price'],
                    'current_stock': prod_data['stock'],
                    'lead_time_days': prod_data['lead_time'],
                    'safety_stock': prod_data['safety_stock'],
                    'reorder_point': prod_data['safety_stock'] + (prod_data['lead_time'] * 5),
                }
            )
            created_products.append(product)
            if created:
                self.stdout.write(self.style.SUCCESS(f'✓ Created product: {product.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'→ Product already exists: {product.name}'))

        # Generate 100 sales records
        self.stdout.write(self.style.MIGRATE_HEADING('Generating 100 sales records...'))
        
        # Generate sales for past 90 days
        base_date = datetime.now().date() - timedelta(days=90)
        sales_count = 0

        for i in range(100):
            # Distribute sales across the 90-day period
            days_offset = random.randint(0, 89)
            sale_date = base_date + timedelta(days=days_offset)
            
            # Randomly select a product
            product = random.choice(created_products)
            
            # Generate realistic quantity (1-25 units, with some products selling more)
            base_quantity = random.randint(1, 15)
            if product.name in ['USB-C Cable', 'Screen Protector', 'Notebook A4 (Pack)', 'Pen Set (50 pcs)']:
                # High-volume items
                quantity = random.randint(5, 25)
            elif product.name in ['Wireless Mouse', 'Phone Case', 'USB Hub']:
                # Medium-volume items
                quantity = random.randint(2, 15)
            else:
                # Low-volume items
                quantity = random.randint(1, 8)

            # Create sales record if it doesn't already exist
            sales_record, created = SalesRecord.objects.get_or_create(
                product=product,
                sale_date=sale_date,
                defaults={'quantity_sold': quantity}
            )
            
            if created:
                sales_count += 1

        self.stdout.write(self.style.SUCCESS(f'✓ Created {sales_count} sales records'))

        # Generate high-risk alerts
        self.stdout.write(self.style.MIGRATE_HEADING('Generating high-risk inventory alerts...'))
        
        alert_configs = [
            {
                'sku': 'WH-001',
                'name': 'Wireless Headphones',
                'alert_type': 'understock',
                'risk_level': 'high',
                'explanation': 'Stock level (28) is critically low. Average daily sales: 3 units. Only 9 days of inventory remaining.',
                'forecasted_demand': 21
            },
            {
                'sku': 'WC-001',
                'name': 'Webcam HD',
                'alert_type': 'understock',
                'risk_level': 'high',
                'explanation': 'Critical inventory shortage. Current stock (35) below minimum threshold (40). Recommend immediate reorder.',
                'forecasted_demand': 18
            },
            {
                'sku': 'SP-001',
                'name': 'Screen Protector',
                'alert_type': 'overstock',
                'risk_level': 'high',
                'explanation': 'Excess inventory detected. Current stock (400) is 4x the recommended level. Consider promotional discount.',
                'forecasted_demand': 80
            },
            {
                'sku': 'PC-002',
                'name': 'Portable Charger',
                'alert_type': 'understock',
                'risk_level': 'high',
                'explanation': 'Stock depletion risk. Trending sales exceed current inventory. Lead time: 7 days. Reorder urgently.',
                'forecasted_demand': 28
            },
            {
                'sku': 'PS-001',
                'name': 'Pen Set (50 pcs)',
                'alert_type': 'overstock',
                'risk_level': 'high',
                'explanation': 'Warehousing cost concern. Stock (180) exceeds 6 months demand forecast. Recommend inventory clearance.',
                'forecasted_demand': 25
            },
        ]

        alerts_created = 0
        for config in alert_configs:
            try:
                product = Product.objects.get(owner=user, sku=config['sku'])
                alert, created = InventoryAlert.objects.get_or_create(
                    product=product,
                    alert_type=config['alert_type'],
                    defaults={
                        'risk_level': config['risk_level'],
                        'explanation': config['explanation'],
                        'forecasted_demand_7d': config['forecasted_demand'],
                        'current_stock': product.current_stock,
                        'acknowledged': False
                    }
                )
                if created:
                    alerts_created += 1
                    self.stdout.write(self.style.SUCCESS(f'✓ Created {config["alert_type"]} alert for {config["name"]}'))
                else:
                    self.stdout.write(self.style.WARNING(f'→ Alert already exists for {config["name"]}'))
            except Product.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'✗ Product {config["name"]} not found'))

        self.stdout.write(self.style.SUCCESS(f'✓ Created {alerts_created} inventory alerts'))
        self.stdout.write(self.style.SUCCESS('\n✅ Dummy data populated successfully!'))
        self.stdout.write(self.style.WARNING('\nSummary:'))
        self.stdout.write(f'  - Products: {len(created_products)}')
        self.stdout.write(f'  - Sales Records: {sales_count}')
        self.stdout.write(f'  - High-Risk Alerts: {alerts_created}')
        self.stdout.write(f'  - User: {user.username}')
