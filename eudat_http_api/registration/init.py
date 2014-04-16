# -*- coding: utf-8 -*-

from flask import Blueprint
import flask
from flask import current_app
from flask import request
from flask import json
from flask import abort, url_for
from flask import redirect
from eudat_http_api.common import request_wants, ContentTypes
from eudat_http_api.epicclient import EpicClient
from eudat_http_api.epicclient import HttpClient
from eudat_http_api.cdmiclient import CDMIClient

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker

from eudat_http_api.registration.models import db
from eudat_http_api import invenioclient
from eudat_http_api import auth
from eudat_http_api.registration.registration_worker import RegistrationWorker

from models import RegistrationRequest, RegistrationRequestSerializer
from config import REQUESTS_PER_PAGE
from datetime import datetime
from requests.auth import HTTPBasicAuth


registration = Blueprint('registration', __name__,
                         template_folder='templates')


def get_hal_links(reg_requests, page):
    """returns links in json hal format"""
    navi = dict()
    navi['self'] = {'href': url_for('get_requests', page=page)}
    if reg_requests.has_next:
        navi['next'] = {'href': url_for('get_requests',
                                        page=reg_requests.next_num)}
    if reg_requests.has_prev:
        navi['prev'] = {'href': url_for('get_requests',
                                        page=reg_requests.prev_num)}

    return navi


def get_registered_base_url():
    return 'http://%s:%d%s' % (current_app.config.get('STORAGE_HOST', None),
                               current_app.config.get('STORAGE_PORT', None),
                               current_app.config.get('REGISTERED_PREFIX',
                                                      None)
                               )


@registration.route('/request/', methods=['GET'])
@auth.requires_auth
def get_requests():
    """Get a requests list."""
    page = int(request.args.get('page', '1'))
    reg_requests = RegistrationRequest.query.order_by(
        RegistrationRequest.timestamp.desc()).paginate(page,
                                                       REQUESTS_PER_PAGE,
                                                       False)

    if request_wants(ContentTypes.json):
        return flask.jsonify(
            {"requests": RegistrationRequestSerializer(reg_requests.items,
                                                       many=True).data,
             "_links": get_hal_links(reg_requests, page)})

    return flask.render_template('requests.html', requests=reg_requests)


@registration.route('/request/', methods=['POST'])
@auth.requires_auth
def post_request():
    """Submit a new registration request

  Specify in the message body:
  src: url of the source file
  checksum: the file you expect the file will have.

  The function returns a URL to check the status of the request.
  The URL includes a request ID.
  """
    current_app.logger.debug('Entering post_request()')

    if flask.request.headers.get('Content-Type') == 'application/json':
        req_body = json.loads(flask.request.data)
    else:
        req_body = flask.request.form

    r = RegistrationRequest(src_url=req_body['src_url'],
                            status_description='Registration request created',
                            timestamp=datetime.utcnow())
    db.session.add(r)
    db.session.commit()

    httpClient = HttpClient(current_app.config['HANDLE_URI'],
                            HTTPBasicAuth(current_app.config['HANDLE_USER'],
                                          current_app.config['HANDLE_PASS']))

    cdmiclient = CDMIClient(auth=HTTPBasicAuth(request.authorization.username,
                            request.authorization.password))

    db_engine = create_engine(
        current_app.config.get('SQLALCHEMY_DATABASE_URI'))
    session_factory = sessionmaker(bind=db_engine)
    Session = scoped_session(session_factory)
    db_session = Session()
    db_session._model_changes = {}

    # FIXME: due to the fuckedup blueprints I don't know how to define the
    # destination url, something like:
    # url_for('http_storage.put_cdmi_obj',objpath='/')
    # reply: we can't use blueprints for this, and we shouldn't, because the
    # destination can be on another server. At least we have to figure out
    # the correct hostname by ourselves.
    p = RegistrationWorker(request_id=r.id,
                           epicclient=EpicClient(httpClient=httpClient),
                           logger=current_app.logger,
                           cdmiclient=cdmiclient,
                           base_url=get_registered_base_url(),
                           db_session=db_session)
    # we have to close it explicitly already here otherwise the request object
    # is bound to this session
    db.session.close()
    p.start()

    r.status_description_list = r.status_description.split(';')

    if request_wants(ContentTypes.json):
        return flask.jsonify(request_id=r.id), 201
    else:
        return flask.render_template('requestcreated.html', reg=r), 201


@registration.route('/request/<request_id>', methods=['GET'])
@auth.requires_auth
def get_request(request_id):
    """Poll the status of a request by ID."""
    r = RegistrationRequest.query.get(request_id)

    #TODO: json error?
    if r is None:
        return abort(404)

    r.status_description_list = r.status_description.split(';')

    if request_wants(ContentTypes.json):
        return flask.jsonify(
            {'request': RegistrationRequestSerializer(r).data}
        )

    return flask.render_template('singleRequest.html', r=r)


#### /registered container ####
#jj: this is a separate component?


@registration.route('/registered/<pid_prefix>/', methods=['GET'])
@auth.requires_auth
def get_pids_by_prefix():
    # search PIDs with this prefix on handle.net

    # return list of PIDs
    # (with links to /registered/<full_pid>) to download
    pass


@registration.route('/registered/<pid_prefix>/<pid_suffix>', methods=['GET'])
@auth.requires_auth
def get_pid_by_handle(pid_prefix, pid_suffix):
    """Retrieves a data object by PID."""
    #pid = pid_prefix + '/' + pid_suffix

    # resolve PID
    #handle_key = "11007/00-ZZZZ-0000-0000-FAKE-7"

    # extract link to data object
    data_object_url = ('http://127.0.0.1:5000/tmp/registered/'
                       '711a84d7159a8ad13e4a42c0e0eb6e1c7af80'
                       '30684a5252a99421e5cf8988925')

    # choose link to data object

    # return data object
    return redirect(data_object_url, code=302)
