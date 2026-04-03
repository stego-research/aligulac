import json
import urllib.request
import urllib.error
from datetime import timedelta, date as dt_date
from decimal import Decimal

from django.core.cache import cache
from django.utils.translation import gettext_lazy as _

from aligulac import settings


# Class adapted from https://bitbucket.org/alquimista/currency

class ExchangeRates(object):

    def __init__(self, date):
        self._date = date
        self._data = self._loadjson(date)

    def _loadjson(self, date):
        date_str = self._date.strftime('%Y-%m-%d')
        cache_key = f'exchangerates:{date_str}'
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return cached_data

        url = 'https://openexchangerates.org/api/historical/' + date_str + '.json?app_id=' + settings.EXCHANGE_ID
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                content = response.read()
                data = json.loads(content.decode('utf-8'))
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
            return False
        except (json.JSONDecodeError, UnicodeDecodeError):
            return False
        except Exception:
            return False

        if not data or 'rates' not in data:
            return False

        # ccy use XBT instead
        try:
            data['rates']['XBT'] = data['rates']['BTC']
        except Exception:
            # Bitcoin transfer rates not available at this time.
            pass

        # Cache the results: 24 hours for current date, 30 days for historical.
        ttl = 86400 if self._date >= dt_date.today() else 2592000
        cache.set(cache_key, data, ttl)

        return data

    def _tobase(self, amount, currency):
        if not self._data or 'rates' not in self._data:
            raise RateNotFoundError(currency, self._date)
        return amount * Decimal(self.rates[currency])

    @property
    def rates(self):
        if not self._data:
            return {}
        return self._data['rates']

    def convert(self, amount, currencyfrom, currencyto='USD'):
        if currencyfrom not in self.rates:
            self.interpolate(currencyfrom)
        if currencyto not in self.rates:
            self.interpolate(currencyto)

        usd = self._tobase(amount, currencyto.upper())
        return usd / Decimal(self.rates[currencyfrom.upper()])

    def interpolate(self, currency):
        """
        Linearly interpolates the rate for `currency`
        by using the rates closest before and after the
        current date.
        """
        one_day = timedelta(days=1)

        after = self._date + one_day
        nafter = 1
        before = self._date - one_day
        nbefore = 1

        rate_after = None
        rate_before = None

        tries = 0
        while rate_after is None and tries < 20:
            e = ExchangeRates(after)
            if currency in e.rates:
                rate_after = e.rates[currency]
                break
            after += one_day
            nafter += 1
            tries += 1

        tries = 0
        while rate_before is None and tries < 20 and rate_after is not None:
            e = ExchangeRates(before)
            if currency in e.rates:
                rate_before = e.rates[currency]
                break
            before -= one_day
            nbefore += 1
            tries += 1

        if rate_after is None or rate_after is None:
            raise RateNotFoundError(currency, self._date)

        coeff = (rate_after - rate_before) / (nafter + nbefore)
        self.rates[currency] = rate_before + coeff * nbefore


class RateNotFoundError(Exception):
    def __init__(self, currency, date, *args, **kwargs):
        super().__init__(
            _("Exchange rate not found for currency %(code)s on %(date)s") % {
                'code': currency,
                'date': date,
            },
            *args, **kwargs
        )
