import tempfile


class Config(object):
    DEBUG = False
    TESTING = True

    HOST = '127.0.0.1'
    PORT = 5000

    CDMI_DOMAIN = 'cern.ch'

    DB_FD, DB_FILENAME = tempfile.mkstemp()
    SQLALCHEMY_DATABASE_URI = '%s%s' % ('sqlite:///', DB_FILENAME)
    REQUESTS_PER_PAGE = 5


class MockConfig(Config):
    STORAGE = 'mock'


class LocalConfig(Config):
    ACTIVATE_STORAGE_READ = True
    ACTIVATE_STORAGE_WRITE = True
    ACTIVATE_REGISTRATION = True

    STORAGE = 'local'
    EXPORTEDPATHS = ['/tmp/']
    USERS = {
        'testname': 'testpass'
    }


class IrodsConfig(Config):
    ACTIVATE_STORAGE_READ = True
    ACTIVATE_STORAGE_WRITE = True
    ACTIVATE_REGISTRATION = True

    STORAGE = 'irods'
    RODSHOST = 'localhost'
    RODSPORT = 1247
    RODSZONE = 'tempZone'
