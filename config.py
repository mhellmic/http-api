import os

basedir = os.path.abspath(os.path.dirname(__file__))

SECRET_KEY = 'vroneneravinjvnaov;d'

############################
# STORAGE SETTINGS         #
############################

############################
# STORAGE FRONTEND SETTINGS

ACTIVATE_STORAGE_READ = True
ACTIVATE_STORAGE_WRITE = True

# cdmi frontend settings
ACTIVATE_CDMI = True
CDMI_DOMAIN = 'cern.ch'
CDMI_ENTERPRISE_NUMBER = 20456

# json frontend settings
ACTIVATE_JSON = False

############################
# STORAGE BACKEND SETTINGS

STORAGE = 'dmlite'  # local, irods, dmlite
# the network interface that the storage should be bound to
# use 127.0.0.1 for only local access, 0.0.0.0 for unrestricted
HOST = '127.0.0.1'
PORT = 8080

# local storage settings
EXPORTEDPATHS = ['/tmp/']
USERS = {
    'testname': 'testpass'
}

# irods storage settings
RODSHOST = 'localhost'
RODSPORT = 1247
RODSZONE = 'tempZone'

# dmlite storage settings
## none for now

############################
# REGISTRATION SETTINGS    #
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

# the space where registered files end up
REGISTERED_SPACE = '/tmp/http_server/registered/'

############################
# IRODS-SPECIFIC REPLICATION SETTINGS

# # where the replication commands are written
IRODS_SHARED_SPACE = '/%s/replicate/' % RODSZONE
# # in the process of replication you have to define the destination where the
# #  data will be stored (for test local zone is ok). HTTP does not write to
# # this location this is done by replication rules.
IRODS_REPLICATION_DESTINATION = '/%s/replicated/' % RODSZONE

############################
# HANDLE SETTINGS

#for testing with: https://github.com/httpPrincess/fakedEpicServer
HANDLE_URI = 'http://localhost:5000'
HANDLE_USER = 'user'
HANDLE_PASS = 'pass'
HANDLE_PREFIX = '666'

# this is where handles are written to
EPIC_URI = 'http://localhost:5000'
EPIC_USER = 'user'
EPIC_PASS = 'pass'
