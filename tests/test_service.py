from unittest.mock import Mock

import pytest

from src.application import OrderService
from src.domain import Order


def test_gateway_approved():
    gateway = Mock()
    gateway.charge.return_value = True
    assert OrderService(gateway).checkout(Order(100)) == 100
    gateway.charge.assert_called_once_with(100)


def test_gateway_rejected():
    gateway = Mock()
    gateway.charge.return_value = False
    with pytest.raises(RuntimeError):
        OrderService(gateway).checkout(Order(100))


# ---------------------------------------------------------------- Paso 5 (E5)
def test_vip_200_rechazado_intenta_cobrar_170():
    gateway = Mock()
    gateway.charge.return_value = False  # la pasarela simulada rechaza el pago
    order = Order(200, vip=True)

    with pytest.raises(RuntimeError, match="payment rejected"):
        OrderService(gateway).checkout(order)

    gateway.charge.assert_called_once_with(170)  # se intento cobrar el importe con descuento
    # Riesgo documentado (ver README, E5): el pedido ya quedo CONFIRMED aunque el pago fallo.
    assert order.status == "CONFIRMED"


def test_vip_200_aprobado_cobra_170():
    gateway = Mock()
    gateway.charge.return_value = True
    assert OrderService(gateway).checkout(Order(200, vip=True)) == 170
    gateway.charge.assert_called_once_with(170)


def test_pedido_con_total_invalido_no_llega_a_la_pasarela():
    gateway = Mock()
    with pytest.raises(ValueError):
        OrderService(gateway).checkout(Order(0))
    gateway.charge.assert_not_called()  # nunca se intenta cobrar


def test_timeout_de_la_pasarela_se_propaga_sin_reintentar():
    gateway = Mock()
    gateway.charge.side_effect = TimeoutError("la pasarela no respondió")
    order = Order(100)
    with pytest.raises(TimeoutError):
        OrderService(gateway).checkout(order)
    gateway.charge.assert_called_once_with(100)  # un solo intento: no hay cobro duplicado
    assert order.status == "CONFIRMED"  # mismo riesgo de consistencia del paso 5
