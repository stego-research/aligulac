# {{{ Imports

from django.shortcuts import render_to_response

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

    base.update({
        'charts': True,
        'patches': PATCHES,
        'entries': BalanceEntry.objects.all().order_by('date'),
    })

    return render_to_response('reports_balance.djhtml', base)
# }}}
