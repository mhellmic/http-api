from requests import get, post
import json
import requests
from urlparse import urlparse
from BeautifulSoup import BeautifulStoneSoup


def create_uri(base_uri, prefix, suffix=''):
    """Creates handle uri from provided parameters

    @param base_uri: base epic service uri
    @param prefix: handle prefix
    @param suffix: handle suffix
    @return: proper http url
    """
    return '/'.join([base_uri, prefix, suffix])


def extract_prefix_suffix(url):
    parsed = urlparse(url)
    tokenized = parsed.path.split('/')
    return tokenized[-2], tokenized[-1]


def rename_key_in_dictionary(dictionary, old_name, new_name):
    if dictionary.has_key(old_name):
        dictionary[new_name] = dictionary.pop(old_name)


class HandleRecord(object):
    """Handle record

    Internal representation of handle records is a list, with
    dictionaries as entries
    """

    TYPE_STR = 'type'
    DATA_STR = 'data'
    EPIC_DATA_STR = 'parsed_data'
    URL_TYPE_NAME = 'URL'
    CHECKSUM_TYPE_NAME = 'CHECKSUM'
    LOC = '10320/LOC'

    def __init__(self):

        self.content = list()

    def add_value(self, entry_type, data):
        self.content.append({self.TYPE_STR: entry_type,
                             self.DATA_STR: data})

    def add_url(self, url):
        self.add_value(entry_type=self.URL_TYPE_NAME, data=url)

    def add_checksum(self, checksum):
        self.add_value(entry_type=self.CHECKSUM_TYPE_NAME, data=checksum)

    def get_entries_with_property_value(self, property_name, value):
        return [k for k in self.content if k[property_name] == value]

    def get_data_with_property_value(self, property_name, value):
        res = self.get_entries_with_property_value(property_name, value)
        if not res:
            return None
        return res[0][self.DATA_STR]

    def get_url_value(self):
        return self.get_data_with_property_value(self.TYPE_STR,
                                                 self.URL_TYPE_NAME)

    def get_checksum_value(self):
        return self.get_data_with_property_value(self.TYPE_STR,
                                                 self.CHECKSUM_TYPE_NAME)

    def get_all_locations(self):
        """Returns list of all locations found in Handle record

        Locations can be found at two places URL and 10320/LOC field. The
        later field has to be parsed.

        """
        locations = [self.get_url_value()]

        loc = self.get_data_with_property_value(self.TYPE_STR, self.LOC)
        if not loc:
            return locations

        soup = BeautifulStoneSoup(loc)
        for l in soup.findAll('location'):
            locations.append(l['href'])
        return locations

    def as_epic_json_array(self):
        cpy = list(self.content)
        for entry in cpy:
            rename_key_in_dictionary(entry, self.DATA_STR,
                                     self.EPIC_DATA_STR)
        return json.dumps(cpy)

    def __str__(self):
        ret = '%s[' % self.__class__.__name__
        for k in self.content:
            ret += '%s ' % k
        return ret + ']'


    @staticmethod
    def from_json(json_entity):
        json_array = json_entity
        data_field_name = HandleRecord.DATA_STR
        if isinstance(json_entity, dict) and json_entity.has_key('values'):
            json_array = json_entity['values']
        else:
            data_field_name = HandleRecord.EPIC_DATA_STR

        h = HandleRecord()
        for entry in json_array:
            h.add_value(entry[h.TYPE_STR], entry[data_field_name])

        return h


    @staticmethod
    def get_handle_with_values(url, checksum=0):
        h = HandleRecord()
        h.add_url(url)
        if checksum != 0:
            h.add_checksum(checksum)

        return h


class EpicClient(object):
    """Client for communication with epic and handle pid service."""

    SARA_BASE_URI = 'https://epic.sara.nl/v2/handles/'
    HANDLE_BASE_URI = 'http://hdl.handle.net/api/handles/'

    def __init__(self, base_uri, credentials, debug=False):
        """Initialize object with connection parameters."""
        self.accept_format = 'application/json'
        self.debug = debug
        self.credentials = credentials
        if base_uri[-1] == '/':
            self.base_uri = base_uri[:-1]
        else:
            self.base_uri = base_uri


    def _debug_msg(self, method, msg):
        """Internal: Print a debug message if debug is enabled."""
        #fixme: should be using logger
        if self.debug:
            print '[ %s ] %s' % (method, msg)

    def retrieve_handle(self, prefix, suffix=''):
        """Retrieve a handle from the PID service.

        This method should work equally good with epic and handle endpoints.

        Parameters:
        prefix: URI to the resource, or the prefix if suffix is not ''.
        suffix: The suffix of the handle. Default: ''.
        Returns handle record

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

        return HandleRecord.from_json(response.json())

    def create_new(self, prefix, handle_record):
        """Create new handle

        utilizes automatic pid generation function of the epic api
        Here we presume (without validating) that the target server is epic
        and not handle. This makes sense since handle does not support
        creation. Nevertheless a more sophisticated verification could be
        sensible here.

        @param prefix: prefix in which the new handle should be placed
        @param handle_record: handle record object
        @return: location of the handle
        """
        headers = {'Content-Type': 'application/json'}
        response = post(url=create_uri(base_uri=self.base_uri,
                                       prefix=prefix, suffix=''),
                        headers=headers,
                        data=handle_record.as_epic_json_array(),
                        auth=self.credentials)

        if response is None:
            return None

        if response.status_code != requests.codes.created:
            self._debug_msg('createNew',
                            'Not Created: Response status %s' %
                            response.status_code)
            return None

        return response.headers['Location']
