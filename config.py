import configparser


config = configparser.ConfigParser()
config.read('settings.ini')
api_keys = config['api keys']
parameters = config['parameters']
