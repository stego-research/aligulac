from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.conf import settings

class Command(BaseCommand):
    help = 'Clears only the Aligulac-specific cache keys'

    def handle(self, *args, **options):
        # This will use the default cache backend which is configured with KEY_PREFIX
        # For RedisCache with a prefix, clear() only deletes keys starting with that prefix
        self.stdout.write('Clearing Aligulac cache...')
        try:
            cache.clear()
            self.stdout.write(self.style.SUCCESS(f'Successfully cleared Aligulac cache (Prefix: {settings.CACHES["default"].get("KEY_PREFIX", "None")})'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to clear cache: {str(e)}'))
