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


class IsFileException(StorageException):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)


class MalformedPathException(StorageException):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)


def read_stream_generator(file_handle, file_size,
                          ordered_range_list, read_func,
                          seek_func, close_func,
                          buffer_size=4194304):
    """Generate the bytestream.

    Default chunking is 4 MByte.

    Supports multirange request.
    (even unordened and if the ranges overlap)

    In case of no range requests, the whole file is read.

    With range requests, we seek the range, and then deliver
    the bytestream in buffer_size chunks. To stop at the end
    of the range, the make the last buffer smaller.
    This might become a performance issue, as we can have very
    small chunks. Also we deliver differently sized chunks to
    the frontend, and I'm not sure how they take it.

    The special values START and END represent the start and end
    of the file to allow for range requests that only specify
    one the two.

    In case of a multirange request, the delimiter shows when a new
    segment begins (by evaluating to True). It carries also
    information about the segment size.

    The output it yields are tuples of:
    (
     delimiter,       True if a segment starts with this chunk
     segment_start,   absolute position of the segment in the file
     segment_end,     absolute position of the end in the file
     segment_data     data in this chunk
    )
    """
    multipart = False
    delimiter = False
    if len(ordered_range_list) > 1:
        multipart = True

    if not ordered_range_list:
        while True:
            data = read_func(file_handle, buffer_size)
            if data == '':
                break
            yield delimiter, 0, file_size, data
    else:
        for start, end in ordered_range_list:
            if start == START:
                start = 0

            segment_start = start
            segment_end = end

            seek_func(file_handle, segment_start)

            if end == END:
                segment_end = file_size - 1

            # http expects the last byte included
            range_size = segment_end - segment_start + 1
            range_size_acc = 0
            range_buffer_size = buffer_size

            if multipart:
                delimiter = range_size

            while range_size_acc < range_size:
                if (range_size - range_size_acc) < range_buffer_size:
                    range_buffer_size = (range_size - range_size_acc)

                data = read_func(file_handle, range_buffer_size)
                if data == '':
                    break
                yield delimiter, segment_start, segment_end, data
                delimiter = False
                range_size_acc += range_buffer_size

    close_func(file_handle)
