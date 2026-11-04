"""Creación del motor y de las tablas.

URL_DE_PRUEBA es SQLite en memoria: solo existe mientras corre la prueba y no toca
datos reales. El sistema final usará la base de datos del Data Center; para
conectarla basta con pasar otra URL a crear_motor() (ADR-004).
"""
from __future__ import annotations

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from autofix.infraestructura.base_de_datos.tablas import Base

URL_DE_PRUEBA = "sqlite+pysqlite:///:memory:"


def crear_motor(url: str = URL_DE_PRUEBA) -> Engine:
    if url.startswith("sqlite") and ":memory:" in url:
        # Una sola conexión compartida: todas las sesiones de la prueba ven la misma base.
        motor = create_engine(url, poolclass=StaticPool, connect_args={"check_same_thread": False})
    else:
        motor = create_engine(url)
    if motor.dialect.name == "sqlite":
        event.listen(motor, "connect", _activar_llaves_foraneas)
    Base.metadata.create_all(motor)
    return motor


def crear_fabrica_de_sesiones(motor: Engine) -> sessionmaker[Session]:
    return sessionmaker(motor, expire_on_commit=False)


def _activar_llaves_foraneas(conexion, _registro) -> None:
    # SQLite no revisa las llaves foráneas si no se le pide.
    cursor = conexion.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
