import os
basedir = os.path.abspath(os.path.dirname(__file__))

DB_NAME = '/tmp/requests.db'
DEBUG = True
SECRET_KEY = 'longkeyinthefuture'
USERNAME = 'httpapi'
PASSWORD = 'allbutdefault'

USE_IRODS_AUTHENTICATION = False

SQLALCHEMY_DATABASE_URI = 'sqlite:///'+os.path.join(basedir, 'http.db')

RODSHOST = 'localhost'
RODSPORT = 1247
RODSZONE = 'tempZone'

HOST = '127.0.0.1'
PORT = 8080