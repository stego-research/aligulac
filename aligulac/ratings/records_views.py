# {{{ Imports
from django.shortcuts import render

from aligulac.cache import cache_page
from aligulac.tools import (
    base_ctx,
    get_param,
    get_param_choice,
)
from countries import data
from ratings.models import (
    Player,
    Rating,
    RACES,
)
from ratings.tools import (
    PATCHES,
    filter_active,
    country_list,
    total_ratings,
)


# }}}

# {{{ history view
@cache_page
def history(request):
    base = base_ctx('Records', 'History', request)

    # {{{ Filtering (appears faster with custom SQL)
    nplayers = int(get_param(request, 'nplayers', '5'))
    race = get_param_choice(request, 'race', ['ptzrs', 'p', 't', 'z', 'ptrs', 'tzrs', 'pzrs'], 'ptzrs')
    nats = get_param_choice(request, 'nats', ['all', 'foreigners'] + list(data.ccn_to_cca2.values()), 'all')

    def get_history():
        query = '''SELECT player.id, player.tag, player.race, player.country, MAX(rating.rating) AS high
                   FROM player
                            JOIN rating ON player.id = rating.player_id'''
        params = []
        if race != 'ptzrs' or nats != 'all':
            query += ' WHERE '
            ands = []
            if race != 'ptzrs':
                race_filters = []
                for r in race:
                    race_filters.append("player.race=%s")
                    params.append(r.upper())
                ands.append('(' + ' OR '.join(race_filters) + ')')
            if nats == 'foreigners':
                ands.append("(player.country!='KR')")
            elif nats != 'all':
                ands.append("(player.country=%s)")
                params.append(nats)
            query += ' AND '.join(ands)
        query += ' GROUP BY player.id, player.tag, player.race, player.country ORDER BY high DESC LIMIT %s'
        params.append(nplayers)

        players_raw = list(Player.objects.raw(query, params))
        player_ids = [p.id for p in players_raw]

        # Use .values() to fetch only needed fields and avoid creating 1000s of model instances.
        # This significantly reduces unpickling time when retrieving from cache.
        all_ratings = Rating.objects.filter(player_id__in=player_ids).values(
            'player_id', 'period__end', 'bf_rating'
        ).order_by('period__end')
        
        ratings_by_player = {}
        from datetime import date
        epoch = date(1970, 1, 1)
        
        for r in all_ratings:
            pid = r['player_id']
            if pid not in ratings_by_player:
                ratings_by_player[pid] = []
            
            date_val = r['period__end']
            rating_val = r['bf_rating']
            
            # Pre-calculate Highcharts data to speed up template rendering
            y = int(round((float(rating_val) + 1.0) * 1000))
            ratings_by_player[pid].append({
                'name': f"{date_val}: {y}",
                'x': (date_val - epoch).days * 24 * 60 * 60 * 1000,
                'y': y
            })

        return [
            {
                'tag': p.tag,
                'race': p.race,
                'ratings': ratings_by_player.get(p.id, [])
            }
            for p in players_raw
        ]

    from aligulac.cache import cached_query
    from django.conf import settings
    cache_key = f"records_history_{nplayers}_{race}_{nats}"
    players_data = cached_query(
        request,
        cache_key,
        get_history,
        timeout=settings.CACHE_TIMES.get('ratings.records_views.history', 900)
    )
    # }}}

    # Cache the country list since it changes very rarely and Player.objects.all() is slow.
    countries = cached_query(
        request,
        'country_list_all',
        lambda: country_list(Player.objects.all()),
        timeout=86400
    )

    base.update({
        'race': race,
        'nats': nats,
        'nplayers': nplayers,
        'players': players_data,
        'countries': countries,
        'charts': True,
        'patches': PATCHES,
    })

    return render(request, 'history.djhtml', base)


# }}}

# {{{ hof view
@cache_page
def hof(request):
    base = base_ctx('Records', 'HoF', request)

    def get_hof():
        return list(Player.objects.filter(
            dom_val__isnull=False, dom_start__isnull=False, dom_end__isnull=False, dom_val__gt=0
        ).order_by('-dom_val'))

    from aligulac.cache import cached_query
    from django.conf import settings
    base['high'] = cached_query(
        request,
        "records_hof",
        get_hof,
        timeout=settings.CACHE_TIMES.get('ratings.records_views.hof', 43200)
    )

    return render(request, 'hof.djhtml', base)


# }}}

# {{{ filter stolen from templatetags/ratings_extras.py
def racefull(value):
    return dict(RACES)[value]


# }}}

# {{{ race view
@cache_page
def race(request):
    race = get_param(request, 'race', 'all')
    if race not in 'PTZ':
        race = 'all'
    sub = ['All', 'Protoss', 'Terran', 'Zerg'][['all', 'P', 'T', 'Z'].index(race)]

    base = base_ctx('Records', sub, request)

    def sift(lst, num=5):
        ret, pls = [], set()
        for r in lst:
            if not r.player_id in pls:
                pls.add(r.player_id)
                ret.append(r)
            if len(ret) == num:
                return ret
        return ret

    high = (
        filter_active(total_ratings(Rating.objects.all()))
        .filter(period__id__gt=16).select_related('player', 'period')
    )

    if race != 'all':
        high = high.filter(player__race=race)

    base.update({
        'hightot': sift(high.order_by('-rating')[:200]),
        'highp': sift(high.order_by('-tot_vp')[:200]),
        'hight': sift(high.order_by('-tot_vt')[:200]),
        'highz': sift(high.order_by('-tot_vz')[:200]),
        'race': race if race != 'all' else '',
    })

    return render(request, 'records.djhtml', base)
# }}}
