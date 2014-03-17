# -*- coding: utf-8 -*-

from __future__ import with_statement

from flask import current_app
from flask import g

import requests


def get_invenio_key():
  return current_app.config['INVENIO_KEY']

def get_metadata(obj_id):
  """Get the metadata of obj as python dict."""
  key = get_invenio_key()

def put_metadata(obj_id, md_dict):
  """Store the metadat of obj into invenio.

  Expects the metadata as python dict.
  """
  key = get_invenio_key()

def update_metadata(obj_id, md_dict):
  """Update metadata of obj.

  All values that exist on invenio already
  will be updated, new ones are added.
  Expects the metadata as python dict.
  """
  key = get_invenio_key()
