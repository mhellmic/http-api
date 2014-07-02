import os
from eudat_http_api.epicclient import EpicClient

basedir = os.path.abspath(os.path.dirname(__file__))

SECRET_KEY = 'longkeyinthefuture'
USERNAME = 'httpapi'
PASSWORD = 'allbutdefault'

SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'http.db')
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

EPIC_URI = 'http://localhost:5000'
EPIC_USER = 'user'
EPIC_PASS = 'pass'
#usually equals EPIC_USER
EPIC_PREFIX = '666'

HANDLE_BASE_URI = EpicClient.HANDLE_BASE_URI
#for testing with: https://github.com/httpPrincess/fakedEpicServer
HANDLE_BASE_URI = 'http://localhost:5000'

# config for b2safe irods (could be different then "playground" irods?)
# # final destination of the files (local safe storage)
IRODS_SAFE_STORAGE = '/%s/safe/' % RODSZONE
# # where the replication commands are written
IRODS_SHARED_SPACE = '/%s/replicate/' % RODSZONE
# # in the process of replication you have to define the destination where the
# #  data will be stored (for test local zone is ok). HTTP does not write to
# # this location this is done by replication rules.
IRODS_REPLICATION_DESTINATION = '/%s/replicated/' % RODSZONE

HANDLE_URI = ''
HANDLE_USER = ''
HANDLE_PASS = ''

#STORAGE = 'irods'
STORAGE = 'local'

ACTIVATE_CDMI = True
CDMI_DOMAIN = 'cern.ch'

ACTIVATE_JSON = False

ACTIVATE_STORAGE_READ = True
ACTIVATE_STORAGE_WRITE = True
ACTIVATE_REGISTRATION = True
