import alpaca_trade_api as tradeapi
from datetime import datetime, timedelta

from config import parameters
from database import (update_database, delete_from_database, insert_profit, get_list_of_orders,
                      get_buy_order_id, get_balance, get_todays_profit, get_total_profit)
from logs import log_this
from orders import make_sell_order, cancel_order_id


def check_orders(api):
    """ Iterates over all orders and checks them. """
    log_this('Checking buy orders starts...')
    list_buy_orders = get_list_of_orders('buy_orders')
    for order_id in list_buy_orders:
        check_buy_order(api, order_id)
    log_this('Checking sell orders starts...')
    list_sell_orders = get_list_of_orders('sell_orders')
    for order_id in list_sell_orders:
        check_sell_order(api, order_id)
    log_this(f'Today\'s profit: ${get_todays_profit()}')
    log_this(f'Total profit: ${get_total_profit()}')


def check_buy_order(api, order_id):
    """ Checks a fulfillment of buy order. """
    try:
        order = api.get_order(order_id)
    except tradeapi.rest.APIError as apierror:
        log_this(f'Something went wrong with API while getting buy order {order_id}!')
        log_this(str(apierror), notime_flag=True)
    else:
        order_time = datetime.fromisoformat(str(datetime.utcnow()) + '+00:00') \
                     - datetime.fromisoformat(str(order.created_at))
        time_limit = timedelta(minutes=parameters.getint('buy-order checking time'))
        if order.status == 'filled':
            log_this(f'Buy-Order {order_id} is filled.')
            log_this(f'Making Limit Sell-Order...')
            target_percent = 1 + parameters.getfloat('sell target percent') / 100
            target_price = round(float(order.limit_price) * target_percent, 2)
            make_sell_order(api, order.symbol, 'limit', order.qty, order_id, target_price)
            delete_from_database(order.side, order_id)
        elif order.status == 'canceled':
            if order.filled_qty == 0:
                delete_from_database(order.side, order_id)
            else:
                make_sell_order(api, order.symbol, 'market', order.filled_qty, order_id)
                delete_from_database(order.side, order_id)
        elif order_time >= time_limit:
            if order.status == 'partially_filled':
                if order_time < time_limit * 2:
                    log_this(f'Buy-Order {order_id} is partially filled. Let\'s wait.')
                    update_database(order.side, order_id, str(datetime.utcnow()))
                else:
                    cancel_order_id(api, order_id)
                    make_sell_order(api, order.symbol, 'market', order.filled_qty, order_id)
                    delete_from_database(order.side, order_id)
            elif order.status == 'new':
                cancel_order_id(api, order_id)
                delete_from_database(order.side, order_id)
            else:
                log_this(f'Buy-Order {order_id} has unexpected order status: {order.status}. Please check.')


def check_sell_order(api, order_id):
    """ Checks a fulfillment of sell order. """
    try:
        order = api.get_order(order_id)
    except tradeapi.rest.APIError as apierror:
        log_this(f'Something went wrong with API while getting sell order {order_id}!')
        log_this(str(apierror), notime_flag=True)
    else:
        order_type = order.type
        order_time = datetime.fromisoformat(str(datetime.utcnow()) + '+00:00') \
                     - datetime.fromisoformat(str(order.created_at))
        time_limit = timedelta(minutes=parameters.getint('sell-order lifetime'))
        buy_order_id = get_buy_order_id(order_id)
        if order.status == 'filled':
            log_this(f'The {order_type} sell order {order_id} is filled.')
            take_profit(api, buy_order_id, order_id)
        elif order_type != 'market' and order_time >= time_limit:
            if order.status == 'partially_filled':
                log_this(f'The {order_type} sell order {order_id} is partially filled.')
                cancel_order_id(api, order_id)
                make_sell_order(api, order.symbol, 'market', int(order.qty) - int(order.filled_qty), buy_order_id)
                take_profit(api, buy_order_id, order_id)
            elif order.status == 'new':
                log_this(f'The {order_type} sell order {order_id} is not filled yet.')
                cancel_order_id(api, order_id)
                delete_from_database(order.side, order_id)
                make_sell_order(api, order.symbol, 'market', order.qty, buy_order_id)
            else:
                log_this(f'Sell-Order {order_id} has unexpected order status: {order.status}. Please check.')


def take_profit(api, buy_order_id, sell_order_id):
    """ Calculates and saves balances and profit. """
    try:
        buy_order = api.get_order(buy_order_id)
        sell_order = api.get_order(sell_order_id)
    except tradeapi.rest.APIError as apierror:
        log_this(f'Something went wrong with API while getting orders!\n{buy_order_id}\n{sell_order_id}')
        log_this(str(apierror), notime_flag=True)
    else:
        total_balance = get_balance('total')
        active_balance = get_balance('active')
        time_now = str(datetime.utcnow())[:19]
        symbol = buy_order.symbol if buy_order.symbol == sell_order.symbol else 'Mistake'
        quantity = float(sell_order.filled_qty)
        buy_price = float(buy_order.limit_price)
        try:
            sell_price = float(sell_order.filled_avg_price)
        except TypeError:
            sell_price = float(sell_order.limit_price)
        finally:
            buy_amount = buy_price * quantity
            sell_amount = sell_price * quantity
            profit = sell_amount - buy_amount
            total_balance += sell_amount
            active_balance += sell_amount if parameters.getboolean('plowback') else min(buy_amount, sell_amount)
            insert_profit(total_balance, active_balance, time_now, symbol, profit, buy_order_id, sell_order_id)
            delete_from_database(sell_order.side, sell_order_id)
