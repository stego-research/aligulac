from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.conf import settings

class Command(BaseCommand):
    help = 'Clears only view-cached pages, preserving sessions and other data'

    def handle(self, *args, **options):
        self.stdout.write('Surgically clearing Aligulac view cache...')
        try:
            # django-redis specific method to delete keys matching a pattern.
            # Page cache keys created by @cache_page typically contain 'views.decorators.cache'
            # We use a broad pattern to catch them while avoiding 'django.contrib.sessions'
            if hasattr(cache, 'delete_pattern'):
                count = cache.delete_pattern("*:views.decorators.cache.cache_page.*")
                self.stdout.write(self.style.SUCCESS(f'Successfully cleared {count} cached pages. Sessions were preserved.'))
            else:
                # Fallback for backends that don't support delete_pattern
                # If we can't be surgical, we warn the user
                self.stdout.write(self.style.WARNING('Backend does not support surgical deletion. Fallback to full clear not performed for safety.'))
                self.stdout.write('Please clear Redis manually or use cache.clear() if sessions are not critical.')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to clear cache: {str(e)}'))
