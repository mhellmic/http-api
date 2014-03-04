# -*- coding: utf-8 -*-

from __future__ import with_statement

from eudat_http_api import app

if app.config['STORAGE'] == 'local':
    app.logger.debug('using local storage backend')
    from eudat_http_api.localstorage import *

elif app.config['STORAGE'] == 'irods':
    app.logger.debug('using irods storage backend')
    from eudat_http_api.irodsstorage import *

else:
    raise NotImplementedError("%s does not exist" % app.config['STORAGE'])
