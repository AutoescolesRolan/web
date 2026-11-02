"""Base de dades de la web (SQLite en local, Postgres a Render via DATABASE_URL)."""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

_url = (os.environ.get("DATABASE_URL") or "sqlite:///./rolan_web.db").strip()
if _url.startswith("postgres://"):          # Render dona l'adreça amb l'esquema antic
    _url = "postgresql://" + _url[len("postgres://"):]
URL = _url

_kw = {"pool_pre_ping": True}
if URL.startswith("sqlite"):
    _kw["connect_args"] = {"check_same_thread": False}
engine = create_engine(URL, **_kw)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
