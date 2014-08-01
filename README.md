Simple REST interface to EUDAT services
=======================================

[![Build Status](https://secure.travis-ci.org/mhellmic/http-api.png?branch=master)](https://travis-ci.org/mhellmic/http-api)

Installation
------------

Required python packages (check `requirements.txt`):

- requests
- Flask
- Flask-SQLAlchemy
- Flask-Bootstrap
- marshmallow
- BeautifulSoup
- ijson
- xattr

Testing:

- mock
- nose
- httmock


Instructions:

    git clone https://github.com/EudatHttpApi/http-api.git

    pip install -r requirements.txt

    git clone https://code.google.com/p/irodspython/
    # follow install instructions in irodspython/PyRods/

    cd http-api
    ./db_create.py
    python run.py

Find more detailed instructions including how to install in a virtualenv here:
https://github.com/EudatHttpApi/http-api/wiki/Installation-guide


Supported Functionality
-----------------------

| Functionality     | Support Level | Comments |
| -------------     | -------------:| -------- |
| HTTP GET          | yes           |
| HTTP PUT          | yes           |
| HTTP DELETE       | yes           |
| HTTP POST         | no            |
| CDMI GET          | yes           | containers and objects |
| CDMI PUT          | partial       | yes (containers) and yes, but very slow and resource-intensive (objects) |
| CDMI DELETE       | yes           | containers and objects |
| CDMI POST         | no            |
| CDMI Object IDs   | partial       | creation works and gets saved, but you cannot access by object ID directly |
| Authentication    | Username/Password |
| PIDs              | yes           | stored in object user metadata |
| Registration      | partial       | works only for src URL that are free to read or user/password-protected |


Coding Style
------------
Primarily all code has to adhere to PEP8 http://legacy.python.org/dev/peps/pep-0008/.
