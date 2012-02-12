# coding: utf-8

from flask import Flask
from flask import g, session, request, redirect, url_for, jsonfiy

from flaskext.principal import Principal, identity_loaded
from flaskext.babel import Babel, gettext as _

from codewow import views
from codewow.ext import db, oid
from codewow.models import User
from codewow.utils.escape import json_encode, json_decode

# configure
DEFAULT_APP_NAME = 'codewow'

DEFAULT_MODULES = (
    ("", views.home),
    ("", views.account),
    ("/gist", views.gist),
    ("/reply", views.gist),
)

# actions
def create_app(config=None, app_name=None, modules=None):

    if app_name is None:
        app_name = DEFAULT_APP_NAME

    if modules is None:
        modules = DEFAULT_MODULES   
    
    app = Flask(app_name)

    app.config.from_pyfile(config)

    # register module
    configure_modules(app, modules) 
    configure_extensions(app)
    configure_i18n(app)
    configure_identity(app)
    configure_ba_handlers(app)
    configure_errorhandlers(app)

    return app


def configure_extensions(app):
    # configure extensions          
    db.init_app(app)
    oid.init_app(app)


def configure_modules(app, modules):
    
    for url_prefix, module in modules:
        app.register_module(module, url_prefix=url_prefix)


def configure_i18n(app):

    babel = Babel(app)

    @babel.localeselector
    def get_locale():
        accept_languages = app.config.get('ACCEPT_LANGUAGES',['en','zh'])
        return request.accept_languages.best_match(accept_languages)


def configure_identity(app):

    principal = Principal(app)

    @identity_loaded.connect_via(app)
    def on_identity_loaded(sender, identity):
        g.user = User.query.from_identity(identity)


def configure_ba_handlers(app):

    @app.before_request
    def lookup_current_user():
        g.user = None
        if 'openid' in session:
            g.user = User.query.filter_by(openid=session['openid']).first()

    @app.before_request
    def convert_data():
        content_type = request.headers.get('Content-Type', '').split(';').pop(0).strip().lower()
        if content_type == 'application/json' and request.method in ('PUT', 'POST'):
            try:
                data = json_decode(request.data) 
            except (ValueError, TypeError), e:
                abort(415)
            else:
                request.json_data = data

def configure_errorhandlers(app):
    @app.errorhandler(401)
    def unauthorized(error):
        if request.is_xhr:
            return jsonfiy(error=_("Login required"))
        flash(_("Please login to see this page"), "error")
        return redirect(url_for("account.login", next=request.path))
  
    @app.errorhandler(403)
    def forbidden(error):
        if request.is_xhr:
            return jsonify(error=_('Sorry, page not allowed'))
        return render_template("errors/403.html", error=error)

    @app.errorhandler(404)
    def page_not_found(error):
        if request.is_xhr:
            return jsonify(error=_('Sorry, page not found'))
        return render_template("errors/404.html", error=error)

    @app.errorhandler(500)
    def server_error(error):
        if request.is_xhr:
            return jsonify(error=_('Sorry, an error has occurred'))
        return render_template("errors/500.html", error=error)

    @app.errorhandler(415)
    def json_decode_error(error):
        return jsonfiy(error=_('Json format error'))
