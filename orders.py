import alpaca_trade_api as tradeapi

from logs import log_this
from database import insert_into_database


def make_limit_buy_order(api, symbol, quantity, price):
    """ Makes an limit buy order via API. """
    try:
        order = api.submit_order(symbol=symbol, side='buy', type='limit',
                                 qty=str(quantity), time_in_force='day', limit_price=price)
    except tradeapi.rest.APIError as apierror:
        log_this(f'Something went wrong with the submission of a limit buy order! Please check terminal! '
                 f'({symbol}, {quantity}, {price})')
        log_this(str(apierror), notime_flag=True)
    else:
        log_this(f'Limit Buy-Order {order.id} is submitted.')
        insert_into_database(order.id, order.symbol)


def make_sell_order(api, symbol, order_type, quantity, buy_order_id, limit_price=None):
    """ Makes an sell order via API. """
    try:
        if limit_price:
            order = api.submit_order(symbol=symbol, side='sell', type=order_type,
                             qty=quantity, time_in_force='gtc', limit_price=limit_price)
        else:
            order = api.submit_order(symbol=symbol, side='sell', type=order_type, qty=quantity, time_in_force='gtc')
    except tradeapi.rest.APIError as apierror:
        log_this(f'Something went wrong with the submission of a {order_type} sell order! Please check terminal! '
                 f'({symbol}, {quantity}, {limit_price})')
        log_this(str(apierror), notime_flag=True)
    else:
        log_this(f'The {order_type} sell-order {order.id} is submitted.')
        insert_into_database(order.id, order.symbol, buy_order_id)


def cancel_order_id(api, order_id):
    """ Cancels an order via API. """
    try:
        api.cancel_order(order_id)
    except tradeapi.rest.APIError as apierror:
        log_this(f'Something went wrong when canceling an order {order_id}! Please check terminal!')
        log_this(str(apierror), notime_flag=True)
    else:
        log_this(f'Order {order_id} is canceled.')
