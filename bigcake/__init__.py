import logging as log
import os

from dotenv import load_dotenv
from flask import Flask

from flask_session import Session

load_dotenv()

CONN_URL = os.getenv("CONN_URL", False)
SECRET_KEY = os.getenv("SECRET_KEY", False)
FLASK_APP = os.getenv("FLASK_APP", False)
FLASK_ENV = os.getenv("FLASK_ENV", False)
MSAL_CLIENT_ID = os.getenv("MSAL_CLIENT_ID", False)
MSAL_CLIENT_SECRET_VALUE = os.getenv("MSAL_CLIENT_SECRET_VALUE", False)
AUTHORITY = os.getenv("AUTHORITY", False)
REDIRECT_PATH = os.getenv("REDIRECT_PATH", False)
ENDPOINT = os.getenv("ENDPOINT", False)
SCOPE = os.getenv("SCOPE", False)
SESSION_TYPE = os.getenv("SESSION_TYPE", False)


assert all(
    [
        CONN_URL,
        SECRET_KEY,
        FLASK_APP,
        FLASK_ENV,
        MSAL_CLIENT_ID,
        MSAL_CLIENT_SECRET_VALUE,
        AUTHORITY,
        REDIRECT_PATH,
        ENDPOINT,
        SCOPE,
        SESSION_TYPE,
    ]
), "Variáveis ambientais não definidas"


log_format = "[%(levelname)s] %(module)s %(funcName)s %(message)s"
if FLASK_ENV == "development":
    log.basicConfig(level=log.INFO, format=log_format)
else:
    log.basicConfig(level=log.WARNING, format=log_format, filename="bolao.log")


app = Flask("bigcake")
app.config.from_mapping(SECRET_KEY=SECRET_KEY, SESSION_TYPE=SESSION_TYPE)
Session(app)


# This section is needed for url_for("foo", _external=True) to automatically
# generate http scheme when this sample is running on localhost,
# and to generate https scheme when it is deployed behind reversed proxy.
# See also https://flask.palletsprojects.com/en/1.0.x/deploying/wsgi-standalone/#proxy-setups
from werkzeug.middleware.proxy_fix import ProxyFix

app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)


class ReverseProxied(object):
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        environ["wsgi.url_scheme"] = "https"
        return self.app(environ, start_response)


if FLASK_ENV != "development":
    app.wsgi_app = ReverseProxied(app.wsgi_app)


from . import auth, db, router

if __name__ == "__main__":
    app.run()
