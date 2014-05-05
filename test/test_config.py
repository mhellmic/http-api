import tempfile

DEBUG = True
TESTING = True

SECRET_KEY = 'longkeyinthefuture'
USERNAME = 'httpapi'
PASSWORD = 'allbutdefault'

DB_FILENAME = tempfile.mktemp()
SQLALCHEMY_DATABASE_URI = 'sqlite:///'+DB_FILENAME
REQUESTS_PER_PAGE = 5

# local storage settings
STORAGE = 'local'
# only used by local storage, all request outside given path are prevented
EXPORTEDPATHS = ['/tmp/']
USERS = {
        'testname': 'testpass'
}

HOST = '127.0.0.1'
PORT = 8080

HANDLE_URI = ''
HANDLE_USER = ''
HANDLE_PASS = ''