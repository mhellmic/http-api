
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import with_statement

from flask import g

from contextlib import closing
import sqlite3

from eudat_http_api import app

def connect_db():
  db = sqlite3.connect(app.config['DB_NAME'])
  db.row_factory = sqlite3.Row
  return db

def init_db():
  with closing(connect_db()) as db:
    with app.open_resource('schema.sql', mode='r') as f:
      db.cursor().executescript(f.read())
    db.commit()

def get_db():
  db = getattr(g, 'requestsdb', None)
  if db is None:
    db = g.requestsdb = connect_db()
  return db

@app.teardown_appcontext
def close_db_on_teardown_appcontext(exception):
  db = getattr(g, 'requestsdb', None)
  if db is not None:
    db.close()

def query_db(query, args=()):
  cursor = get_db().execute(query, args)
  rv = cursor.fetchall()
  cursor.close()
  return rv

def query_db_single(query, args=()):
  cursor = get_db().execute(query, args)
  rv = cursor.fetchone()
  cursor.close()
  return rv

def query_db_single_with_conn(db, query, args=()):
  cursor = db.execute(query, args)
  rv = cursor.fetchone()
  cursor.close()
  return rv

def insert_db(query, args=()):
  db = get_db()
  db.cursor().execute(query, args)
  db.commit()

