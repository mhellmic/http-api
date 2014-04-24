from requests import get, post, put, delete
import json


def create_uri(base_uri, prefix, suffix=''):
    separator = '/'
    if base_uri[-1] == '/':
        separator = ''

    uri = base_uri + separator + prefix
    if uri[-1] != '/':
        uri += '/'
    if suffix != '':
        uri += suffix
    return uri


class HttpClient():
    """http client for the communication"""

    def __init__(self, base_uri, credentials):
        self.credentials = credentials
        self.base_uri = base_uri

    def get(self, prefix, suffix, *args, **kwargs):
        uri = create_uri(self.base_uri, prefix=prefix, suffix=suffix)
        kwargs['auth'] = self.credentials
        try:
            return get(url=uri, *args, **kwargs)
        except Exception as e:
            self._debug_msg('An Exception occurred during request GET %s\n %s' % (uri, e))
            return None

    def put(self, prefix, suffix, *args, **kwargs):
        uri = create_uri(self.base_uri, prefix=prefix, suffix=suffix)
        kwargs['auth'] = self.credentials
        try:
            return put(url=uri, *args, **kwargs)
        except Exception as e:
            self._debug_msg('An Exception occurred during request PUT %s\n %s' % (uri, e))
            return None

    def delete(self, prefix, suffix, *args, **kwargs):
        uri = create_uri(self.base_uri, prefix=prefix, suffix=suffix)
        kwargs['auth'] = self.credentials
        try:
            return delete(url=uri, *args, **kwargs)
        except Exception as e:
            self._debug_msg('An Exception occurred during request DELETE %s\n %s' % (uri, e))
            return None

    def post(self, prefix, suffix, *args, **kwargs):
        uri = create_uri(self.base_uri, prefix=prefix, suffix=suffix)
        kwargs['auth'] = self.credentials
        try:
            return post(url=uri, *args, **kwargs)
        except Exception as e:
            self._debug_msg('An Exception occurred during request POST %s\n %s' % (uri, e))
            return None

    @staticmethod
    def _debug_msg(msg):
        print '[ %s ]' % msg


def convert_to_handle(location, checksum):
    if checksum:
        new_handle_json = json.dumps([{'type': 'URL',
                                             'parsed_data': location},
                                            {'type': 'CHECKSUM',
                                             'parsed_data': checksum}])
    else:
        new_handle_json = json.dumps([{'type': 'URL',
                                             'parsed_data': location}])
    return new_handle_json


class EpicClient():
    """Class implementing an EPIC client."""

    def __init__(self, http_client, debug=False):
        """Initialize object with connection parameters."""
        # assert isinstance(self.client.get, )?
        self.client = http_client
        self.accept_format = 'application/json'
        self.debug = debug

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
        headers = None
        if self.accept_format:
            headers = {'Accept': self.accept_format}

        response = self.client.get(prefix=prefix, suffix=suffix, headers=headers)

        if response.status_code != 200:
            self._debug_msg('retrieveHandle', 'Response status: %s' % response.status_code)
            return None

        return response.content

    def create_handle(self, prefix, suffix, location, checksum):
        """Create a new handle for a file.
        Parameters:
        prefix:     URI to the resource, or the prefix if suffix is not ''.
        suffix:     The suffix of the handle. Default: ''.
        keyValues:     Dictionary with all key:value pairs to add to this handle.
                The 'URL' key is required, all other keys are optional and up to the caller''
        Returns the URI of the new handle, None if an error occurred.

        """
        #if-none-match is here for "conditional" PUT only if url don't exist yet
        headers = {'If-None-Match': '*',
                   'Content-Type': 'application/json'}

        new_handle_json = convert_to_handle(location, checksum)
        response = self.client.put(prefix=prefix, suffix=suffix, headers=headers, data=new_handle_json)

        if response.status_code != 201:
            self._debug_msg('createHandleWithLocation', 'Not Created: Response status: %s' % response.status_code)
            return None
        return response.headers['Location']

    def create_new(self, prefix, location, checksum):
        headers = {'Content-Type': 'application/json'}
        new_handle_json = convert_to_handle(location, checksum)
        response = self.client.post(prefx=prefix, headers=headers, data=new_handle_json)
        if response.status_code != 201:
            self._debug_msg('createNew', 'Not Created: Response status %s' % response.status_coce)
            return None

        return response.headers['Location']

    def delete_handle(self, prefix, suffix=''):
        """Delete a handle from the server.

        Parameters:
        prefix: URI to the resource, or the prefix if suffix is not ''.
        suffix: The suffix of the handle. Default: ''.
        Returns True if deleted, False otherwise.

        """
        response = self.client.delete(suffix=suffix, prefix=prefix)

        if response.status_code != 200:
            self._debug_msg('delete_handle', 'Not Deleted: Response status: %s ' % response.status_code)
            return False

        return True
