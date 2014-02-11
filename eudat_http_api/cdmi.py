
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import with_statement

from flask import g
from flask import request
from flask import jsonify as flask_jsonify

from eudat_http_api import app


@app.before_request
def check_cdmi():
  if request.headers.get('Content-Type').startswith('application/cdmi'):
    g.cdmi = True
    g.cdmi_version = request.headers.get('X-CDMI-Specification-Version')
  else:
    g.cdmi = False


def jsonify():
  return flask_jsonify()
