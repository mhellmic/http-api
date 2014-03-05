# -*- coding: utf-8 -*-

START = 'file-start'
END = 'file-end'

MULTI_DELIM = '@DELMI@'


class StorageObject(object):
    name = None
    path = None
    metadata = None
    objtype = None

    def __init__(self):
        self.name = ''
        self.path = ''
        self.metadata = {}


class StorageDir(StorageObject):
    objtype = 'dir'

    def __init__(self, name, path, meta={}):
        super(StorageDir, self).__init__()
        self.name = name
        self.path = path
        self.meta = meta


class StorageFile(StorageObject):
    objtype = 'file'
    size = None
    resc = None

    def __init__(self, name, path, meta={}, size=0):
        super(StorageFile, self).__init__()
        self.name = name
        self.path = path
        self.meta = meta
        self.size = size


class StorageException(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)


class InternalException(StorageException):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)


class NotFoundException(StorageException):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)


class NotAuthorizedException(StorageException):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)


class ConflictException(StorageException):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)


class IsDirException(StorageException):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)
