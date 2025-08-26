from django.core.management.base import BaseCommand
from extractor.models import Vendor

class Command(BaseCommand):
    help = 'Initialize default vendors based on config files'

    def handle(self, *args, **options):
        vendors = [
            ('JSW Steel', 'JSW'),
            ('CITIC Steel', 'CITIC'),
            ('POSCO Steel', 'POSCO'),
            ('Iraeta Steel', 'IRAETA'),
            ('Hengrun Steel', 'HENGRUN'),
        ]

        for display_name, short_name in vendors:
            vendor, created = Vendor.objects.get_or_create(
                name=display_name
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created vendor: {display_name} ({short_name})'))
            else:
                self.stdout.write(f'Vendor already exists: {display_name} ({short_name})')

        self.stdout.write(self.style.SUCCESS('Vendor initialization completed'))
