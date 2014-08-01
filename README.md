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

    # install cffi development package, e.g.
    yum install libffi-devel

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
| HTTP GET          | <span style="color:green">yes</span>          |
| HTTP PUT          | <span style="color:green">yes</span>          |
| HTTP DELETE       | <span style="color:green">yes</span>          |
| HTTP POST         | <span style="color:red">no</span>             |
| CDMI GET          | <span style="color:green">yes</span>          | containers and objects |
| CDMI PUT          | <span style="color:yellow">partial</span>     | yes (containers) and yes, but very slow and resource-intensive (objects) |
| CDMI DELETE       | <span style="color:green">yes</span>          | containers and objects |
| CDMI POST         | <span style="color:red">no</span>             |
| CDMI Object IDs   | <span style="color:yellow">partial</span>     | creation works and gets saved, but you cannot access by object ID directly |
| Authentication    | <span style="color:yellow">Username/Password</span> |
| PIDs              | <span style="color:green">yes</span>          | stored in object user metadata |
| Registration      | <span style="color:yellow">partial</span>     | works only for src URL that are free to read or user/password-protected |


Coding Style
------------
Primarily all code has to adhere to PEP8 http://legacy.python.org/dev/peps/pep-0008/.
