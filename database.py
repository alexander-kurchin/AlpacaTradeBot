import sqlite3
import os
from datetime import datetime, timedelta

from config import parameters
from logs import log_this


def check_database_existence():
    """ Creating a new database if not exist. """
    if not os.path.exists('data.db'):
        try:
            conn = sqlite3.connect('data.db')
            cur = conn.cursor()
            script = '''CREATE TABLE "buy_orders" ( "id"	TEXT NOT NULL UNIQUE,
                                                    "symbol"	TEXT NOT NULL,
                                                    "checked_at"	TEXT,
                                                    PRIMARY KEY("id")
                                                    );
                        CREATE TABLE "sell_orders" ("id"	TEXT NOT NULL UNIQUE,
                                                    "symbol"	TEXT NOT NULL,
                                                    "buy_order_id"	TEXT,
                                                    PRIMARY KEY("id")
                                                    );
                        CREATE TABLE "profits" ("id"	INTEGER NOT NULL UNIQUE,
                                                "total_balance"	REAL,
                                                "active_balance"	REAL,
                                                "time"	TEXT NOT NULL,
                                                "symbol"	TEXT NOT NULL,
                                                "profit"	REAL NOT NULL,
                                                "buy_order_id"	TEXT NOT NULL,
                                                "sell_order_id"	TEXT NOT NULL,
                                                PRIMARY KEY("id" AUTOINCREMENT)
                                                );'''
            cur.executescript(script)
            conn.commit()
            conn.close()
            time_now = str(datetime.utcnow())[:19]
            insert_profit(parameters.getfloat('initial funds'), parameters.getfloat('initial funds'),
                          time_now, 'None', 0, 'None', 'None', nolog_flag=True)
        except:
            log_this('Something went wrong while creating the new database!')


def insert_into_database(order_id, symbol, buy_order_id=None):
    """ Adding a new order into database. """
    check_database_existence()
    try:
        conn = sqlite3.connect('data.db')
        cur = conn.cursor()
        if buy_order_id:
            table = "sell_orders"
            heads = "id, symbol, buy_order_id"
            values = f"'{order_id}', '{symbol}', '{buy_order_id}'"
        else:
            table = "buy_orders"
            heads = "id, symbol"
            values = f"'{order_id}', '{symbol}'"
        cur.execute(f"INSERT INTO {table} ({heads}) VALUES ({values})")
        conn.commit()
        conn.close()
        log_this(f'Database: Order {order_id} has been inserted into the {table} table.')
    except:
        log_this(f'Something went wrong while inserting into the database! ({order_id}, {symbol}, {buy_order_id})')


def update_database(side, order_id, check_time):
    """ Adding a checked_at into order record. """
    check_database_existence()
    try:
        conn = sqlite3.connect('data.db')
        cur = conn.cursor()
        cur.execute(f"UPDATE {side}_orders SET checked_at = '{check_time}' WHERE id='{order_id}'")
        conn.commit()
        conn.close()
    except:
        log_this(f'Something went wrong while updating the database! ({side}_orders, {order_id}, {check_time})')


def delete_from_database(side, order_id):
    """ Deleting an order from database. """
    check_database_existence()
    try:
        conn = sqlite3.connect('data.db')
        cur = conn.cursor()
        cur.execute(f"DELETE FROM {side}_orders WHERE id='{order_id}'")
        conn.commit()
        conn.close()
        log_this(f'Database: Order {order_id} has been deleted from the {side}_orders table.')
    except:
        log_this(f'Something went wrong while deleting from the database! ({side}_orders, {order_id})')


def get_buy_order_id(order_id):
    """ Getting buy_order_id from sell order record. """
    check_database_existence()
    try:
        conn = sqlite3.connect('data.db')
        cur = conn.cursor()
        cur.execute(f"SELECT buy_order_id FROM sell_orders WHERE id='{order_id}'")
        buy_order_id = cur.fetchone()[0]
        conn.close()
        return buy_order_id
    except:
        log_this('Something went wrong while getting buy_order_id from the database!')
        return 'None'


def get_list_of_orders(table):
    """ Getting list of orders id from the table. """
    check_database_existence()
    try:
        conn = sqlite3.connect('data.db')
        cur = conn.cursor()
        cur.execute(f"SELECT id FROM {table}")
        list_of_orders = list()
        for order_id in cur.fetchall():
            list_of_orders.append(order_id[0])
        conn.close()
        return list_of_orders
    except:
        log_this('Something went wrong while getting list of orders from the database!')
        return []


def insert_profit(total_balance, active_balance, time, symbol, profit,
                  buy_order_id, sell_order_id, nolog_flag=False):
    """ Adding a new profit info into database. """
    check_database_existence()
    try:
        conn = sqlite3.connect('data.db')
        cur = conn.cursor()
        heads = 'total_balance, active_balance, time, symbol, profit, buy_order_id, sell_order_id'
        values = (f"{total_balance}, {active_balance}, '{time}', '{symbol}', "
                  f"{profit}, '{buy_order_id}', '{sell_order_id}'")
        cur.execute(f"INSERT INTO profits ({heads}) VALUES ({values})")
        conn.commit()
        conn.close()
        if not nolog_flag:
            log_this(f'Database: Profit ${profit} by {symbol} has been inserted into the table.')
    except:
        log_this(f'Something went wrong while inserting into the database! '
                 f'({total_balance}, {active_balance}, {time}, {symbol}, '
                 f'{profit}, {buy_order_id}, {sell_order_id})')


def get_balance(prefix):
    """ Getting current balance. """
    check_database_existence()
    try:
        conn = sqlite3.connect('data.db')
        cur = conn.cursor()
        cur.execute(f"SELECT {prefix}_balance FROM profits ORDER BY id DESC")
        balance = cur.fetchone()[0]
        conn.close()
        return balance
    except:
        log_this(f'Something went wrong while getting {prefix}_balance from the database!')
        return 0


def get_total_profit():
    """ Getting total profit. """
    check_database_existence()
    try:
        conn = sqlite3.connect('data.db')
        cur = conn.cursor()
        cur.execute(f"SELECT SUM(profit) FROM profits")
        total_profit = cur.fetchone()[0]
        conn.close()
        return round(total_profit, 2)
    except:
        log_this('Something went wrong while getting total profit from the database!')
        return 0


def get_todays_profit():
    """ Getting today's profit. """
    check_database_existence()
    try:
        today = str(datetime.date(datetime.utcnow()))
        tomorrow = str(datetime.date(datetime.utcnow() + timedelta(days=1)))
        conn = sqlite3.connect('data.db')
        cur = conn.cursor()
        cur.execute(f"SELECT SUM(profit) FROM profits WHERE time>'{today}' AND time<'{tomorrow}'")
        todays_profit = cur.fetchone()[0]
        conn.close()
        return round(todays_profit, 2)
    except:
        log_this('Something went wrong while getting total profit from the database!')
        return 0


def get_symbol_count(symbol, table):
    """ Getting count of orders with symbol from the table. """
    check_database_existence()
    try:
        conn = sqlite3.connect('data.db')
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(symbol) FROM {table} WHERE symbol='{symbol}'")
        count = cur.fetchone()[0]
        conn.close()
        return count
    except:
        log_this(f'Something went wrong while count of orders with {symbol} from the database!')
        return 0
