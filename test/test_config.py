import tempfile
from eudat_http_api.epicclient import EpicClient

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

EPIC_URI = 'http://localhost:5000'
EPIC_USER = 'user'
EPIC_PASS = 'pass'
EPIC_PREFIX = '666'

HANDLE_BASE_URI = EpicClient.HANDLE_BASE_URI
HANDLE_BASE_URI = 'http://localhost:5000'

RODSHOST = 'localhost'
RODSPORT = 1247
RODSZONE = 'tempZone'

# # final destination of the files (local safe storage)
IRODS_SAFE_STORAGE = '/%s/safe/' % RODSZONE
# # where the replication commands are written
IRODS_SHARED_SPACE = '/%s/replicate/' % RODSZONE
# # in the process of replication you have to define the destination where the
# #  data will be stored (for test local zone is ok). HTTP does not write to
# # this location this is done by replication rules.
IRODS_REPLICATION_DESTINATION = '/%s/replicated/' % RODSZONE