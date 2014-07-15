#!/bin/sh
set -ex
cd /tmp

wget https://irodspython.googlecode.com/git/Downloads/PyRods-3.3.5.tar.gz -O /tmp/PyRods-3.3.5.tar.gz
tar xvzf PyRods-3.3.5.tar.gz
cd PyRods-3.3.5

#wget https://github.com/mhellmic/irodspython/archive/master.zip -O /tmp/PyRods.zip
#unzip PyRods.zip
#cd irodspython-master/PyRods

export CFLAGS=-fPIC
./scripts/configure
make clients
python setup.py build
python setup.py install
