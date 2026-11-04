"""TDD en el PIA (CA-005): un diagnóstico vacío no es un diagnóstico registrado.

RED: esta prueba se escribió antes de cambiar OrdenDeServicio y falló porque el
dominio aceptaba un diagnóstico con solo espacios y la orden se podía cotizar.
"""
import pytest
from escenarios import CLIENTE_PARTICULAR, INICIO, PLACAS

from autofix.dominio.compartido.errores import ValorInvalido
from autofix.dominio.compartido.valores import NumeroOrden, Placas
from autofix.dominio.ordenes.orden_de_servicio import OrdenDeServicio


def _orden_en_diagnostico() -> OrdenDeServicio:
    orden = OrdenDeServicio(NumeroOrden("OS-0001"), CLIENTE_PARTICULAR.id, False, Placas(PLACAS),
                            "Ruido al frenar", INICIO)
    orden.asignar_tecnico_para_diagnostico("Técnico Juan", INICIO)
    return orden


@pytest.mark.parametrize("texto", ["", "   ", "\n\t"])
def test_diagnostico_vacio_se_rechaza(texto):
    orden = _orden_en_diagnostico()
    with pytest.raises(ValorInvalido, match="describir la falla"):
        orden.registrar_diagnostico(texto, INICIO)
    assert orden.diagnostico is None


def test_diagnostico_con_texto_se_guarda_sin_espacios_sobrantes():
    orden = _orden_en_diagnostico()
    orden.registrar_diagnostico("  Balatas gastadas  ", INICIO)
    assert orden.diagnostico == "Balatas gastadas"
