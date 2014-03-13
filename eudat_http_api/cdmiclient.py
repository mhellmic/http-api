# -*- coding: utf-8 -*-

from __future__ import with_statement

import requests


def head(url):
    r = requests.head(url)
    return None, r


def get(url):
    r = requests.get(url)
    return None, r


def post(url):
    pass


def cdmi_head(url):
    headers = {
        'Accept': 'application/cdmi-object',
        'X-CDMI-Specification-Version': '1.0.2',
    }

    r = requests.head(url, headers=headers)

    return None, r


def cdmi_get(url):
    headers = {
        'Accept': 'application/cdmi-object',
        'X-CDMI-Specification-Version': '1.0.2',
    }

    r = requests.get(url, headers=headers)

    return None, r


def post(url):
    pass
