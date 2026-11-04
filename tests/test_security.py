from datetime import UTC, datetime, timedelta

import pytest

from src.security import can_cancel

# Fecha fija: los resultados no dependen de la hora en que se ejecute la prueba.
NOW = datetime(2026, 10, 26, 12, 0, tzinfo=UTC)


def test_owner_within_24h():
    now = datetime.now(UTC)
    assert can_cancel("NEW", 1, 1, False, now - timedelta(hours=1), now)


def test_stranger_denied():
    now = datetime.now(UTC)
    assert not can_cancel("NEW", 1, 2, False, now, now)


def test_shipped_denied_even_admin():
    now = datetime.now(UTC)
    assert not can_cancel("SHIPPED", 1, 1, True, now, now)


def test_expired_denied():
    now = datetime.now(UTC)
    assert not can_cancel("NEW", 1, 1, False, now - timedelta(hours=25), now)


# ---------------------------------------------------------------- Paso 6 (E6)
def test_admin_cancela_pedido_new_de_otro_usuario():
    # usuario 99 es administrador; el pedido pertenece al usuario 1
    assert can_cancel("NEW", owner_id=1, user_id=99, is_admin=True,
                      created_at=NOW - timedelta(hours=2), now=NOW)


def test_propietario_exactamente_a_las_24h_es_rechazado():
    assert not can_cancel("NEW", owner_id=1, user_id=1, is_admin=False,
                          created_at=NOW - timedelta(hours=24), now=NOW)


def test_propietario_un_segundo_antes_de_24h_si_puede():
    assert can_cancel("NEW", owner_id=1, user_id=1, is_admin=False,
                      created_at=NOW - timedelta(hours=24) + timedelta(seconds=1), now=NOW)


def test_sin_now_usa_la_hora_actual():
    assert can_cancel("NEW", 1, 1, False, datetime.now(UTC) - timedelta(minutes=5))


# Matriz de autorizacion completa (E6): rol, propietario, estado, antiguedad -> resultado
MATRIZ = [
    # (rol,        es_propietario, estado,     horas, permitido)
    ("admin",      False,          "NEW",       2,    True),
    ("admin",      False,          "NEW",       48,   True),
    ("admin",      True,           "SHIPPED",   1,    False),
    ("cliente",    True,           "NEW",       1,    True),
    ("cliente",    True,           "NEW",       24,   False),
    ("cliente",    True,           "NEW",       25,   False),
    ("cliente",    True,           "SHIPPED",   1,    False),
    ("cliente",    False,          "NEW",       1,    False),
]


@pytest.mark.parametrize(("rol", "es_propietario", "estado", "horas", "permitido"), MATRIZ)
def test_matriz_de_autorizacion(rol, es_propietario, estado, horas, permitido):
    owner_id = 1
    user_id = 1 if es_propietario else 2
    created_at = NOW - timedelta(hours=horas)
    resultado = can_cancel(estado, owner_id, user_id, rol == "admin", created_at, NOW)
    assert resultado is permitido
