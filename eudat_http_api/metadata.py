# -*- coding: utf-8 -*-

from __future__ import with_statement

from eudat_http_api import app
from eudat_http_api import storage


def stat(identifier, user_metadata=None):
  app.logger.debug('called the metadata service')
  return storage.stat(identifier, user_metadata)
