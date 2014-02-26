import os
basedir = os.path.abspath(os.path.dirname(__file__))

DB_NAME = '/tmp/requests.db'
DEBUG = True
SECRET_KEY = 'longkeyinthefuture'
USERNAME = 'httpapi'
PASSWORD = 'allbutdefault'

HOST = '127.0.0.1'
PORT = 8080

RODSHOST = ''
RODSPORT = 80
RODSZONE = ''
