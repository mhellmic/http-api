DEBUG = True
SECRET_KEY = 'longkeyinthefuture'
USERNAME = 'httpapi'
PASSWORD = 'allbutdefault'

USE_IRODS_AUTHENTICATION = True

SQLALCHEMY_DATABASE_URI = 'sqlite:///Users/mhellmic/repo/http-api/http.db'
REQUESTS_PER_PAGE = 5

RODSHOST = 'irods2.cern.ch'
RODSPORT = 1247
RODSZONE = 'cern'

HOST = '127.0.0.1'
PORT = 5000

STORAGE = 'irods'
