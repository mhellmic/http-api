# -*- coding: utf-8 -*-

from __future__ import with_statement

from flask import current_app


if current_app.config['STORAGE'] == 'local':
    current_app.logger.debug('using local storage backend')
    from eudat_http_api.http_storage.localstorage import *

elif current_app.config['STORAGE'] == 'irods':
    current_app.logger.debug('using irods storage backend')
    from eudat_http_api.http_storage.irodsstorage import *

elif current_app.config['STORAGE'] == 'mock':
    current_app.logger.debug('using mock storage backend')
    from eudat_http_api.http_storage.mockstorage import *

else:
    raise NotImplementedError('%s does not exist'
                              % current_app.config['STORAGE'])
