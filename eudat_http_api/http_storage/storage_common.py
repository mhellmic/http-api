# -*- coding: utf-8 -*-

from functools import partial

START = 'file-start'
END = 'file-end'
BACKWARDS = 'file-back'

DIR = 'dir'
FILE = 'file'

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


def adjust_range_size(x, y, file_size):
    '''Adjust from range representation of the CDMI layer.

    This adjustments translates all symbolic values into
    offsets in the file to read. It also makes the ranges
    sortable for optimal access.

    The CDMI layer does not know about the filesize, so
    we translate the constants START and END into
    file_size and 0.
    Because it doesn't know the filesize, it also cannot
    calculate the offsets for reading the last part of a file.
    It shows this case by providing the segment length as x
    and y as BACKWARDS, which we convert into a segment
    (filesize,  filesize - x) for acual access.

    The behaviour is according to:
    http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html
    14.35.1 Byte Ranges
    '''
    # this case has to go first, as all constants eval > file_size
    if y == BACKWARDS:  # get the last part of the file
        y = file_size
        x = file_size - x
        if x < 0:
            x = 0
    if y > file_size or y == END:
        y = file_size
    if x == START:
        x = 0
    return (x, y)


def get_range_size(x, y, file_size):
    '''Get the range sizes.

    The only special case handled here is the discount of
    1 for values == file_size. This is because we have to
    adjust all other range sizes to include the last byte,
    which is included for y == file_size.
    '''
    if y == file_size:
        y -= 1  # because we adjust all other sizes below
    return y - x + 1  # http expects the last byte included


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
        for data in iter(partial(read_func, file_handle, buffer_size), ''):
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
