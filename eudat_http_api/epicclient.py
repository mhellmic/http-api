
from requests import get, post, put, delete
import json

def create_uri(baseuri, prefix, suffix=''):
        uri = baseuri + '/' + prefix
        if suffix != '':
            uri += '/' + suffix
        return uri

class HttpClient():
    def __init__(self, baseuri, credentials):
        self.credentials = credentials
        self.baseuri = baseuri

    def get(self, prefix, suffix, *args, **kwargs):
        uri = create_uri(self.baseuri, prefix=prefix, suffix=suffix)
        kwargs['auth'] = self.credentials
        try:
            return get(url=uri, *args, **kwargs)
        except Exception as e:
            self._debugMsg('An Exception occurred during request GET %s\n %s' % (uri, e))
            return None

    def put(self, prefix, suffix, *args, **kwargs):
        uri = create_uri(self.baseuri, prefix=prefix, suffix=suffix)
        kwargs['auth'] = self.credentials
        try:
            return put(url=uri, *args, **kwargs)
        except Exception as e:
            self._debugMsg('An Exception occurred during request PUT %s\n %s' % (uri, e))
            return None

    def delete(self, prefix, suffix, *args, **kwargs):
        uri = create_uri(self.baseuri, prefix=prefix, suffix=suffix)
        kwargs['auth'] = self.credentials
        try:
            return delete(url=uri, *args, **kwargs)
        except Exception as e:
            self._debugMsg('An Exception occurred during request DELETE %s\n %s' % (uri, e))
            return None

    def _debugMsg(self, msg):
        print '[ %s ]' % msg


def convert_dict_to_handle(keyValues):
    index = 1
    dict = {}
    for key in keyValues:
        dict[str(index)] = {'type': key, 'data': keyValues[key]}
        index += 1
    return json.dumps(dict)


class EpicClient():
    """Class implementing an EPIC client."""

    def __init__(self, httpClient, debug=False):
        """Initialize object with connection parameters."""
        # assert isinstance(self.client.get, )?
        self.client = httpClient
        self.accept_format = 'application/json'
        self.debug = debug


    def _debugMsg(self, method, msg):
        """Internal: Print a debug message if debug is enabled."""
        #fixme: should be using logger
        if self.debug:
            print '[ %s ] %s' % (method, msg)

    def retrieveHandle(self, prefix, suffix=''):
        """Retrieve a handle from the PID service.
        Parameters:
        prefix: URI to the resource, or the prefix if suffix is not ''.
        suffix: The suffix of the handle. Default: ''.
        Returns the content of the handle in JSON, None on error.

        """
        hdrs = None
        if self.accept_format:
            hdrs = {'Accept': self.accept_format}

        response = self.client.get(prefix=prefix, suffix=suffix, headers=hdrs)

        if response.status_code != 200:
            self._debugMsg('retrieveHandle', 'Response status: %s' % response.status_code)
            return None

        return response.content

    def createHandle(self, prefix, suffix, keyValues):
        """Create a new handle for a file.
        Parameters:
        prefix: 	URI to the resource, or the prefix if suffix is not ''.
        suffix: 	The suffix of the handle. Default: ''.
        keyValues: 	Dictionary with all key:value pairs to add to this handle.
                The 'URL' key is required, all other keys are optional and up to the caller''
        Returns the URI of the new handle, None if an error occurred.

        """
        #fixme: check what the if-none-match is here for
        hdrs = {'If-None-Match': '*', 'Content-Type': 'application/json'}

        new_handle_json = convert_dict_to_handle(keyValues)
        response = self.client.put(prefix=prefix, suffix=suffix, headers=hdrs, data=new_handle_json)

        if response.status_code != 201:
            self._debugMsg('createHandleWithLocation', 'Not Created: Response status: %s' % response.status_code)
            return None

        return response['location']


    def modifyHandle(self, prefix, key, value, suffix=''):
        """Modify a parameter of a handle

        Parameters:
        prefix: 	URI to the resource, or the prefix if suffix is not ''.
        key: 		The parameter "type" wanted to change
        value: 		New value to store in "data"
        suffix: 	The suffix of the handle. Default: ''.
        Returns True if modified or parameter not found, False otherwise.

        """

        hdrs = {'Content-Type': 'application/json'}

        if not key:
            return False

        handle_json = self.retrieveHandle(prefix, suffix)
        if not handle_json:
            self._debugMsg('modifyHandle', 'Cannot modify an non-existing handle: %s/%s' % (prefix, suffix))
            return False

        handle = json.loads(handle_json)
        maxIdx = 0
        for idx in handle:
            if int(idx) > maxIdx: maxIdx = int(idx)
            if 'type' in handle[idx] and handle[idx]['type'] == key:
                self._debugMsg('modifyHandle', 'Found key %s idx = %d' % (key, idx))
                if value is None:
                    del (handle[idx])
                else:
                    handle[idx]['data'] = value
                break
        else:
            if value is None:
                self._debugMsg('modifyHandle', 'Key %s  not found. Quiting' % key)
                return True

            idx = maxIdx + 1
            self._debugMsg('modifyHandle', "Key " + key + " not found. Generating new idx=" + str(idx))
            handle[idx] = {'type': key, 'data': value}

        handle_json = json.dumps(handle)
        self._debugMsg('modifyHandle', 'JSON: %s ' + handle_json)
        response = self.client.put(prefix=prefix, suffix=suffix, headers=hdrs, data=handle_json)

        if response.status_code != 200:
            self._debugMsg('modifyHandle', 'Not Modified: Response status: %s' % response.status_code)
            return False

        return True


    def deleteHandle(self, prefix, suffix=''):
        """Delete a handle from the server.

        Parameters:
        prefix: URI to the resource, or the prefix if suffix is not ''.
        suffix: The suffix of the handle. Default: ''.
        Returns True if deleted, False otherwise.

        """
        response = self.client.delete(suffix=suffix, prefix=prefix)

        if response.status_code != 200:
            self._debugMsg('deleteHandle', 'Not Deleted: Response status: %s ' % response.status_code)
            return False

        return True


