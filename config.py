import os
from eudat_http_api.epicclient import EpicClient

basedir = os.path.abspath(os.path.dirname(__file__))

SECRET_KEY = 'longkeyinthefuture'
USERNAME = 'httpapi'
PASSWORD = 'allbutdefault'

SQLALCHEMY_DATABASE_URI = 'sqlite:///'+os.path.join(basedir, 'http.db')
REQUESTS_PER_PAGE = 5

# local storage settings
STORAGE = 'local'
# only used by local storage, all request outside given path are prevented
EXPORTEDPATHS = ['/tmp/']
USERS = {
        'testname': 'testpass'
}

# irods storage settings
STORAGE = 'irods'
RODSHOST = 'localhost'
RODSPORT = 1247
RODSZONE = 'tempZone'

HOST = '127.0.0.1'
PORT = 8080

HANDLE_URI = ''
HANDLE_USER = ''
HANDLE_PASS = ''

HANDLE_BASE_URI = EpicClient.HANDLE_BASE_URI
HANDLE_BASE_URI = 'http://localhost:5000'
