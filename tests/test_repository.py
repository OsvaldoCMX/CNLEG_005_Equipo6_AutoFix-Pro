import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.domain import Order
from src.repository import OrderRow, SqlOrderRepository, make_engine


def test_repository_commit():
    engine = make_engine()
    with Session(engine) as session:
        SqlOrderRepository(session).save(1, Order(120))
        session.commit()
        assert session.scalar(select(OrderRow).where(OrderRow.id == 1)).total == 120
    engine.dispose()


def test_repository_rollback():
    engine = make_engine()
    with Session(engine) as session:
        SqlOrderRepository(session).save(1, Order(120))
        session.rollback()
        assert session.scalar(select(OrderRow).where(OrderRow.id == 1)) is None
    engine.dispose()


# ---------------------------------------------------------------- Paso 4 (E4)
def test_repository_commit_id_2_total_250():
    engine = make_engine()  # SQLite en memoria: cada prueba tiene su propia base vacia
    order = Order(250)
    order.confirm()
    with Session(engine) as session:
        SqlOrderRepository(session).save(2, order)
        session.commit()

    # Se abre una sesion NUEVA para comprobar que el dato quedo guardado de verdad
    with Session(engine) as other_session:
        row = other_session.get(OrderRow, 2)
        assert row is not None
        assert row.id == 2
        assert row.total == 250
        assert row.status == "CONFIRMED"
    engine.dispose()


def test_repository_unicidad_id_duplicado():
    """Restricción de unicidad: la base rechaza dos pedidos con el mismo id."""
    engine = make_engine()
    with Session(engine) as session:
        SqlOrderRepository(session).save(3, Order(100))
        session.commit()
        SqlOrderRepository(session).save(3, Order(999))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
        assert session.get(OrderRow, 3).total == 100  # se conserva el primer registro
    engine.dispose()
