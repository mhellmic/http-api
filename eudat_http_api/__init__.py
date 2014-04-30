from flask import Flask


def create_app(config_name):
    app = Flask(__name__)
    if config_name is not None:
        app.config.from_object(config_name)

    if not app.debug:
        import logging
        from logging.handlers import SysLogHandler
        file_handler = SysLogHandler()
        file_handler.setLevel(logging.WARNING)
        app.logger.addHandler(file_handler)

    with app.app_context():
        # the app context is needed to switch the storage
        # backend based on the config parameter.
        # (which is bound to the app object)
        if app.config.get('ACTIVATE_STORAGE_READ', False):
            from eudat_http_api.http_storage.init import http_storage_read
            app.register_blueprint(http_storage_read)

        if app.config.get('ACTIVATE_STORAGE_WRITE', False):
            from eudat_http_api.http_storage.init import http_storage_write
            app.register_blueprint(http_storage_write)

        if app.config.get('ACTIVATE_CDMI'):
            from eudat_http_api.http_storage.cdmi import cdmi_uris
            app.register_blueprint(cdmi_uris)

        if app.config.get('ACTIVATE_REGISTRATION', False):
            from eudat_http_api.registration.init import registration
            app.register_blueprint(registration)

            from eudat_http_api.registration import models
            models.db.init_app(app)

    return app
