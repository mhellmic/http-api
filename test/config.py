import tempfile


class Config(object):
    DEBUG = False
    # do NOT set TESTING True, it will disable flask-login
    # all testing does is to enable better error reports,
    # so enable it if you see something suspicious :)
    TESTING = False

    HOST = '127.0.0.1'
    PORT = 5000

    CDMI_DOMAIN = 'cern.ch'
    CDMI_ENTERPRISE_NUMBER = 20456

    SECRET_KEY = 'vroneneravinjvnaov;d'

    DB_FD, DB_FILENAME = tempfile.mkstemp()
    SQLALCHEMY_DATABASE_URI = '%s%s' % ('sqlite:///', DB_FILENAME)
    REQUESTS_PER_PAGE = 5


class MockConfig(Config):
    STORAGE = 'mock'


class LocalConfig(Config):
    ACTIVATE_STORAGE_READ = True
    ACTIVATE_STORAGE_WRITE = True
    ACTIVATE_REGISTRATION = True
    ACTIVATE_CDMI = True

    STORAGE = 'local'
    EXPORTEDPATHS = ['/tmp/']
    USERS = {
        'testname': 'testpass'
    }


class IrodsConfig(Config):
    ACTIVATE_STORAGE_READ = True
    ACTIVATE_STORAGE_WRITE = True
    ACTIVATE_REGISTRATION = True
    ACTIVATE_CDMI = True

    STORAGE = 'irods'
    RODSHOST = 'localhost'
    RODSPORT = 1247
    RODSZONE = 'tempZone'
