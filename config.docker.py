import os

basedir = os.path.abspath(os.path.dirname(__file__))

############################
# STORAGE SETTINGS #
############################

############################
# STORAGE FRONTEND SETTINGS

ACTIVATE_STORAGE_READ = True
ACTIVATE_STORAGE_WRITE = True

# cdmi frontend settings
ACTIVATE_CDMI = True
CDMI_DOMAIN = 'foo.bar'
CDMI_ENTERPRISE_NUMBER = 12717

# json frontend settings
ACTIVATE_JSON = True

############################
# STORAGE BACKEND SETTINGS

STORAGE = 'local' 
if os.environ.has_key('IRODS_PORT_1247_TCP_ADDR'):
   STORAGE = 'irods'


HOST = '0.0.0.0'
PORT = 8080

# local storage settings
EXPORTEDPATHS = ['/tmp/']
USERS = {
    'testname': 'testpass'
}

# irods storage settings
RODSHOST = os.getenv('IRODS_PORT_1247_TCP_ADDR', 'localhost')
RODSPORT = int(os.getenv('IRODS_PORT_1247_TCP_PORT', '1247'))
RODSZONE = os.getenv('IRODS_ENV_ZONE','tempZone')


############################
# REGISTRATION SETTINGS #
############################

ACTIVATE_REGISTRATION = True

SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'http.db')
REQUESTS_PER_PAGE = 5

# the destination host for file registering requests.
# this should be an fqdn of the (or a) machine where the http-api
# storage runs on.
HTTP_ENDPOINT = 'http://localhost:8080'

# public scratch space path
SCRATCH_SPACE = '/tmp/http_server/scratch/'

if os.environ.has_key('IRODS_PORT_1247_TCP_ADDR'):
   SCRATCH_SPACE = '/%s/home/public/' % RODSZONE

# the space where registered files end up
REGISTERED_SPACE = '/tmp/http_server/registered/'
if os.environ.has_key('IRODS_PORT_1247_TCP_ADDR'):
    REGISTERED_SPACE = '/%s/registered/' % RODSZONE

############################
# IRODS-SPECIFIC REPLICATION SETTINGS

# # where the replication commands are written
IRODS_SHARED_SPACE = '/%s/replicate/' % RODSZONE
# # in the process of replication you have to define the destination where the
# # data will be stored (for test local zone is ok). HTTP does not write to
# # this location this is done by replication rules.
IRODS_REPLICATION_DESTINATION = '/%s/replicated/' % RODSZONE

############################
# HANDLE SETTINGS

EPIC_URI = 'http://%s:%s' % (os.getenv('EPIC_PORT_5000_TCP_ADDR', 'localhost'), os.getenv('EPIC_PORT_5000_TCP_PORT','5000'))
EPIC_USER = 'user'
EPIC_PASS = 'pass'
#usually equals EPIC_USER
EPIC_PREFIX = '666'
HANDLE_PREFIX = '666'

HANDLE_URI = EPIC_URI
