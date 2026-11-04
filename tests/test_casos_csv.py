"""Casos CP01-CP15 del profesor ejecutados desde los CSV con csv.DictReader.

Los CSV no se cargan solos: esta prueba los lee, arma cada pedido y compara el
resultado real contra el esperado. La matriz final queda en
reportes/matriz_laboratorio_resultados.csv.
"""
from __future__ import annotations

import csv
from pathlib import Path
from unittest.mock import Mock

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.application import OrderService
from src.domain import Order
from src.repository import OrderRow, SqlOrderRepository, make_engine

DATOS = Path(__file__).resolve().parents[1] / "datos"

# CP08 se escribio para el ciclo TDD: antes del paso 3 el codigo permitia confirmar dos
# veces. Despues de GREEN el resultado correcto es el rechazo, por eso se actualiza aqui.
EXPECTATIVAS_DESPUES_DE_TDD = {"CP08": "ValueError: already confirmed"}


def _leer(nombre: str) -> list[dict[str, str]]:
    with (DATOS / nombre).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


PEDIDOS = {p["pedido_id"]: p for p in _leer("pedidos_prueba.csv")}
CASOS = _leer("casos_de_prueba.csv")


def _describir_error(error: Exception) -> str:
    return f"{type(error).__name__}: {error}"


def ejecutar_caso(caso: dict[str, str]) -> str:
    """Ejecuta un caso y devuelve el resultado real con el mismo formato del CSV."""
    accion = caso["accion"]
    if accion == "confirmar":
        p = PEDIDOS[caso["pedido_id"]]
        order = Order(float(p["total"]), vip=p["es_vip"] == "1", status=p["estado_inicial"])
        try:
            cobro = order.confirm(customer_debt=float(p["deuda_cliente"]))
        except Exception as error:  # noqa: BLE001 - el tipo de error ES el resultado a comparar
            return _describir_error(error)
        return f"{order.status}, cobro {cobro:.2f}"

    if accion == "pago rechazado":
        gateway = Mock()
        gateway.charge.return_value = False
        try:
            OrderService(gateway).checkout(Order(100))
        except RuntimeError as error:
            return _describir_error(error)
        return "pago aceptado"

    engine = make_engine()
    with Session(engine) as session:
        SqlOrderRepository(session).save(1, Order(120))
        if accion == "persistencia commit":
            session.commit()
        else:
            session.rollback()
        fila = session.scalar(select(OrderRow).where(OrderRow.id == 1))
    engine.dispose()
    if accion == "persistencia commit":
        return "Registro visible después de commit" if fila else "Registro ausente después de commit"
    return "Registro ausente después de rollback" if fila is None else "Registro visible tras rollback"


def _coincide(real: str, esperado: str) -> bool:
    # "ValueError" en el CSV acepta "ValueError: <mensaje>" como resultado real
    return real == esperado or real.startswith(esperado + ":")


@pytest.mark.parametrize("caso", CASOS, ids=[c["caso_id"] for c in CASOS])
def test_caso_del_csv(caso, matriz):
    esperado = EXPECTATIVAS_DESPUES_DE_TDD.get(caso["caso_id"], caso["resultado_esperado"])
    real = ejecutar_caso(caso)
    fila = {
        "caso_id": caso["caso_id"],
        "pedido_id": caso["pedido_id"],
        "accion": caso["accion"],
        "resultado_esperado_original": caso["resultado_esperado"],
        "resultado_esperado": esperado,
    }
    matriz.anotar("matriz_laboratorio_resultados.csv", fila, real, _coincide(real, esperado))
    assert _coincide(real, esperado), f"{caso['caso_id']}: esperado {esperado!r}, real {real!r}"


def test_los_csv_tienen_los_15_casos_y_12_pedidos():
    assert len(CASOS) == 15
    assert len(PEDIDOS) == 12
