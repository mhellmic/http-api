Simple REST interface to EUDAT services
=======================================

Installation
------------

Required python packages:

- flask
- requests
- Flask-SQLAlchemy
- marshmallow
- BeautifulSoup

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


Unit Testing
------------

You can start the unit tests to confirm your changes.

    cd http-api
    TEST_CONFIG=test.config.LocalConfig nosetests test.unittests

This will run nosetests to do all unit tests with the local storage backend.
Using another environment variable tests other backends, for example irods.

    TEST_CONFIG=test.config.IrodsConfig nosetests test.unittests

For this, you probably want to configure your irods server in

    vim test/config.py

You can also execute the tests partially, by class

    TEST_CONFIG=test.config.LocalConfig nosetests test.unittests:TestHttpApi

or by single test

    TEST_CONFIG=test.config.LocalConfig nosetests test.unittests:TestStorageApi.test_stat

If you start the tests without an environment variable, nosetests will try to test the mock backend,
which is already deprecated. Please don't be upset about errors.


Coding Style
------------
Primarily all code has to adhere to PEP8 http://legacy.python.org/dev/peps/pep-0008/.
