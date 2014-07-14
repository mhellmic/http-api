# -*- coding: utf-8 -*-

from __future__ import with_statement

from flask import current_app

from eudat_http_api.http_storage.common import get_config_parameter


if get_config_parameter('STORAGE') == 'local':
    current_app.logger.debug('using local storage backend')
    from eudat_http_api.http_storage.localstorage import *

elif get_config_parameter('STORAGE') == 'irods':
    current_app.logger.debug('using irods storage backend')
    from eudat_http_api.http_storage.irodsstorage import *

elif get_config_parameter('STORAGE') == 'dmlite':
    current_app.logger.debug('using dmlite storage backend')
    from eudat_http_api.http_storage.dmlitestorage import *

else:
    raise NotImplementedError('%s does not exist'
                              % get_config_parameter('STORAGE'))
