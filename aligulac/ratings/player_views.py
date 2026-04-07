# {{{ Imports
import shlex
from datetime import datetime, date
from itertools import zip_longest
from math import sqrt
from urllib.parse import urlencode

from dateutil.relativedelta import relativedelta
from django import forms
from django.core.paginator import Paginator
from django.db.models import Sum, Q, Case, When, F, Count, IntegerField
from django.shortcuts import render, get_object_or_404
from django.utils.translation import gettext_lazy as _

from aligulac.cache import cache_page
from aligulac.settings import INACTIVE_THRESHOLD, SHOW_PER_LIST_PAGE
from aligulac.tools import (
    base_ctx,
    cache_login_protect,
    etn,
    generate_messages,
    get_param,
    Message,
    ntz,
    StrippedCharField,
)
from countries import (
    data,
    transformations,
)
from ratings.models import (
    GAMES,
    P,
    Period,
    Player,
    RACES,
    Rating,
    T,
    TLPD_DBS,
    WCS_TIERS,
    WCS_YEARS,
    Z
)
from ratings.tools import (
    add_counts,
    cdf,
    count_winloss_player,
    count_matchup_player,
    display_matches,
    filter_flags,
    get_placements,
    PATCHES,
    total_ratings,
)
from ratings.templatetags.ratings_extras import (
    milliseconds,
    ratscale,
)

# }}}

msg_inactive = _(
    'Due to %s\'s lack of recent games, they have been marked as <em>inactive</em> and '
    'removed from the current rating list. Once they play a rated game they will be reinstated.'
)
msg_nochart = _('%s has no rating chart on account of having played matches in fewer than two periods.')


# {{{ meandate: Rudimentary function for sorting objects with a start and end date.
def meandate(tm):
    if tm.start is not None and tm.end is not None:
        return (tm.start.toordinal() + tm.end.toordinal()) / 2
    elif tm.start is not None:
        return tm.start.toordinal()
    elif tm.end is not None:
        return tm.end.toordinal()
    else:
        return 1000000


# }}}

# {{{ interp_rating: Takes a date and a rating list, and interpolates linearly.
def interp_rating(date, ratings):
    for ind, r in enumerate(ratings):
        if (r['period__end'] - date).days >= 0:
            if ind == 0:
                return r['bf_rating']
            try:
                right = (r['period__end'] - date).days
                left = (date - ratings[ind - 1]['period__end']).days
                return (left * r['bf_rating'] + right * ratings[ind - 1]['bf_rating']) / (left + right)
            except ZeroDivisionError:
                return r['bf_rating']
    return ratings[-1]['bf_rating']


# }}}

# {{{ PlayerModForm: Form for modifying a player.
class PlayerModForm(forms.Form):
    tag = StrippedCharField(max_length=30, required=True, label=_('Tag'))
    race = forms.ChoiceField(choices=RACES, required=True, label=_('Race'))
    name = StrippedCharField(max_length=100, required=False, label=_('Name'))
    romanized_name = StrippedCharField(max_length=100, required=False, label=_('Romanized Name'))
    akas = forms.CharField(max_length=200, required=False, label=_('AKAs'))
    birthday = forms.DateField(required=False, label=_('Birthday'))

    tlpd_id = forms.IntegerField(required=False, label=_('TLPD ID'))
    tlpd_db = forms.MultipleChoiceField(
        required=False, choices=TLPD_DBS, label=_('TLPD DB'), widget=forms.CheckboxSelectMultiple)
    lp_name = StrippedCharField(max_length=200, required=False, label=_('Liquipedia title'))
    sc2e_id = forms.IntegerField(required=False, label=_('SC2Earnings.com ID'))

    country = forms.ChoiceField(choices=data.countries, required=False, label=_('Country'))

    # {{{ Constructor
    def __init__(self, request=None, player=None):
        if request is not None:
            super(PlayerModForm, self).__init__(request.POST)
        else:
            super(PlayerModForm, self).__init__(initial={
                'tag': player.tag,
                'race': player.race,
                'country': player.country,
                'name': player.name,
                'romanized_name': player.romanized_name,
                'akas': ', '.join(player.get_aliases()),
                'birthday': player.birthday,
                'sc2e_id': player.sc2e_id,
                'lp_name': player.lp_name,
                'tlpd_id': player.tlpd_id,
                'tlpd_db': filter_flags(player.tlpd_db if player.tlpd_db else 0),
            })

        self.label_suffix = ''

    # }}}

    # {{{ update_player: Pushes updates to player, responds with messages
    def update_player(self, player):
        ret = []

        if not self.is_valid():
            ret.append(Message(_('Entered data was invalid, no changes made.'), type=Message.ERROR))
            for field, errors in self.errors.items():
                for error in errors:
                    ret.append(Message(error=error, field=self.fields[field].label))
            return ret

        def update(value, attr, setter, label):
            if value != getattr(player, attr):
                getattr(player, setter)(value)
                # Translators: Changed something (a noun).
                ret.append(Message(_('Changed %s.') % label, type=Message.SUCCESS))

        update(self.cleaned_data['tag'], 'tag', 'set_tag', _('tag'))
        update(self.cleaned_data['race'], 'race', 'set_race', _('race'))
        update(self.cleaned_data['country'], 'country', 'set_country', _('country'))
        update(self.cleaned_data['name'], 'name', 'set_name', _('name'))
        update(self.cleaned_data['romanized_name'], 'romanized_name', 'set_romanized_name', _('romanized name'))
        update(self.cleaned_data['birthday'], 'birthday', 'set_birthday', _('birthday'))
        update(self.cleaned_data['tlpd_id'], 'tlpd_id', 'set_tlpd_id', _('TLPD ID'))
        update(self.cleaned_data['lp_name'], 'lp_name', 'set_lp_name', _('Liquipedia title'))
        update(self.cleaned_data['sc2e_id'], 'sc2e_id', 'set_sc2e_id', _('SC2Earnings.com ID'))
        update(sum([int(a) for a in self.cleaned_data['tlpd_db']]), 'tlpd_db', 'set_tlpd_db', _('TLPD DBs'))

        if player.set_aliases([x for x in self.cleaned_data['akas'].split(',') if x.strip() != '']):
            ret.append(Message(_('Changed aliases.'), type=Message.SUCCESS))

        return ret
    # }}}


# }}}

# {{{ ResultsFilterForm: Form for filtering results.
class ResultsFilterForm(forms.Form):
    after = forms.DateField(required=False, label=_('After'))
    before = forms.DateField(required=False, label=_('Before'))
    event = forms.CharField(required=False, label=_('Event'))
    race = forms.ChoiceField(
        choices=[
            ('ptzr', _('All')),
            ('p', _('Protoss')),
            ('t', _('Terran')),
            ('z', _('Zerg')),
            ('tzr', _('No Protoss')),
            ('pzr', _('No Terran')),
            ('ptr', _('No Zerg')),
        ],
        required=False, label=_('Opponent race'), initial='ptzr'
    )
    country = forms.ChoiceField(
        choices=[('all', _('All')), ('KR', _('South Korea')), ('foreigners', _('Non-Koreans')), ('', '')] +
                sorted(data.countries, key=lambda a: a[1]),
        required=False, label=_('Country'), initial='all'
    )
    bestof = forms.ChoiceField(
        choices=[
            ('all', _('All')),
            ('3', _('Best of 3+')),
            ('5', _('Best of 5+')),
        ],
        required=False, label=_('Match format'), initial='all'
    )
    offline = forms.ChoiceField(
        choices=[
            ('both', _('Both')),
            ('offline', _('Offline')),
            ('online', _('Online')),
        ],
        required=False, label=_('On/offline'), initial='both',
    )
    wcs_season = forms.ChoiceField(
        choices=[
                    ('', _('All events')),
                    ('all', _('All seasons')),
                ] + WCS_YEARS,
        required=False, label=_('WCS Season'), initial='',
    )
    _all_tiers = ''.join(map(lambda t: str(t[0]), WCS_TIERS))
    wcs_tier = forms.ChoiceField(
        choices=[
                    ('', _('All events')),
                    (_all_tiers, _('All tiers')),
                ] + WCS_TIERS + [
                    (''.join(map(lambda t: str(t[0]), WCS_TIERS[1:])), _('Non-native'))
                ],
        required=False, label=_('WCS Tier'), initial='',
    )
    game = forms.ChoiceField(
        choices=[('all', 'All')] + GAMES, required=False, label=_('Game version'), initial='all')

    # {{{ Constructor
    def __init__(self, *args, **kwargs):
        super(ResultsFilterForm, self).__init__(*args, **kwargs)

        self.label_suffix = ''

    # }}}

    # {{{ Cleaning with default values
    def clean_default(self, field):
        if not self[field].html_name in self.data:
            return self.fields[field].initial
        return self.cleaned_data[field]

    clean_race = lambda s: s.clean_default('race')
    clean_country = lambda s: s.clean_default('country')
    clean_bestof = lambda s: s.clean_default('bestof')
    clean_offline = lambda s: s.clean_default('offline')
    clean_wcs_season = lambda s: s.clean_default('wcs_season')
    clean_wcs_tier = lambda s: s.clean_default('wcs_tier')
    clean_game = lambda s: s.clean_default('game')
    # }}}


# }}}

# {{{ player view
@cache_login_protect
def player(request, player_id):
    # {{{ Get player object and base context, generate messages and make changes if needed
    player = get_object_or_404(Player, id=player_id)
    base = base_ctx('Ranking', 'Summary', request, context=player)

    if request.method == 'POST' and 'modplayer' in request.POST and base['adm']:
        modform = PlayerModForm(request)
        base['messages'] += modform.update_player(player)
    else:
        modform = PlayerModForm(player=player)

    base['messages'] += generate_messages(player)
    # }}}

    # {{{ Various easy data
    from aligulac.cache import cached_query
    from django.conf import settings

    def get_player_stats():
        matches = player.get_matchset()
        recent = matches.filter(date__gte=(date.today() - relativedelta(months=2)))

        # Efficiently fetch counts in a single aggregation
        stats = matches.aggregate(
            total_m=Count('id'),
            offline_m=Count('id', filter=Q(offline=True)),
            # Match wins/losses
            m_win=Count('id', filter=(Q(pla=player, sca__gt=F('scb')) | Q(plb=player, scb__gt=F('sca')))),
            m_loss=Count('id', filter=(Q(pla=player, sca__lt=F('scb')) | Q(plb=player, scb__lt=F('sca')))),
            # Game wins/losses
            g_win=Sum(Case(When(pla=player, then=F('sca')), When(plb=player, then=F('scb')), default=0)),
            g_loss=Sum(Case(When(pla=player, then=F('scb')), When(plb=player, then=F('sca')), default=0)),
        )
        
        # Recent stats
        recent_stats = recent.aggregate(
            m_win=Count('id', filter=(Q(pla=player, sca__gt=F('scb')) | Q(plb=player, scb__gt=F('sca')))),
            m_loss=Count('id', filter=(Q(pla=player, sca__lt=F('scb')) | Q(plb=player, scb__lt=F('sca')))),
            g_win=Sum(Case(When(pla=player, then=F('sca')), When(plb=player, then=F('scb')), default=0)),
            g_loss=Sum(Case(When(pla=player, then=F('scb')), When(plb=player, then=F('sca')), default=0)),
        )

        return {
            'first_date': etn(lambda: matches.earliest('date').date),
            'last_date': etn(lambda: matches.latest('date').date),
            'totalmatches': stats['total_m'],
            'offlinematches': stats['offline_m'],
            'earnings': ntz(player.earnings_set.aggregate(Sum('earnings'))['earnings__sum']),
            'total': (ntz(stats['g_win']), ntz(stats['g_loss'])),
            'vp': count_matchup_player(matches, player, P),
            'vt': count_matchup_player(matches, player, T),
            'vz': count_matchup_player(matches, player, Z),
            'totalf': (ntz(recent_stats['g_win']), ntz(recent_stats['g_loss'])),
            'vpf': count_matchup_player(recent, player, P),
            'vtf': count_matchup_player(recent, player, T),
            'vzf': count_matchup_player(recent, player, Z),
            'riv_nem_vic': list(zip_longest(
                list(player.rivals),
                list(player.nemesis),
                list(player.victim)
            ))
        }

    stats_cache_key = f"player_stats_{player.id}"
    p_stats = cached_query(request, stats_cache_key, get_player_stats, timeout=3600)

    base.update(p_stats)
    base.update({
        'player': player,
        'modform': modform,
        'aliases': list(player.alias_set.all().values('name')),
        'team': player.get_current_team(),
    })

    if player.country is not None:
        base['countryfull'] = transformations.cc_to_cn(player.country)
    # }}}

    # {{{ Recent matches
    # We don't cache this as much or use simple dicts because display_matches is complex
    matches = player.get_matchset(related=['rta', 'rtb', 'pla', 'plb', 'eventobj'])[0:10]
    if matches.exists():
        base['matches'] = display_matches(matches, fix_left=player, ratings=True)
    # }}}

    # {{{ Team memberships
    def get_team_history():
        mems = list(player.groupmembership_set.filter(group__is_team=True).select_related('group'))
        mems.sort(key=lambda t: t.id, reverse=True)
        mems.sort(key=meandate, reverse=True)
        mems.sort(key=lambda t: t.current, reverse=True)
        return [{
            'group': {'id': m.group_id, 'name': m.group.name},
            'start': m.start,
            'end': m.end,
            'current': m.current
        } for m in mems]

    base['teammems'] = cached_query(request, f"player_teams_{player.id}", get_team_history, timeout=3600)
    # }}}

    # {{{ If the player has at least one rating
    def get_rating_data():
        if not player.current_rating:
            return {'charts': False}

        ratings_q = total_ratings(player.rating_set.filter(period__computed=True)).select_related('period')
        
        def get_rating_dict(r):
            if not r: return None
            return {
                'rating': r.rating,
                'rating_vp': r.rating_vp,
                'rating_vt': r.rating_vt,
                'rating_vz': r.rating_vz,
                'tot_vp': r.rating + r.rating_vp,
                'tot_vt': r.rating + r.rating_vt,
                'tot_vz': r.rating + r.rating_vz,
                'dev': r.dev,
                'dev_vp': r.dev_vp,
                'dev_vt': r.dev_vt,
                'dev_vz': r.dev_vz,
                'tot_dev_vp': sqrt(r.dev**2 + r.dev_vp**2),
                'tot_dev_vt': sqrt(r.dev**2 + r.dev_vt**2),
                'tot_dev_vz': sqrt(r.dev**2 + r.dev_vz**2),
                'position': r.position,
                'position_vp': r.position_vp,
                'position_vt': r.position_vt,
                'position_vz': r.position_vz,
                'period': {
                    'id': r.period_id, 
                    'end': r.period.end,
                    'start': r.period.start,
                },
                'decay': r.decay,
            }

        recent_update = player.get_latest_rating_update()
        first_rating = ratings_q.earliest('period')
        
        res = {
            'highs': (
                get_rating_dict(ratings_q.order_by('-rating').first()),
                get_rating_dict(ratings_q.order_by('-tot_vp').first()),
                get_rating_dict(ratings_q.order_by('-tot_vt').first()),
                get_rating_dict(ratings_q.order_by('-tot_vz').first()),
            ),
            'recentchange': get_rating_dict(recent_update),
            'firstrating': get_rating_dict(first_rating),
            'rating': get_rating_dict(player.current_rating),
            'charts': recent_update.period_id > first_rating.period_id
        }

        if res['charts']:
            # Fetch ratings using .values() to minimize object unpickling overhead
            ratings_query = (
                total_ratings(player.rating_set.filter(period_id__lte=recent_update.period_id))
                .values('id', 'period_id', 'period__start', 'period__end', 'rating', 'tot_vp', 'tot_vt', 'tot_vz', 
                        'bf_rating', 'bf_rating_vp', 'bf_rating_vt', 'bf_rating_vz', 'prev_id')
                .order_by('period_id')
            )
            
            # Optimized match count fetching
            match_stats = player.get_matchset().values('period_id').annotate(
                nmatches=Count('id'),
                ngames=Sum(F('sca') + F('scb'))
            )
            stats_map = {s['period_id']: s for s in match_stats}

            ratings_list = []
            for r in ratings_query:
                s = stats_map.get(r['period_id'], {'nmatches': 0, 'ngames': 0})
                
                # Pre-calculate data for Highcharts to avoid template filter overhead
                # Reuse canonical logic from templatetags
                r['ms'] = milliseconds(r['period__end'])
                r['r_gen'] = ratscale(r['bf_rating'])
                r['r_vp'] = ratscale(float(r['bf_rating']) + float(r['bf_rating_vp']))
                r['r_vt'] = ratscale(float(r['bf_rating']) + float(r['bf_rating_vt']))
                r['r_vz'] = ratscale(float(r['bf_rating']) + float(r['bf_rating_vz']))
                
                r['nmatches'] = s['nmatches']
                r['ngames'] = s['ngames']
                ratings_list.append(r)

            # Look through team changes
            teampoints = []
            for mem in base['teammems']: # Use teampoints from outer scope
                if mem['start'] and res['firstrating']['period']['end'] < mem['start'] < res['recentchange']['period']['end']:
                    teampoints.append({
                        'date': mem['start'],
                        'ms': milliseconds(mem['start']),
                        'rating': ratscale(interp_rating(mem['start'], ratings_list)),
                        'data': [{'date': mem['start'], 'team': mem['group'], 'jol': _('joins')}],
                    })
                if mem['end'] and res['firstrating']['period']['end'] < mem['end'] < res['recentchange']['period']['end']:
                    teampoints.append({
                        'date': mem['end'],
                        'ms': milliseconds(mem['end']),
                        'rating': ratscale(interp_rating(mem['end'], ratings_list)),
                        'data': [{'date': mem['end'], 'team': mem['group'], 'jol': _('leaves')}],
                    })
            teampoints.sort(key=lambda p: p['date'])

            # Condense team switches
            cur = 0
            while cur < len(teampoints) - 1:
                if (teampoints[cur + 1]['date'] - teampoints[cur]['date']).days <= 14:
                    teampoints[cur]['data'].append(teampoints[cur + 1]['data'][0])
                    del teampoints[cur + 1]
                else:
                    cur += 1

            for point in teampoints:
                point['data'].sort(key=lambda a: a['jol'], reverse=True)
                point['data'].sort(key=lambda a: a['date'])

            # Look through stories
            stories = list(player.story_set.all().select_related('event'))
            story_list = []
            for s in stories:
                if res['firstrating']['period']['start'] < s.date < res['recentchange']['period']['end']:
                    story_list.append({
                        'text': str(s),
                        'date': s.date,
                        'ms': milliseconds(s.date),
                        'event': {'id': s.event.id, 'fullname': s.event.fullname} if s.event else None,
                        'rating': ratscale(interp_rating(s.date, ratings_list))
                    })

            res.update({
                'ratings': ratings_list,
                'stories': story_list,
                'teampoints': teampoints,
            })
        
        return res

    # Cache key must include language because teampoints contains translated "joins"/"leaves"
    rating_cache_key = f"player_ratings_{player.id}_{request.LANGUAGE_CODE}"
    rating_data = cached_query(request, rating_cache_key, get_rating_data, timeout=3600)
    base.update(rating_data)

    if player.current_rating and player.current_rating.decay >= INACTIVE_THRESHOLD:
        base['messages'].append(Message(msg_inactive % player.tag, 'Inactive', type=Message.INFO))
    
    if not player.current_rating:
        base['messages'].append(Message(_('%s has no rating yet.') % player.tag, type=Message.INFO))
    elif not base['charts']:
        base['messages'].append(Message(msg_nochart % player.tag, type=Message.INFO))

    base['patches'] = PATCHES
    # }}}

    return render(request, 'player.djhtml', base)


# }}}

# {{{ adjustment view
@cache_page
def adjustment(request, player_id, period_id):
    # {{{ Get objects
    period = get_object_or_404(Period, id=period_id, computed=True)
    player = get_object_or_404(Player, id=player_id)
    rating = get_object_or_404(Rating, player=player, period=period)
    base = base_ctx('Ranking', 'Adjustments', request, context=player)

    base.update({
        'period': period,
        'player': player,
        'rating': rating,
        'prevlink': etn(lambda: player.rating_set.filter(period__lt=period, decay=0).latest('period')),
        'nextlink': etn(lambda: player.rating_set.filter(period__gt=period, decay=0).earliest('period')),
    })
    # }}}

    # {{{ Matches
    matches = player.get_matchset(related=['rta', 'rtb', 'pla', 'plb', 'eventobj']).filter(period=period)

    # If there are no matches, we don't need to continue
    if not matches.exists():
        return render(request, 'ratingdetails.djhtml', base)

    base.update({
        'matches': display_matches(matches, fix_left=player, ratings=True),
        'has_treated': False,
        'has_nontreated': False,
    })
    # }}}

    # {{{ Perform calculations
    tot_rating = {'M': 0.0, 'P': 0.0, 'T': 0.0, 'Z': 0.0}
    ngames = {'M': 0.0, 'P': 0.0, 'T': 0.0, 'Z': 0.0}
    expwins = {'M': 0.0, 'P': 0.0, 'T': 0.0, 'Z': 0.0}
    nwins = {'M': 0.0, 'P': 0.0, 'T': 0.0, 'Z': 0.0}

    for m in base['matches']:
        if not m['match'].treated:
            base['has_nontreated'] = True
            continue
        base['has_treated'] = True

        total_score = m['pla']['score'] + m['plb']['score']

        scale = sqrt(1 + m['pla']['dev'] ** 2 + m['plb']['dev'] ** 2)
        expected = total_score * cdf(m['pla']['rating'] - m['plb']['rating'], scale=scale)

        ngames['M'] += total_score
        tot_rating['M'] += m['plb']['rating'] * total_score
        expwins['M'] += expected
        nwins['M'] += m['pla']['score']

        vs_races = [m['plb']['race']] if m['plb']['race'] in 'PTZ' else 'PTZ'
        weight = 1 / len(vs_races)
        for r in vs_races:
            ngames[r] += weight * total_score
            tot_rating[r] += weight * m['plb']['rating'] * total_score
            expwins[r] += weight * expected
            nwins[r] += weight * m['pla']['score']

    for r in 'MPTZ':
        if ngames[r] > 0:
            tot_rating[r] /= ngames[r]

    base.update({
        'ngames': ngames,
        'tot_rating': tot_rating,
        'expwins': expwins,
        'nwins': nwins,
    })
    # }}}

    return render(request, 'ratingdetails.djhtml', base)


# }}}

# {{{ results view
@cache_page
def results(request, player_id):
    # {{{ Get objects
    player = get_object_or_404(Player, id=player_id)
    base = base_ctx('Ranking', 'Match history', request, context=player)

    base['player'] = player
    # }}}

    # {{{ Filtering
    matches = player.get_matchset(related=['pla', 'plb', 'eventobj'])

    form = ResultsFilterForm(request.GET)
    base['form'] = form

    form.is_valid()

    q = Q()
    for r in form.cleaned_data['race'].upper():
        q |= Q(pla=player, rcb=r) | Q(plb=player, rca=r)
    matches = matches.filter(q)

    if form.cleaned_data['country'] == 'foreigners':
        matches = matches.exclude(Q(pla=player, plb__country='KR') | Q(plb=player, pla__country='KR'))
    elif form.cleaned_data['country'] != 'all':
        matches = matches.filter(
            Q(pla=player, plb__country=form.cleaned_data['country'])
            | Q(plb=player, pla__country=form.cleaned_data['country'])
        )

    if form.cleaned_data['bestof'] != 'all':
        sc = int(form.cleaned_data['bestof']) // 2 + 1
        matches = matches.filter(Q(sca__gte=sc) | Q(scb__gte=sc))

    if form.cleaned_data['offline'] != 'both':
        matches = matches.filter(offline=(form.cleaned_data['offline'] == 'offline'))

    if form.cleaned_data['game'] != 'all':
        matches = matches.filter(game=form.cleaned_data['game'])

    if form.cleaned_data['wcs_season'] != '':
        if form.cleaned_data['wcs_season'] == 'all':
            matches = matches.filter(
                eventobj__uplink__parent__wcs_year__isnull=False
            )
        else:
            matches = matches.filter(
                eventobj__uplink__parent__wcs_year=int(form.cleaned_data['wcs_season'])
            )

    if form.cleaned_data['wcs_tier'] != '':
        tiers = list(map(int, form.cleaned_data['wcs_tier']))
        matches = matches.filter(
            eventobj__uplink__parent__wcs_tier__in=tiers
        )

    if form.cleaned_data['after'] is not None:
        matches = matches.filter(date__gte=form.cleaned_data['after'])

    if form.cleaned_data['before'] is not None:
        matches = matches.filter(date__lte=form.cleaned_data['before'])

    if form.cleaned_data['event'] is not None:
        lex = shlex.shlex(form.cleaned_data['event'], posix=True)
        lex.wordchars += "'"
        lex.quotes = '"'

        terms = [s.strip() for s in list(lex) if s.strip() != '']

        matches = matches.filter(
            eventobj__fullname__iregex=(
                r"\s".join(r".*{}.*".format(term) for term in terms)
            )
        )
    matches = matches.distinct().order_by('-date', '-id')
    # }}}

    # {{{ Statistics
    # Efficiently aggregate all stats in one query
    stats = matches.aggregate(
        sc_my=Sum(Case(When(pla=player, then=F('sca')), When(plb=player, then=F('scb')), default=0,
                       output_field=IntegerField())),
        sc_op=Sum(Case(When(pla=player, then=F('scb')), When(plb=player, then=F('sca')), default=0,
                       output_field=IntegerField())),
        msc_my=Count('id', filter=(Q(pla=player, sca__gt=F('scb')) | Q(plb=player, scb__gt=F('sca')))),
        msc_op=Count('id', filter=(Q(pla=player, scb__gt=F('sca')) | Q(plb=player, sca__gt=F('scb')))),
        
        # Matchup game wins/losses
        vp_w=Sum(Case(When(pla=player, rcb=P, then=F('sca')), When(plb=player, rca=P, then=F('scb')), default=0)),
        vp_l=Sum(Case(When(pla=player, rcb=P, then=F('scb')), When(plb=player, rca=P, then=F('sca')), default=0)),
        vt_w=Sum(Case(When(pla=player, rcb=T, then=F('sca')), When(plb=player, rca=T, then=F('scb')), default=0)),
        vt_l=Sum(Case(When(pla=player, rcb=T, then=F('scb')), When(plb=player, rca=T, then=F('sca')), default=0)),
        vz_w=Sum(Case(When(pla=player, rcb=Z, then=F('sca')), When(plb=player, rca=Z, then=F('scb')), default=0)),
        vz_l=Sum(Case(When(pla=player, rcb=Z, then=F('scb')), When(plb=player, rca=Z, then=F('sca')), default=0)),
    )

    recent = matches.filter(date__gte=(date.today() - relativedelta(months=2)))
    recent_stats = recent.aggregate(
        g_win=Sum(Case(When(pla=player, then=F('sca')), When(plb=player, then=F('scb')), default=0)),
        g_loss=Sum(Case(When(pla=player, then=F('scb')), When(plb=player, then=F('sca')), default=0)),
        m_win=Count('id', filter=(Q(pla=player, sca__gt=F('scb')) | Q(plb=player, scb__gt=F('sca')))),
        m_loss=Count('id', filter=(Q(pla=player, sca__lt=F('scb')) | Q(plb=player, scb__lt=F('sca')))),
        
        vp_w=Sum(Case(When(pla=player, rcb=P, then=F('sca')), When(plb=player, rca=P, then=F('scb')), default=0)),
        vp_l=Sum(Case(When(pla=player, rcb=P, then=F('scb')), When(plb=player, rca=P, then=F('sca')), default=0)),
        vt_w=Sum(Case(When(pla=player, rcb=T, then=F('sca')), When(plb=player, rca=T, then=F('scb')), default=0)),
        vt_l=Sum(Case(When(pla=player, rcb=T, then=F('scb')), When(plb=player, rca=T, then=F('sca')), default=0)),
        vz_w=Sum(Case(When(pla=player, rcb=Z, then=F('sca')), When(plb=player, rca=Z, then=F('scb')), default=0)),
        vz_l=Sum(Case(When(pla=player, rcb=Z, then=F('scb')), When(plb=player, rca=Z, then=F('sca')), default=0)),
    )

    base.update({
        'sc_my': stats['sc_my'] or 0,
        'sc_op': stats['sc_op'] or 0,
        'msc_my': stats['msc_my'] or 0,
        'msc_op': stats['msc_op'] or 0,
        'total': (stats['sc_my'] or 0, stats['sc_op'] or 0),
        'vp': (stats['vp_w'] or 0, stats['vp_l'] or 0),
        'vt': (stats['vt_w'] or 0, stats['vt_l'] or 0),
        'vz': (stats['vz_w'] or 0, stats['vz_l'] or 0),
        'totalf': (recent_stats['g_win'] or 0, recent_stats['g_loss'] or 0),
        'vpf': (recent_stats['vp_w'] or 0, recent_stats['vp_l'] or 0),
        'vtf': (recent_stats['vt_w'] or 0, recent_stats['vt_l'] or 0),
        'vzf': (recent_stats['vz_w'] or 0, recent_stats['vz_l'] or 0),
    })
    # }}}

    # {{{ Pagination
    paginator = Paginator(matches, SHOW_PER_LIST_PAGE)
    page_num = get_param(request, 'page', 1)
    page = paginator.get_page(page_num)

    base['matches'] = display_matches(page.object_list, fix_left=player)
    base['page_obj'] = page
    # }}}

    # {{{ TL Postable

    has_after = form.cleaned_data['after'] is not None
    has_before = form.cleaned_data['before'] is not None

    if not has_after and not has_before:
        match_date = ""
    elif not has_after:  # and has_before
        match_date = _(" before {}").format(form.cleaned_data['before'])
    elif not has_before:  # and has_after
        match_date = _(" after {}").format(form.cleaned_data['after'])
    else:
        match_date = _(" between {} and {}").format(form.cleaned_data['after'],
                                                    form.cleaned_data['before'])

    match_filter = ""

    def switcher(race):
        if race == "S":
            return "R"
        elif race == "s":
            return "r"
        return race

    def win(match):
        return match['pla']['score'] >= match['plb']['score']

    def format_match(d):
        # TL only recognizes lower case country codes :(
        if d["pla"]["country"] is not None:
            d["pla_country_formatted"] = ":{}:".format(d["pla"]["country"].lower())
        else:
            d["pla_country_formatted"] = ""

        if d["plb"]["country"] is not None:
            d["plb_country_formatted"] = ":{}:".format(d["plb"]["country"].lower())
        else:
            d["plb_country_formatted"] = ""

        # and no race switchers
        d["pla_race"] = switcher(d["pla"]["race"])
        d["plb_race"] = switcher(d["plb"]["race"])

        # Check who won
        temp = {
            "plaws": "",
            "plawe": "",
            "plbws": "",
            "plbwe": ""
        }

        if win(d):
            temp["plaws"] = "[b]"
            temp["plawe"] = "[/b]"
        else:
            temp["plbws"] = "[b]"
            temp["plbwe"] = "[/b]"

        d.update(temp)
        d["pla_id"] = d["pla"]["id"]
        d["pla_tag"] = d["pla"]["tag"]
        d["pla_score"] = d["pla"]["score"]
        d["plb_id"] = d["plb"]["id"]
        d["plb_tag"] = d["plb"]["tag"]
        d["plb_score"] = d["plb"]["score"]

        return TL_HISTORY_MATCH_TEMPLATE.format(**d)

    recent_matches = base['matches'][:min(10, len(base['matches']))]

    recent = "\n".join(format_match(m) for m in recent_matches)

    recent_form = " ".join("W" if win(m) else "L"
                           for m in reversed(recent_matches))

    # Get the parameters and remove those with None value
    get_params = dict((k, form.cleaned_data[k])
                      for k in form.cleaned_data
                      if form.cleaned_data[k] is not None)

    country = ""
    if player.country is not None:
        country = ":{}:".format(player.country.lower())

    tl_params = {
        "player_tag": player.tag,
        "player_country_formatted": country,
        "player_race": switcher(player.race),
        "filter": match_filter,
        "date": match_date,
        "recent": recent,
        "pid": player_id,
        "get": urlencode(get_params),
        "url": "http://aligulac.com"
    }

    tl_params.update({
        "sc_my": base["sc_my"],
        "sc_op": base["sc_op"],
        "msc_my": base["msc_my"],
        "msc_op": base["msc_op"],
        "form": recent_form
    })

    def calc_percent(s):
        f, a = float(int(tl_params[s + "_my"])), int(tl_params[s + "_op"])
        if f + a == 0:
            return "  NaN"
        return round(100 * f / (f + a), 2)

    tl_params.update({
        "sc_percent": calc_percent("sc"),
        "msc_percent": calc_percent("msc")
    })

    tl_params.update(get_params)

    # Final clean up and translation

    if tl_params["bestof"] != "all":
        tl_params["bestof"] = _('best of') + ' {}'.format(tl_params["bestof"])
    else:
        tl_params['bestof'] = _('all')

    if set(tl_params["race"]) == set('ptzr'):
        tl_params["race"] = _('all')
    else:
        tl_params['race'] = {
            'p': _('Protoss'),
            't': _('Terran'),
            'z': _('Zerg'),
            'ptr': _('No Zerg'),
            'pzr': _('No Terran'),
            'tzr': _('No Protoss'),
        }[tl_params['race']]

    if tl_params['country'] in ['all', 'foreigners']:
        tl_params['country'] = {
            'all': _('all'),
            'foreigners': _('foreigners'),
        }[tl_params['country']]
    else:
        tl_params['country'] = transformations.ccn_to_cn(transformations.cca2_to_ccn(tl_params['country']))

    tl_params['offline'] = {
        'offline': _('offline'),
        'online': _('online'),
        'both': _('both'),
    }[tl_params['offline']]

    if tl_params['game'] == 'all':
        tl_params['game'] = _('all')
    else:
        tl_params['game'] = dict(GAMES)[tl_params['game']]

    tl_params.update({
        'resfor': _('Results for'),
        'games': _('Games'),
        'matches': _('Matches'),
        'curform': _('Current form'),
        'recentmatches': _('Recent matches'),
        'filters': _('Filters'),
        # Translators: These have to line up on the right!
        'opprace': _('Opponent Race:    '),
        # Translators: These have to line up on the right!
        'oppcountry': _('Opponent Country: '),
        # Translators: These have to line up on the right!
        'matchformat': _('Match Format:     '),
        # Translators: These have to line up on the right!
        'onoff': _('On/offline:       '),
        # Translators: These have to line up on the right!
        'version': _('Game Version:     '),
        'statslink': _('Stats by [url={url}]Aligulac[/url]'),
        # Translators: Link in the sense of a HTTP hyperlink.
        'link': _('Link'),
    })

    base.update({
        # One of the replacement strings contain another string interpolation,
        # so do it twice.
        "postable_tl": TL_HISTORY_TEMPLATE.format(**tl_params).format(**tl_params)
    })

    # }}}

    return render(request, 'player_results.djhtml', base)


# }}}

# {{{ historical view
@cache_page
def historical(request, player_id):
    player = get_object_or_404(Player, id=player_id)
    base = base_ctx('Ranking', 'Rating history', request, context=player)

    latest = player.rating_set.filter(period__computed=True, decay=0).latest('period')
    historical_query = (
        player.rating_set.filter(period_id__lte=latest.period_id)
        .values('id', 'period_id', 'period__start', 'period__end', 'period__is_preview',
                'rating', 'rating_vp', 'rating_vt', 'rating_vz',
                'tot_vp', 'tot_vt', 'tot_vz', 
                'bf_rating', 'bf_rating_vp', 'bf_rating_vt', 'bf_rating_vz', 'dev', 'decay', 'position', 
                'position_vp', 'position_vt', 'position_vz', 'prev_id')
        .order_by('-period_id')
    )

    # Bulk fetch match stats
    match_stats = player.get_matchset().values('period_id').annotate(
        nmatches=Count('id'),
        ngames=Sum(F('sca') + F('scb'))
    )
    stats_map = {s['period_id']: s for s in match_stats}

    historical_list = []
    for r in historical_query:
        s = stats_map.get(r['period_id'], {'nmatches': 0, 'ngames': 0})
        r['nmatches'] = s['nmatches']
        r['ngames'] = s['ngames']
        historical_list.append(r)

    # Pre-calculate rating differences (since it's ordered by -period_id, next item is the previous one)
    for i in range(len(historical_list) - 1):
        curr = historical_list[i]
        prev = historical_list[i+1]
        
        # Only show diffs if they are consecutive and same player
        if curr['prev_id'] == prev['id']:
            curr['rating_diff'] = curr['rating'] - prev['rating']
            curr['rating_diff_vp'] = (curr['rating'] + curr['rating_vp']) - (prev['rating'] + prev['rating_vp'])
            curr['rating_diff_vt'] = (curr['rating'] + curr['rating_vt']) - (prev['rating'] + prev['rating_vt'])
            curr['rating_diff_vz'] = (curr['rating'] + curr['rating_vz']) - (prev['rating'] + prev['rating_vz'])
            curr['has_prev'] = True

    base.update({
        'player': player,
        'historical': historical_list,
    })

    return render(request, 'historical.djhtml', base)


# }}}

# {{{ earnings view
@cache_page
def earnings(request, player_id):
    player = get_object_or_404(Player, id=player_id)
    base = base_ctx('Ranking', 'Earnings', request, context=player)

    year = get_param(request, 'year', 'all')

    # {{{ Gather data
    earnings = player.earnings_set
    if year != 'all':
        earnings = earnings.filter(event__latest__year=year)
    earnings = earnings.prefetch_related('event__earnings_set').order_by('-event__latest')
    totalearnings = earnings.aggregate(Sum('earnings'))['earnings__sum']

    years = range(2010, datetime.now().year + 1)

    def year_is_valid(y):
        return player.earnings_set.filter(event__latest__year=y).exists()

    valid_years = filter(year_is_valid, years)

    # Get placement range for each prize
    for e in earnings:
        placements = get_placements(e.event)
        for prize, rng in placements.items():
            if rng[0] <= e.placement <= rng[1]:
                e.rng = rng
    # }}}

    # {{{ Sum up earnings by currency
    currencies = {e.currency for e in earnings}
    by_currency = {cur: sum([e.origearnings for e in earnings if e.currency == cur]) for cur in currencies}
    if len(by_currency) == 1 and 'USD' in by_currency:
        by_currency = None
    # }}}

    base.update({
        'player': player,
        'earnings': earnings,
        'totalearnings': totalearnings,
        'by_currency': by_currency,
        'year': year,
        'valid_years': reversed(list(valid_years))
    })

    return render(request, 'player_earnings.djhtml', base)


# }}}


# {{{ Postable templates
TL_HISTORY_TEMPLATE = (
        "{resfor} {player_country_formatted} :{player_race}: " +
        "[url={url}/players/{pid}/]{player_tag}[/url]{date}.\n" +
        "\n" +
        "[b]{games}:[/b] {sc_percent:0<5}% ({sc_my}-{sc_op})\n" +
        "[b]{matches}:[/b] {msc_percent:0<5}% ({msc_my}-{msc_op})\n" +
        "\n" +
        "[b][big]{curform}:[/big][/b]\n" +
        "[indent]{form}\n" +
        "[b][big]{recentmatches}:[/big][/b]\n" +
        "{recent}\n" +
        "\n\n" +
        "{filters}:\n" +
        "[spoiler][code]" +
        "{opprace}{race}\n" +
        "{oppcountry}{country}\n" +
        "{matchformat}{bestof}\n" +
        "{onoff}{offline}\n" +
        "{version}{game}\n" +
        "[/code][/spoiler]\n" +
        "[small]{statslink}. " +
        "[url={url}/players/{pid}/results/?{get}]{link}[/url].[/small]"
)

TL_HISTORY_MATCH_TEMPLATE = (
    "[indent]"
    " {pla_country_formatted} :{pla_race}: "
    " {plaws}[url=http://aligulac.com/players/{pla_id}/]{pla_tag}[/url]{plawe}"
    " {pla_score:>2} – {plb_score:<2} "
    " {plb_country_formatted} :{plb_race}: "
    " {plbws}[url=http://aligulac.com/players/{plb_id}/]{plb_tag}[/url]{plbwe}"
)

# }}}
