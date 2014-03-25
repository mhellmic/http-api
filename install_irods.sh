#!/bin/sh
set -e
wget ftp://ftp.renci.org/pub/irods/releases/3.0.1/eirods-3.0.1-64bit-icat-postgres.deb -O /tmp/eirods.deb

sudo apt-get -y update -qq

sudo apt-get -y install gdebi
# do this before installing irods -- it doesn't install with multiple postgres versions
sudo apt-get -y remove postgresql*
sudo gdebi -n /tmp/eirods.deb

#start irods explicitly
sudo service eirods start

sudo su eirods -c "iadmin mkuser testname rodsuser"
sudo su eirods -c "iadmin moduser testname password testpass"

sudo su eirods -c "lu"
udo su eirods -c "ils /tempZone/home/testname"
