#!/bin/sh
set -ex
cd /tmp
wget https://irodspython.googlecode.com/git/Downloads/PyRods-3.3.4.tar.gz -O /tmp/PyRods-3.3.4.tar.gz
tar xvzf PyRods-3.3.4.tar.gz
cd PyRods-3.3.4
export CFLAGS=-fPIC
./scripts/configure
make clients
python setup.py build
sudo python setup.py install
