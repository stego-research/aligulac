# {{{ Imports

from django.shortcuts import render

from aligulac.cache import cache_page
from aligulac.tools import (
    base_ctx,
)
from ratings.models import (
    BalanceEntry,
)
from ratings.tools import (
    PATCHES,
)


# }}}

# {{{ Balance report view
@cache_page
def balance(request):
    base = base_ctx('Misc', 'Balance Report', request)

    def get_balance_entries():
        return list(BalanceEntry.objects.all().order_by('date'))

    from aligulac.cache import cached_query
    from django.conf import settings
    entries = cached_query(
        request,
        "balance_entries",
        get_balance_entries,
        timeout=settings.CACHE_TIMES.get('ratings.reports_views.balance', 43200)
    )

    base.update({
        'charts': True,
        'patches': PATCHES,
        'entries': entries,
    })

    return render(request, 'reports_balance.djhtml', base)
# }}}
