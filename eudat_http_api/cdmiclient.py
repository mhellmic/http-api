# -*- coding: utf-8 -*-

from __future__ import with_statement

import requests

def cdmi_head(url, auth):
    headers = {
        'Accept': 'application/cdmi-object',
        'X-CDMI-Specification-Version': '1.0.2',
    }
    r = requests.head(url, headers=headers, auth=auth)
    return r

def cdmi_get(url, auth):
    headers = {
        'Accept': 'application/cdmi-object',
        'X-CDMI-Specification-Version': '1.0.2',
    }

    r = requests.get(url, headers=headers, auth=auth)

    return r


def post(url):
    pass
