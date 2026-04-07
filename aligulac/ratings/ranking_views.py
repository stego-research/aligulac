# {{{ Imports
from django.db.models import (
    Q,
    Sum,
)
from django.shortcuts import (
    get_object_or_404,
    render,
)
from django.template.defaultfilters import (
    date as django_date_filter
)
from django.utils.translation import gettext_lazy as _

from aligulac.cache import cache_page
from aligulac.settings import INACTIVE_THRESHOLD, SHOW_PER_LIST_PAGE
from aligulac.tools import (
    Message,
    base_ctx,
    get_param,
)
from ratings.models import (
    Earnings,
    P,
    Period,
    Player,
    Rating,
    T,
    Z,
)
from ratings.tools import (
    count_matchup_games,
    count_mirror_games,
    country_list,
    currency_list,
    filter_active,
    populate_teams,
    total_ratings,
)

# }}}

msg_preview = _('This is a <em>preview</em> of the next rating list. It will not be finalized until %s.')


# {{{ periods view
@cache_page
def periods(request):
    base = base_ctx('Ranking', 'History', request)
    base['periods'] = Period.objects.filter(computed=True).order_by('-id')

    return render(request, 'periods.djhtml', base)


# }}}

# {{{ period view
@cache_page
def period(request, period_id=None):
    base = base_ctx('Ranking', 'Current', request)

    # {{{ Get period object
    if not period_id:
        period = base['curp']
    else:
        period = get_object_or_404(Period, id=period_id, computed=True)

    if period.is_preview():
        base['messages'].append(Message(msg_preview % django_date_filter(period.end, 'F jS'), type=Message.INFO))

    base['period'] = period
    if period.id != base['curp'].id:
        base['curpage'] = ''
    # }}}

    from aligulac.cache import cached_query
    from django.conf import settings

    # {{{ Best, most specialised, gainers, losers, matchup stats, and country list
    def get_period_stats():
        stats = {}
        # Best and most specialised players
        qset = total_ratings(filter_active(Rating.objects.filter(period=period))).select_related('player')
        qsetp = qset.filter(player__race=P)
        qsett = qset.filter(player__race=T)
        qsetz = qset.filter(player__race=Z)
        stats.update({
            'best': qset.latest('rating'),
            'bestvp': qset.latest('tot_vp'),
            'bestvt': qset.latest('tot_vt'),
            'bestvz': qset.latest('tot_vz'),
            'bestp': qsetp.latest('rating'),
            'bestpvp': qsetp.latest('tot_vp'),
            'bestpvt': qsetp.latest('tot_vp'),
            'bestpvz': qsetp.latest('tot_vp'),
            'bestt': qsett.latest('rating'),
            'besttvp': qsett.latest('tot_vp'),
            'besttvt': qsett.latest('tot_vt'),
            'besttvz': qsett.latest('tot_vz'),
            'bestz': qsetz.latest('rating'),
            'bestzvp': qsetz.latest('tot_vp'),
            'bestzvt': qsetz.latest('tot_vt'),
            'bestzvz': qsetz.latest('tot_vz'),
            'specvp': qset.extra(select={'d': 'rating_vp/dev_vp*(rating+1.5)'}).latest('d'),
            'specvt': qset.extra(select={'d': 'rating_vt/dev_vt*(rating+1.5)'}).latest('d'),
            'specvz': qset.extra(select={'d': 'rating_vz/dev_vz*(rating+1.5)'}).latest('d'),
            'specpvp': qsetp.extra(select={'d': 'rating_vp/dev_vp*(rating+1.5)'}).latest('d'),
            'specpvt': qsetp.extra(select={'d': 'rating_vt/dev_vt*(rating+1.5)'}).latest('d'),
            'specpvz': qsetp.extra(select={'d': 'rating_vz/dev_vz*(rating+1.5)'}).latest('d'),
            'spectvp': qsett.extra(select={'d': 'rating_vp/dev_vp*(rating+1.5)'}).latest('d'),
            'spectvt': qsett.extra(select={'d': 'rating_vt/dev_vt*(rating+1.5)'}).latest('d'),
            'spectvz': qsett.extra(select={'d': 'rating_vz/dev_vz*(rating+1.5)'}).latest('d'),
            'speczvp': qsetz.extra(select={'d': 'rating_vp/dev_vp*(rating+1.5)'}).latest('d'),
            'speczvt': qsetz.extra(select={'d': 'rating_vt/dev_vt*(rating+1.5)'}).latest('d'),
            'speczvz': qsetz.extra(select={'d': 'rating_vz/dev_vz*(rating+1.5)'}).latest('d'),
        })
        # Highest gainer and biggest losers
        gainers = filter_active(Rating.objects.filter(period=period)) \
            .filter(prev__isnull=False) \
            .select_related('prev', 'player') \
            .extra(select={'diff': 'rating.rating - T3.rating'}) \
            .order_by('-diff')
        losers = filter_active(Rating.objects.filter(period=period)) \
            .filter(prev__isnull=False) \
            .select_related('prev', 'player') \
            .extra(select={'diff': 'rating.rating - T3.rating'}) \
            .order_by('diff')

        stats['updown'] = list(zip(list(gainers[:5]), list(losers[:5])))

        # Matchup statistics
        qset_matches = period.match_set
        stats['pvt_wins'], stats['pvt_loss'] = count_matchup_games(qset_matches, 'P', 'T')
        stats['pvz_wins'], stats['pvz_loss'] = count_matchup_games(qset_matches, 'P', 'Z')
        stats['tvz_wins'], stats['tvz_loss'] = count_matchup_games(qset_matches, 'T', 'Z')
        stats.update({
            'pvp_games': count_mirror_games(qset_matches, 'P'),
            'tvt_games': count_mirror_games(qset_matches, 'T'),
            'zvz_games': count_mirror_games(qset_matches, 'Z'),
        })
        stats['tot_mirror'] = stats['pvp_games'] + stats['tvt_games'] + stats['zvz_games']

        # Build country list
        all_players = Player.objects.filter(rating__period_id=period.id, rating__decay__lt=INACTIVE_THRESHOLD)
        stats['countries'] = country_list(all_players)
        
        return stats

    period_stats = cached_query(
        request,
        f"period_stats_{period.id}",
        get_period_stats,
        timeout=settings.CACHE_TIMES.get('ratings.ranking_views.period', 900)
    )
    base.update(period_stats)
    # }}}

    # {{{ Filtering and pagination
    race = get_param(request, 'race', 'ptzrs')
    nats = get_param(request, 'nats', 'all')
    sort = get_param(request, 'sort', '')
    page = int(get_param(request, 'page', 1))

    def get_period_entries():
        # Initial filtering of ratings
        entries = filter_active(period.rating_set).select_related('player')

        # Race filter
        q = Q()
        for r in race:
            q |= Q(player__race=r.upper())
        entries = entries.filter(q)

        # Country filter
        if nats == 'foreigners':
            entries = entries.exclude(player__country='KR')
        elif nats != 'all':
            entries = entries.filter(player__country=nats)

        # Sorting
        if sort not in ['vp', 'vt', 'vz']:
            entries = entries.order_by('-rating', 'player__tag')
        else:
            entries = entries.extra(select={'d': 'rating+rating_' + sort}).order_by('-d', 'player__tag')

        entries = entries.prefetch_related('prev')

        # Pages etc.
        pagesize = SHOW_PER_LIST_PAGE
        nitems = entries.count()
        npages = nitems // pagesize + (1 if nitems % pagesize > 0 else 0)
        actual_page = min(max(page, 1), npages)
        
        entries_list = list(entries[(actual_page - 1) * pagesize: actual_page * pagesize]) if actual_page > 0 else []

        return {
            'entries': populate_teams(entries_list),
            'npages': npages,
            'nitems': nitems,
            'page': actual_page,
        }

    entries_data = cached_query(
        request,
        f"period_entries_{period.id}_{race}_{nats}_{sort}_{page}",
        get_period_entries,
        timeout=settings.CACHE_TIMES.get('ratings.ranking_views.period', 900)
    )
    
    actual_page = entries_data['page']
    npages = entries_data['npages']
    pagesize = SHOW_PER_LIST_PAGE

    pn_start, pn_end = actual_page - 2, actual_page + 2
    if pn_start < 1:
        pn_end += 1 - pn_start
        pn_start = 1
    if pn_end > npages:
        pn_start -= pn_end - npages
        pn_end = npages
    if pn_start < 1:
        pn_start = 1

    base.update({
        'race': race,
        'nats': nats,
        'sort': sort,
        'page': actual_page,
        'npages': npages,
        'startcount': (actual_page - 1) * pagesize,
        'entries': entries_data['entries'],
        'nperiods': Period.objects.filter(computed=True).count(),
        'pn_range': range(pn_start, pn_end + 1),
    })
    # }}}

    base.update({
        'sortable': True,
        'localcount': True,
    })

    fmt_date = django_date_filter(period.end, "F jS, Y")

    return render(request, 'period.djhtml', base)


# }}}

# {{{ earnings view
@cache_page
def earnings(request):
    base = base_ctx('Ranking', 'Earnings', request)

    from aligulac.cache import cached_query
    from django.conf import settings

    # {{{ Build country and currency list
    def get_earnings_stats():
        all_players = Player.objects.filter(earnings__player__isnull=False).distinct()
        return {
            'countries': country_list(all_players),
            'currencies': currency_list(Earnings.objects),
        }

    stats = cached_query(request, "earnings_stats", get_earnings_stats, timeout=900)
    base.update(stats)
    # }}}

    # {{{ Initial filtering of earnings
    year = get_param(request, 'year', 'all')
    nats = get_param(request, 'country', 'all')
    curs = get_param(request, 'currency', 'all')
    page = int(get_param(request, 'page', 1))

    base['filters'] = {'year': year, 'country': nats, 'currency': curs}

    def get_earnings_ranking():
        preranking = Earnings.objects.filter(earnings__isnull=False)

        # Filtering by year
        if year != 'all':
            preranking = preranking.filter(event__latest__year=int(year))

        # Country filter
        if nats == 'foreigners':
            preranking = preranking.exclude(player__country='KR')
        elif nats != 'all':
            preranking = preranking.filter(player__country=nats)

        # Currency filter
        if curs != 'all':
            preranking = preranking.filter(currency=curs)

        totalorigprizepool = preranking.aggregate(Sum('origearnings'))['origearnings__sum']
        totalprizepool = preranking.aggregate(Sum('earnings'))['earnings__sum']

        ranking_qset = (
            preranking.values('player')
            .annotate(totalorigearnings=Sum('origearnings'))
            .annotate(totalearnings=Sum('earnings'))
            .order_by('-totalearnings', 'player')
        )

        nitems = ranking_qset.count()
        pagesize = SHOW_PER_LIST_PAGE
        npages = nitems // pagesize + (1 if nitems % pagesize > 0 else 0)
        actual_page = min(max(page, 1), npages)

        if nitems > 0:
            ranking_list = list(ranking_qset[(actual_page - 1) * pagesize: actual_page * pagesize])
            
            # Populate with player and team objects
            ids = [p['player'] for p in ranking_list]
            players = Player.objects.in_bulk(ids)
            for p in ranking_list:
                p['playerobj'] = players[p['player']]
                p['teamobj'] = p['playerobj'].get_current_team()
        else:
            ranking_list = []

        return {
            'ranking': ranking_list,
            'totalorigprizepool': totalorigprizepool,
            'totalprizepool': totalprizepool,
            'nitems': nitems,
            'npages': npages,
            'page': actual_page,
        }

    ranking_data = cached_query(
        request,
        f"earnings_ranking_{year}_{nats}_{curs}_{page}",
        get_earnings_ranking,
        timeout=900
    )

    actual_page = ranking_data['page']
    npages = ranking_data['npages']
    pagesize = SHOW_PER_LIST_PAGE

    pn_start, pn_end = actual_page - 2, actual_page + 2
    if pn_start < 1:
        pn_end += 1 - pn_start
        pn_start = 1
    if pn_end > npages:
        pn_start -= pn_end - npages
        pn_end = npages
    if pn_start < 1:
        pn_start = 1

    base.update({
        'ranking': ranking_data['ranking'],
        'totalorigprizepool': ranking_data['totalorigprizepool'],
        'totalprizepool': ranking_data['totalprizepool'],
        'page': actual_page,
        'npages': npages,
        'startcount': (actual_page - 1) * pagesize,
        'pn_range': range(pn_start, pn_end + 1),
    })

    if not ranking_data['ranking']:
        base['empty'] = True
    # }}}

    return render(request, 'earnings.djhtml', base)
# }}}
