import msal
import requests
from flask import redirect, render_template, request, session, url_for

from . import (
    AUTHORITY,
    ENDPOINT,
    MSAL_CLIENT_ID,
    MSAL_CLIENT_SECRET_VALUE,
    REDIRECT_PATH,
    SCOPE,
    app,
)


@app.get("/login")
def login():
    session["flow"] = _build_auth_code_flow(scopes=[SCOPE])
    return render_template(
        "login.html", auth_url=session["flow"]["auth_uri"], version=msal.__version__
    )


@app.get(REDIRECT_PATH)
def authorized():
    try:
        cache = _load_cache()
        result = _build_msal_app(cache=cache).acquire_token_by_auth_code_flow(
            session.get("flow", {}), request.args
        )
        if "error" in result:
            return render_template("auth_error.html", result=result)
        session["user"] = result.get("id_token_claims")
        _save_cache(cache)
    except ValueError:
        pass
    return redirect(url_for("index"))


@app.get("/logout")
def logout():
    session.clear()
    return redirect(
        AUTHORITY
        + "/oauth2/v2.0/logout"
        + "?post_logout_redirect_uri="
        + url_for("index", _external=True)
    )


def graphcall():
    token = _get_token_from_cache([SCOPE])
    if not token:
        return redirect(url_for("login"))

    graph_data = requests.get(
        ENDPOINT, headers={"Authorization": "Bearer " + token["access_token"]},
    ).json()
    return render_template("display.html", result=graph_data)


def _load_cache():
    cache = msal.SerializableTokenCache()
    if session.get("token_cache"):
        cache.deserialize(session["token_cache"])
    return cache


def _save_cache(cache):
    if cache.has_state_changed:
        session["token_cache"] = cache.serialize()


def _build_msal_app(cache=None, authority=None):
    return msal.ConfidentialClientApplication(
        MSAL_CLIENT_ID,
        authority=authority or AUTHORITY,
        client_credential=MSAL_CLIENT_SECRET_VALUE,
        token_cache=cache,
    )


def _build_auth_code_flow(authority=None, scopes=None):
    return _build_msal_app(authority=authority).initiate_auth_code_flow(
        scopes or [], redirect_uri=url_for("authorized", _external=True)
    )


def _get_token_from_cache(scope=None):
    cache = _load_cache()
    cca = _build_msal_app(cache=cache)
    accounts = cca.get_accounts()
    if accounts:
        result = cca.acquire_token_silent(scope, account=accounts[0])
        _save_cache(cache)
        return result


app.jinja_env.globals.update(_build_auth_code_flow=_build_auth_code_flow)
