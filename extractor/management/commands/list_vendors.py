from django.core.management.base import BaseCommand
from extractor.models import Vendor

class Command(BaseCommand):
    help = 'Lists all vendors in the database'

    def handle(self, *args, **options):
        vendors = Vendor.objects.all()
        if not vendors:
            self.stdout.write(self.style.WARNING('No vendors found in the database'))
            return

        self.stdout.write(self.style.SUCCESS('Current vendors:'))
        for vendor in vendors:
            self.stdout.write(f'- ID: {vendor.id}, Name: {vendor.name}')
