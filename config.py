import os
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
#STORAGE = 'irods'
RODSHOST = 'localhost'
RODSPORT = 1247
RODSZONE = 'tempZone'

HOST = '127.0.0.1'
PORT = 8080

# these are not meant for eternity, we might
# come up with something better
STORAGE_HOST = HOST
STORAGE_PORT = PORT
REGISTERED_PREFIX = '/tmp/registered/'

HANDLE_URI = ''
HANDLE_USER = ''
HANDLE_PASS = ''

ACTIVATE_STORAGE_READ = True
ACTIVATE_STORAGE_WRITE = True
ACTIVATE_REGISTRATION = True
