"""Cierra las bases SQLite en memoria que se abrieron durante cada prueba."""
import pytest
from escenarios import MOTORES_ABIERTOS


@pytest.fixture(autouse=True)
def cerrar_bases_de_datos():
    yield
    while MOTORES_ABIERTOS:
        MOTORES_ABIERTOS.pop().dispose()
