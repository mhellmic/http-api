#!/bin/bash

APPNAME="eudat_http_api.app"
PORT=5000

start() {
  twistd web --port $PORT --wsgi $APPNAME
}

stop() {
  if [ -f twistd.pid ]; then
    kill `cat twistd.pid`
  fi
}

status() {
  pgrep twistd > /dev/null
  if [ $? -eq 0 ]; then
    echo "twistd is running ..."
  else
    echo "twistd is stopped."
  fi
}

case "$1" in
  start)
    start
    RETVAL=$?
    ;;
  stop)
    stop
    RETVAL=$?
    ;;
  restart)
    stop
    start
    RETVAL=$?
    ;;
  status)
    status
    RETVAL=$?
    ;;
  *)
    echo $"Usage: ./service_twistd.sh {start|stop|restart|status}"
    RETVAL=2
    ;;
esac

exit $RETVAL
