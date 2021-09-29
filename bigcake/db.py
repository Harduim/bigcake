import json
import logging as log
from dataclasses import dataclass
from datetime import date
from typing import Dict, List

from sqlalchemy import Boolean, Column, Date, ForeignKey, Integer, String, Table, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.sql import text
from unidecode import unidecode

from . import CONN_URL, app

pais_id = "paises.pais_id"
engine = create_engine(CONN_URL, pool_size=20, max_overflow=30)
session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base = declarative_base()
Base.query = session.query_property()


@dataclass
class Podio:
    pais_ouro: str
    pais_prata: str
    pais_bronze: str


usuario_modalidade = Table(
    "usuarios_modalidades",
    Base.metadata,
    Column(
        "usuario_id",
        String(100),
        ForeignKey("usuarios.usuario_id"),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "modalidade_id",
        Integer,
        ForeignKey("modalidades.modalidade_id"),
        primary_key=True,
        nullable=False,
    ),
    Column("pais_ouro", Integer, ForeignKey(pais_id)),
    Column("pais_prata", Integer, ForeignKey(pais_id)),
    Column("pais_bronze", Integer, ForeignKey(pais_id)),
)


class Usuario(Base):
    __tablename__ = "usuarios"
    usuario_id = Column(String(100), primary_key=True, nullable=False)
    usuario_nome = Column(String(100))
    total_pontos = Column(Integer)


class Modalidade(Base):
    __tablename__ = "modalidades"
    modalidade_id = Column(Integer, primary_key=True, nullable=False)
    modalidade_nome = Column(String(100), nullable=False)
    mod_cat_id = Column(Integer, nullable=False)
    pais_ouro = Column(Integer, ForeignKey(pais_id))
    pais_prata = Column(Integer, ForeignKey(pais_id))
    pais_bronze = Column(Integer, ForeignKey(pais_id))
    desabilita_palpite = Column(Date)
    habilitado = Column(Boolean, default=True)


class CategoriaModalidade(Base):
    __tablename__ = "categoria_modalidades"
    cat_id = Column(Integer, primary_key=True, nullable=False)
    cat_nome = Column(String(100), nullable=False)
    cat_icon_url = Column(String(100), nullable=False)


class Pais(Base):
    __tablename__ = "paises"
    pais_id = Column(Integer, primary_key=True, nullable=False)
    pais_nome = Column(String(100), nullable=False)


def load_default_paises():
    with open("bigcake/config/paises.json") as f:
        paises = json.loads(f.read())

    for id, name in enumerate(sorted(paises), 1):
        engine.execute(f"INSERT INTO paises VALUES ({id}, '{name}')")


def load_default_modalidades():
    def norm(s: str):
        return unidecode(s).replace(" ", "_").lower()

    with open("bigcake/config/modalidades.json") as f:
        modalidades = json.loads(f.read())

    mod_categorias = {m.split(" - ")[0] for m, _, hab in modalidades if hab == "true"}
    mod_categorias = {m: (id, norm(m)) for id, m in enumerate(sorted(mod_categorias), 1)}

    for id, (mod, dt, habilitado) in enumerate(sorted(modalidades), 1):
        if habilitado != "true":
            continue
        mod_cat_id = mod_categorias[mod.split(" - ")[0]][0]
        engine.execute(
            f"""
            INSERT INTO modalidades
                (modalidade_id, modalidade_nome, mod_cat_id, desabilita_palpite, habilitado)
            VALUES ({id}, '{mod}', {mod_cat_id}, '{dt}', {habilitado.title()})"""
        )

    for nome, (id, murl) in mod_categorias.items():
        engine.execute(f"INSERT INTO categoria_modalidades VALUES ({id},'{nome}','{murl}.svg')")


def init_db():
    Base.metadata.create_all(bind=engine)


def reset_db():
    Base.metadata.drop_all(bind=engine)
    init_db()
    load_default_modalidades()
    load_default_paises()


def check_user(user: dict):
    oid = user.get("oid", False)
    username = user.get("name", False)
    if not all([oid, username]):
        raise TypeError

    db_user = session.query(Usuario).filter(Usuario.usuario_id == user.get("oid")).all()
    if not db_user:
        db_user = Usuario(usuario_id=oid, usuario_nome=username, total_pontos=0,)
        session.add(db_user)
        session.commit()


def get_categorias() -> List[CategoriaModalidade]:
    return session.query(CategoriaModalidade).all()


def get_modalidades() -> List[Modalidade]:
    return session.query(Modalidade).where(Modalidade.habilitado == True).all()


def get_paises() -> List[Pais]:
    return session.query(Pais).order_by(Pais.pais_nome).all()


def get_palpites(uid: str) -> Dict[int, tuple]:
    return (
        session.query(
            usuario_modalidade.c.modalidade_id,
            usuario_modalidade.c.pais_ouro,
            usuario_modalidade.c.pais_prata,
            usuario_modalidade.c.pais_bronze,
        )
        .where(usuario_modalidade.c.usuario_id == uid)
        .all()
    )


def get_podios(uid: str, paises: List[Pais]) -> Dict[int, Podio]:
    paises = {pais.pais_id: pais.pais_nome for pais in paises}
    palpites = (
        session.query(
            usuario_modalidade.c.modalidade_id,
            usuario_modalidade.c.pais_ouro,
            usuario_modalidade.c.pais_prata,
            usuario_modalidade.c.pais_bronze,
        )
        .where(usuario_modalidade.c.usuario_id == uid)
        .all()
    )
    return {
        m_id: Podio(paises[ouro], paises[prata], paises[bronze])
        for m_id, ouro, prata, bronze in palpites
    }


def get_users() -> List[Usuario]:
    return session.query(Usuario).order_by(Usuario.total_pontos.desc()).all()


def add_palpite(uid: str, modalidade_id: int, pais_ouro: int, pais_prata: int, pais_bronze: int):
    if not modalidade_id:
        log.warning("Empty modalidade_id uid:{uid}")
        return

    modalidade_id = int(modalidade_id)
    today = date.today()
    date_desabilita_palpite = (
        session.query(Modalidade.desabilita_palpite)
        .where(Modalidade.modalidade_id == modalidade_id)
        .one()[0]
    )
    if today > date_desabilita_palpite:
        return

    insert = text(
        """
        INSERT INTO usuarios_modalidades
        (usuario_id, modalidade_id, pais_ouro, pais_prata, pais_bronze)
        VALUES (:uid, :modalidade_id, :pais_ouro, :pais_prata, :pais_bronze)
        ON DUPLICATE KEY UPDATE 
            pais_ouro = VALUES(pais_ouro),
            pais_prata = VALUES(pais_prata),
            pais_bronze = VALUES(pais_bronze);
        """
    )
    engine.execute(
        insert,
        **{
            "uid": str(uid),
            "modalidade_id": modalidade_id,
            "pais_ouro": int(pais_ouro),
            "pais_prata": int(pais_prata),
            "pais_bronze": int(pais_bronze),
        },
    )


def add_resultado(modalidade_id: int, pais_ouro: int, pais_prata: int, pais_bronze: int):
    update_stmt = text(
        """
        UPDATE modalidades
        SET pais_ouro = :pais_ouro,
            pais_prata = :pais_prata,
            pais_bronze = :pais_bronze
        WHERE modalidade_id = :modalidade_id;
        """
    )
    engine.execute(
        update_stmt,
        **{
            "modalidade_id": int(modalidade_id),
            "pais_ouro": int(pais_ouro),
            "pais_prata": int(pais_prata),
            "pais_bronze": int(pais_bronze),
        },
    )


@app.teardown_appcontext
def shutdown_session(exception=None):
    session.remove()
