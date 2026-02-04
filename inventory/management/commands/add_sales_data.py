"""
Management command to add more sales data for better ML model training.
"""

from django.core.management.base import BaseCommand
from inventory.models import Product, SalesRecord
from datetime import datetime, timedelta
import random


class Command(BaseCommand):
    help = 'Add additional sales records for better ML training'

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=300, help='Number of sales records to add')

    def handle(self, *args, **options):
        count = options['count']
        products = list(Product.objects.all())
        
        if not products:
            self.stdout.write(self.style.ERROR('No products found'))
            return
        
        base_date = datetime.now().date() - timedelta(days=180)
        created = 0
        
        for i in range(count):
            product = random.choice(products)
            sale_date = base_date + timedelta(days=random.randint(0, 180))
            
            # Vary quantities based on product category
            if product.name in ['USB-C Cable', 'Screen Protector', 'Notebook A4 (Pack)', 'Pen Set (50 pcs)']:
                quantity = random.randint(8, 30)
            elif product.name in ['Wireless Mouse', 'Phone Case', 'USB Hub', 'HDMI Cable']:
                quantity = random.randint(2, 12)
            else:
                quantity = random.randint(1, 8)
            
            # Try to create, skip if duplicate date exists
            _, created_flag = SalesRecord.objects.get_or_create(
                product=product,
                sale_date=sale_date,
                defaults={'quantity_sold': quantity}
            )
            
            if created_flag:
                created += 1
        
        self.stdout.write(self.style.SUCCESS(f'✓ Added {created} new sales records'))
        self.stdout.write(f'Total sales records now: {SalesRecord.objects.count()}')
