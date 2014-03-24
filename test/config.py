import tempfile


class Config(object):
    DEBUG = True
    TESTING = True

    HOST = '127.0.0.1'
    PORT = 5000

    DB_FD, DB_FILENAME = tempfile.mkstemp()
    SQLALCHEMY_DATABASE_URI = '%s%s' % ('sqlite:///', DB_FILENAME)
    REQUESTS_PER_PAGE = 5


class MockConfig(Config):
    STORAGE = 'mock'


class LocalConfig(Config):
    STORAGE = 'local'
    BASE_PATH = ''
    USERS = {
        'testname': 'testpass'
    }


class IrodsConfig(Config):
    STORAGE = 'irods'
    RODSHOST = 'localhost'
    RODSPORT = 1247
    RODSZONE = 'tempZone'