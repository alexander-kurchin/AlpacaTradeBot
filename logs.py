import os
from datetime import datetime

from config import parameters


def log_this(log_string, notime_flag=False):
    """ Simple logging to a text file / screen. """
    if parameters.getboolean('log to file'):
        if not os.path.exists('logs/'):
            os.mkdir('logs/')
        log = open(f'logs/{datetime.date(datetime.utcnow())}.log', 'a')
        log.write(f'\n{log_string}\n\n' if notime_flag else f'{str(datetime.utcnow())[:19]} | {log_string}\n')
        log.close()
    if parameters.getboolean('log to screen'):
        print(f'\n{log_string}\n\n' if notime_flag else f'{str(datetime.utcnow())[:19]} | {log_string}\n')
