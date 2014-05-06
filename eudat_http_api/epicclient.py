from requests import get, post
import json
import requests


def create_uri(base_uri, prefix, suffix=''):
    """creates handle uri from provided parameters

    @param base_uri: base epic service uri
    @param prefix: handle prefix
    @param suffix: handle suffix
    @return: proper http url
    """
    return '/'.join([base_uri, prefix, suffix])


def convert_to_handle(location, checksum=0):
    """creates handle record in json format

    @param location: URL value of the handle record
    @param checksum: checksum value of the handle record
    @return: handle record in json format (ready to submit)
    """
    handle_content = [{'type': 'URL', 'parsed_data': location}]

    if checksum:
        handle_content.append({'type': 'CHECKSUM', 'parsed_data': checksum})

    return json.dumps(handle_content)


class EpicClient(object):
    """Client for communication with epic pid service."""

    def __init__(self, base_uri, credentials, debug=False):

        """Initialize object with connection parameters."""
        self.accept_format = 'application/json'
        self.debug = debug
        self.credentials = credentials
        self.base_uri = base_uri


    def _debug_msg(self, method, msg):
        """Internal: Print a debug message if debug is enabled."""
        #fixme: should be using logger
        if self.debug:
            print '[ %s ] %s' % (method, msg)

    def retrieve_handle(self, prefix, suffix=''):
        """Retrieve a handle from the PID service.
        Parameters:
        prefix: URI to the resource, or the prefix if suffix is not ''.
        suffix: The suffix of the handle. Default: ''.
        Returns the content of the handle in JSON, None on error.

        """
        headers = {'Accept': self.accept_format}

        response = get(url=create_uri(base_uri=self.base_uri, prefix=prefix,
                                      suffix=suffix),
                       headers=headers,
                       auth=self.credentials,
                       allow_redirects=False)

        if response is None:
            return None

        if response.status_code != requests.codes.ok:
            self._debug_msg('retrieveHandle',
                            'Response status: %s' % response.status_code)
            return None

        return response.content

    def create_new(self, prefix, location, checksum):
        """create new handle

        utilizes automatic pid generation function of the epic api

        @param prefix: prefix in which the new handle should be placed
        @param location: will be included in handle record as URL
        @param checksum: checksum of the data object created
        @return: location of the handle
        """
        headers = {'Content-Type': 'application/json'}
        new_handle_json = convert_to_handle(location, checksum)
        response = post(url=create_uri(base_uri=self.base_uri,
                                       prefix=prefix, suffix=''),
                        headers=headers,
                        data=new_handle_json,
                        auth=self.credentials)

        if response is None:
            return None

        if response.status_code != requests.codes.created:
            self._debug_msg('createNew',
                            'Not Created: Response status %s' %
                            response.status_code)
            return None

        return response.headers['Location']
