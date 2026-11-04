import pytest

from src.domain import CustomerHasDebt, Order


def test_vip_discount():
    o = Order(100, vip=True)
    assert o.confirm() == 85
    assert o.status == "CONFIRMED"


def test_regular_no_discount():
    assert Order(100).confirm() == 100


def test_customer_debt():
    with pytest.raises(CustomerHasDebt):
        Order(100).confirm(customer_debt=50)


@pytest.mark.parametrize("total", [0, -1])
def test_invalid_total(total):
    with pytest.raises(ValueError, match="total must be positive"):
        Order(total).confirm()


# ---------------------------------------------------------------- Paso 2 (E2)
def test_vip_200_paga_170():
    # Arrange
    order = Order(200, vip=True)
    # Act
    amount = order.confirm()
    # Assert
    assert amount == 170
    assert order.discount == 30
    assert order.status == "CONFIRMED"


def test_regular_200_paga_200():
    order = Order(200)
    amount = order.confirm()
    assert amount == 200
    assert order.discount == 0
    assert order.status == "CONFIRMED"


# ---------------------------------------------------------------- Paso 3 (E3) TDD
def test_cannot_confirm_twice():
    order = Order(100)
    order.confirm()
    with pytest.raises(ValueError, match="already confirmed"):
        order.confirm()


def test_second_confirm_keeps_first_result():
    """REFACTOR: el segundo intento no debe alterar el descuento ni el estado."""
    order = Order(200, vip=True)
    order.confirm()
    with pytest.raises(ValueError):
        order.confirm()
    assert order.discount == 30
    assert order.status == "CONFIRMED"
