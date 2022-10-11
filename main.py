import os
import alpaca_trade_api as tradeapi
from datetime import datetime, timedelta

from config import parameters, api_keys
from logs import log_this
from orders import make_limit_buy_order
from orders_checks import check_orders
from database import get_balance, insert_profit, get_symbol_count


API_KEY = api_keys.get('api key')
API_SECRET = api_keys.get('api secret')
APCA_API_BASE_URL = 'https://{}api.alpaca.markets'.format('paper-' if parameters.getboolean('sandbox mode') else '')
SYMBOLS_FILE = 'symbols.txt'


def run():
    """ Main function. """
    log_this('Script is running', notime_flag=True)
    try:
        api = tradeapi.REST(API_KEY, API_SECRET, APCA_API_BASE_URL, api_version='v2')
        clock = api.get_clock()
    except tradeapi.rest.APIError as apierror:
        log_this('Something went wrong with API while connecting!')
        log_this(str(apierror), notime_flag=True)
    else:
        if not clock.is_open:
            log_this('The market is closed.')
        else:
            log_this('The market is open.')
            check_symbols_file(api)
            with open(SYMBOLS_FILE, 'r') as symbols:
                for line in symbols.readlines():
                    if is_hourly_limitation_not_ok(api):
                        log_this('Hourly limitation ({}) is reached.'.format(parameters.getint('hourly limitation')))
                        break
                    symbol = line[:-1]
                    if is_symbolic_limitation_ok(symbol):
                        log_this(f'Checking {symbol}...')
                        is_it_good, price = currency_checking(api, symbol)
                        if is_it_good:
                            log_this(f'{symbol} has passed all checks.')
                            buy_it(api, symbol, price)
                        else:
                            log_this(f'{symbol} hasn\'t passed all checks.')
            check_orders(api)


def buy_it(api, symbol, price):
    """ Buys currency if enough money. """
    total_balance = get_balance('total')
    active_balance = get_balance('active')
    if active_balance > price:
        log_this(f'Making Limit Buy-Order...')
        quantity = (min(active_balance, parameters.getfloat('maximal order volume')) / price) // 1
        make_limit_buy_order(api, symbol, quantity, price)
        total_balance -= quantity * price
        active_balance -= quantity * price
        time_now = str(datetime.utcnow())[:19]
        insert_profit(total_balance, active_balance, time_now,
                      symbol, 0, 'None', 'None', nolog_flag=True)
    else:
        log_this('But not enough money.')


def currency_checking(api, symbol):
    """ Checks the currency for compliance with the conditions. """
    try:
        barset = api.get_barset(symbol, 'day', limit=2)
    except tradeapi.rest.APIError as apierror:
        log_this(f'Something went wrong with API while getting bars for {symbol}!')
        log_this(str(apierror), notime_flag=True)
        return False, 0
    else:
        try:
            yesterday_bar = barset[symbol][0]
            today_bar = barset[symbol][1]
        except IndexError:
            return False, 0
        else:
            if datetime.date(datetime.fromtimestamp(today_bar._raw['t'])) != datetime.date(datetime.utcnow()):
                return False, 0
            log_this(barset.df, notime_flag=True)
            if yesterday_bar.v + today_bar.v < 2 * parameters.getfloat('least trade volume'):
                log_this(f'{symbol} has not enough volume.')
            else:
                log_this(f'{symbol} has enough volume.')
                if today_bar.c / today_bar.l > parameters.getfloat('current-lowest gap'):
                    log_this(f'But {symbol} has not the lowest point for today.')
                else:
                    log_this(f'{symbol} has the lowest point for today.')
                    current_price = today_bar.c
                    target_percent = 1 + parameters.getfloat('check target percent')/100
                    target_price = round(current_price * target_percent, 2)
                    if not today_bar.l <= target_price <= today_bar.h:
                        log_this(f'But target ${target_price} hasn\'t been hit today.')
                    else:
                        log_this(f'And target ${target_price} has been hit today.')
                        return True, current_price
            return False, 0


def is_hourly_limitation_not_ok(api):
    """ Checks hourly limitation of buy orders. """
    count = 0
    now = datetime.utcnow()
    try:
        orders = api.list_orders(after=(now - timedelta(hours=1)), limit=500, status='all')
    except tradeapi.rest.APIError as apierror:
        log_this('Something went wrong with API while checking hourly limitation!')
        log_this(str(apierror), notime_flag=True)
        return True
    else:
        for order in orders:
            if order.side == 'buy':
                count += 1
    return False if count < parameters.getint('hourly limitation') else True


def is_symbolic_limitation_ok(symbol):
    """ Checks symbolic limitation. """
    count = get_symbol_count(symbol, 'buy_orders') + get_symbol_count(symbol, 'sell_orders')
    return True if count < parameters.getint('symbolic limitation') else False


def check_symbols_file(api):
    """ Compiles a list of traded symbols if it doesn't exist. """
    if not os.path.exists(SYMBOLS_FILE):
        log_this(f'{SYMBOLS_FILE} doesn\'t exist. Making list of symbols...')
        symbols_file = open(SYMBOLS_FILE, 'w')
        assets_list = [asset.symbol + '\n' for asset in api.list_assets() if asset.tradable]
        symbols_file.writelines(assets_list)
        symbols_file.close()
        log_this(f'{SYMBOLS_FILE} ready.')


if __name__ == '__main__':
    run()
