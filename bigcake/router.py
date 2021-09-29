from datetime import date

from flask import redirect, render_template, session, url_for
from flask_wtf import FlaskForm
from wtforms import SelectField, TextField
from wtforms.validators import DataRequired, Length

from . import app, msal
from .db import (
    add_palpite,
    add_resultado,
    check_user,
    get_categorias,
    get_modalidades,
    get_paises,
    get_podios,
    get_users,
)

ADMIN_OIDS = ["YOUR_OID"]


def is_admin(user: dict) -> bool:
    return user.get("oid") in ADMIN_OIDS


def form_builder() -> FlaskForm:
    field_args = dict(
        render_kw={"class": "form-control"}, validators=[DataRequired(), Length(min=1, max=3)],
    )

    class PalpiteForm(FlaskForm):
        modalidade_id = TextField("modalidade_id", **field_args)
        pais_ouro = SelectField("Ouro", **field_args)
        pais_prata = SelectField("Prata", **field_args)
        pais_bronze = SelectField("Bronze", **field_args)

    paises_options = [(p.pais_id, p.pais_nome) for p in get_paises()]
    form = PalpiteForm()
    form.pais_ouro.choices = paises_options
    form.pais_prata.choices = paises_options
    form.pais_bronze.choices = paises_options

    return form


@app.get("/")
def index():
    user = session.get("user")
    if not user:
        return redirect(url_for("login"))

    check_user(user)
    categorias = get_categorias()
    modalidades = get_modalidades()
    paises = get_paises()
    paises_dict = {p.pais_id: p.pais_nome for p in paises}
    palpites = get_podios(user.get("oid"), paises)
    today = date.today()

    form = form_builder()

    return render_template(
        "index.html",
        today=today,
        categorias=categorias,
        modalidades=modalidades,
        palpites=palpites,
        form=form,
        user=user,
        version=msal.__version__,
        is_admin=is_admin(user),
        paises=paises_dict,
    )


@app.post("/")
def index_post():
    user = session.get("user")
    if not user:
        return redirect(url_for("login"))

    check_user(user)

    form = form_builder()
    form.validate()

    add_palpite(
        user.get("oid"),
        form.modalidade_id.data,
        form.pais_ouro.data,
        form.pais_prata.data,
        form.pais_bronze.data,
    )

    return "OK"


@app.get("/admin/")
def admin():
    user = session.get("user")
    if not user:
        return redirect(url_for("login"))

    if not is_admin(user):
        return redirect(url_for("index"))

    check_user(user)
    categorias = get_categorias()
    modalidades = get_modalidades()
    paises = {p.pais_id: p.pais_nome for p in get_paises()}
    today = date.today()

    form = form_builder()

    return render_template(
        "admin.html",
        today=today,
        categorias=categorias,
        modalidades=modalidades,
        paises=paises,
        form=form,
        user=user,
        version=msal.__version__,
        is_admin=True,
    )


@app.post("/admin/")
def admin_post():
    user = session.get("user")
    if not user:
        return redirect(url_for("login"))

    if user.get("oid") not in ADMIN_OIDS:
        return redirect(url_for("index"))

    check_user(user)

    form = form_builder()
    form.validate()

    add_resultado(
        form.modalidade_id.data, form.pais_ouro.data, form.pais_prata.data, form.pais_bronze.data,
    )

    return "OK"


@app.get("/regras")
def regras():
    user = session.get("user")
    if not user:
        return redirect(url_for("login"))

    check_user(user)

    return render_template(
        "regras.html", user=user, version=msal.__version__, is_admin=is_admin(user),
    )


@app.get("/resultados")
def resultados():
    user = session.get("user")
    if not user:
        return redirect(url_for("login"))

    check_user(user)
    users = get_users()

    return render_template(
        "resultados.html",
        user=user,
        version=msal.__version__,
        is_admin=is_admin(user),
        users=users,
    )
