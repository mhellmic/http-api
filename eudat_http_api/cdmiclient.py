# -*- coding: utf-8 -*-

from flask import json
import requests


class CDMIClient:
    def __init__(self, auth):
        self.auth = auth

    def cdmi_head(self, url):
        headers = {
            'Accept': 'application/cdmi-object',
            'X-CDMI-Specification-Version': '1.0.2',
        }
        r = requests.head(url, headers=headers, auth=self.auth)
        return r

    def cdmi_get(self, url, stream=False):
        headers = {
            'Accept': 'application/cdmi-object',
            'X-CDMI-Specification-Version': '1.0.2',
        }

        r = requests.get(url, headers=headers, auth=self.auth, stream=stream)

        return r

    def cdmi_put(self, url, data):
        cdmi_headers = {
            'Content-type': 'application/cdmi-object',
            'X-CDMI-Specification-Version': '1.0.2',
        }

        cdmi_data = json.dumps({
            'value': data,
        })

        return requests.put(url, headers=cdmi_headers,
                            data=cdmi_data, auth=self.auth)

    def cdmi_copy(self, url, src_url):
        cdmi_headers = {
            'Accept': 'application/cdmi-object',
            'Content-type': 'application/cdmi-object',
            'X-CDMI-Specification-Version': '1.0.2',
        }

        cdmi_data = json.dumps({
            'copy': src_url,
        })

        return requests.put(url, headers=cdmi_headers,
                            data=cdmi_data, auth=self.auth)

    def cdmi_delete(self, url):
        headers = {
            'Accept': 'application/cdmi-object',
            'X-CDMI-Specification-Version': '1.0.2',
        }

        r = requests.delete(url, headers=headers, auth=self.auth)

        return r
