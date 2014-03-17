import os
basedir = os.path.abspath(os.path.dirname(__file__))

DEBUG = False
SECRET_KEY = 'longkeyinthefuture'
USERNAME = 'httpapi'
PASSWORD = 'allbutdefault'

SQLALCHEMY_DATABASE_URI = 'sqlite:///'+os.path.join(basedir, 'http.db')
REQUESTS_PER_PAGE = 5

# only used by local storage, all request outside given path are prevented
BASE_PATH = "/tmp/"

RODSHOST = 'localhost'
RODSPORT = 1247
RODSZONE = 'tempZone'

HOST = '127.0.0.1'
PORT = 8080

STORAGE = 'irods'
# STORAGE = 'local'
