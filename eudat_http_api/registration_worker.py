# -*- coding: utf-8 -*-

from __future__ import with_statement

import json
import requests

from eudat_http_api import app
from eudat_http_api import cdmiclient
from eudat_http_api.models import RegistrationRequest

#jj: this should be moved to model?
request_statuses = {
    'waiting to be started': 'W',
    'started': 'S',
    'src checked': 'E',
    'dst permissions checked': 'DP',
    'checksums in request and src match': 'C',
    'retrieved PID': 'P',
    'file copied to dst space': 'FC',
    'aborted': 'A'
    }

def register_data_object(request_id):
  app.logger.debug('starting to process request with id = %s' % (request_id,))
  r = RegistrationRequest.query.get(request_id)

  steps = [
      create_dst_url,
      check_src,
      check_dst_permissions,
      check_checksum_match,
      get_handle,
      copy_data_object
      ]

  for s in steps:
    s(r)

def create_dst_url(request):
  pass

def check_src(request):
  if request.pid:
    return

    continue_request(request, request_statuses['started'])
  # check existence and correct permissions on source
  _, response = cdmiclient.head('%s' % (request.src_url))
  if response.status_code > 299:
    abort_request(request, 'Source file is not available')
  else:
    continue_request(request, request_statuses['src checked'])

  metadata, response = cdmiclient.cdmi_get('%s?%s' % (request.src_url, 'metadata'))
  metadata_json = json.loads(metadata.read())

  # also check the content of metadata; if it conforms to datacite3

  # we could use the request object as a store going from function to function,
  # so we can separate e.g. check_src_permissions and check_checksum,
  # but still do only one request


def check_dst_permissions(request):
  if request.pid:
    return

  #jj: I don't agree with the logic here. Shall we really use CDMI to interact
  #with the destination?
  if 1==1:
      return
  # check existence and correct permissions on dsts
  metadata, response = cdmiclient.get('%s?%s' % (request['dst_url'], 'metadata'))
  if response.status_code > 299:
    abort_request(request, 'Dst location is not available')
  else:
    continue_request(request, request_statuses['dst checked'])

def check_checksum_match(request):
  if request['pid']:
    return

def get_handle(request):
  if request.pid:
    return

def copy_data_object(request):
  # check src and dst permissions
  # check checksum
  # copy

  # possibly just do a CDMI PUT { copy: <src> }
  pass

def abort_request(request, reason_string):
  pass

def continue_request(request, stage_string):
  pass
