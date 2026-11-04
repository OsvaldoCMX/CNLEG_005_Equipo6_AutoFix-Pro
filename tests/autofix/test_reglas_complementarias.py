"""Pruebas unitarias complementarias del dominio de AutoFix Pro (sin base de datos).

Cubren invariantes y rechazos que el reporte de cobertura de ramas mostró sin probar.
Cada prueba verifica una regla del Glosario o de un criterio de aceptación.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from escenarios import CLIENTE_FLOTILLA, CLIENTE_PARTICULAR, INICIO, PLACAS

from autofix.dominio.clientes.cliente import Cliente, TipoCliente
from autofix.dominio.compartido.calendario import CalendarioHabil
from autofix.dominio.compartido.errores import (
    OperacionDeCotizacionNoPermitida,
    PagoNoPermitido,
    SolicitudNoPermitida,
    TrabajoNoEncontrado,
    TransicionDeEstadoNoPermitida,
    ValorInvalido,
)
from autofix.dominio.compartido.valores import Dinero, NumeroOrden, Placas
from autofix.dominio.cotizaciones.cotizacion import Cotizacion
from autofix.dominio.cotizaciones.linea_de_cotizacion import LineaDeCotizacion
from autofix.dominio.cotizaciones.politica_de_aprobacion import PoliticaPorMontoDeCotizacionInicial
from autofix.dominio.cotizaciones.valores import (
    Autorizante,
    DecisionDelCliente,
    RefaccionCotizada,
    RolDeAutorizante,
    TipoCotizacion,
    TrabajoDecidido,
    VersionCotizacion,
)
from autofix.dominio.ordenes.estados import EstadoOrden, EstadoTrabajo, validar_transicion
from autofix.dominio.ordenes.orden_de_servicio import OrdenDeServicio
from autofix.dominio.ordenes.trabajo import SolicitudDeCompra, Trabajo
from autofix.dominio.ordenes.valores import FormaDePago, Pago

MIL = Dinero(Decimal(1000))


def _linea(numero=1, monto=MIL):
    return LineaDeCotizacion(numero, "Cambio de balatas", monto)


def _cotizacion(tipo=TipoCotizacion.INICIAL, version=1):
    return Cotizacion.generar("COT-0001", NumeroOrden("OS-0001"), tipo, VersionCotizacion(version),
                              [_linea()], PoliticaPorMontoDeCotizacionInicial(), INICIO)


def _orden(cliente=CLIENTE_PARTICULAR, diagnostico=True):
    orden = OrdenDeServicio(NumeroOrden("OS-0001"), cliente.id, cliente.es_de_flotilla, Placas(PLACAS),
                            "Ruido al frenar", INICIO)
    orden.asignar_tecnico_para_diagnostico("Técnico Juan", INICIO)
    if diagnostico:
        orden.registrar_diagnostico("Balatas gastadas", INICIO)
    return orden


def _decision(autorizados, no_autorizados=(), tipo=TipoCotizacion.INICIAL):
    return DecisionDelCliente(tuple(autorizados), tuple(no_autorizados),
                              Autorizante("María López", RolDeAutorizante.CLIENTE), INICIO, tipo)


def _orden_autorizada(cliente=CLIENTE_PARTICULAR, trabajos=1):
    orden = _orden(cliente)
    orden.marcar_cotizada(INICIO)
    orden.aplicar_decision(_decision([TrabajoDecidido(i, f"Trabajo {i}", MIL)
                                      for i in range(1, trabajos + 1)]))
    return orden


def _terminada(cliente=CLIENTE_PARTICULAR):
    orden = _orden_autorizada(cliente)
    orden.iniciar_trabajo(1, INICIO)
    orden.completar_trabajo(1, INICIO)
    return orden


# ------------------------------------------------------------------ Value Objects y Cliente
def test_un_importe_no_puede_ser_negativo():
    with pytest.raises(ValorInvalido, match="negativo"):
        Dinero(Decimal("-0.01"))


def test_las_placas_no_pueden_estar_vacias():
    with pytest.raises(ValorInvalido):
        Placas("  -  ")


def test_cliente_de_flotilla_sin_responsable_no_se_puede_registrar():
    """CA-028: una flotilla siempre tiene empresa y Responsable de Flotilla."""
    with pytest.raises(ValorInvalido, match="Responsable de Flotilla"):
        Cliente("CLI-9", "Transportes X", TipoCliente.FLOTILLA, empresa="Transportes X")


@pytest.mark.parametrize("crear", [
    lambda: VersionCotizacion(0),
    lambda: RefaccionCotizada("  ", 1, MIL),
    lambda: RefaccionCotizada("Bujía", 0, MIL),
    lambda: Autorizante("  ", RolDeAutorizante.CLIENTE),
    lambda: LineaDeCotizacion(0, "Afinación", MIL),
    lambda: LineaDeCotizacion(1, "   ", MIL),
], ids=["version-0", "refaccion-sin-descripcion", "refaccion-cantidad-0", "autorizante-sin-nombre",
        "linea-0", "linea-sin-descripcion"])
def test_datos_invalidos_de_la_cotizacion_se_rechazan(crear):
    with pytest.raises(ValorInvalido):
        crear()


# ------------------------------------------------------------------ Calendario hábil (CA-023)
def test_dias_habiles_no_cuentan_fin_de_semana():
    viernes = date(2026, 10, 16)
    assert CalendarioHabil().dias_habiles_entre(viernes, viernes + timedelta(days=3)) == 1  # lunes


def test_dias_habiles_con_fechas_invertidas_es_cero():
    assert CalendarioHabil().dias_habiles_entre(date(2026, 10, 16), date(2026, 10, 12)) == 0


# ------------------------------------------------------------------ Cotización
def test_la_cotizacion_inicial_siempre_es_v1():
    with pytest.raises(ValorInvalido, match="versión 1"):
        _cotizacion(TipoCotizacion.INICIAL, 2)


def test_la_cotizacion_adicional_es_v2_o_posterior():
    with pytest.raises(ValorInvalido, match="versión 2"):
        _cotizacion(TipoCotizacion.ADICIONAL, 1)


def test_no_se_repite_un_trabajo_en_la_cotizacion():
    with pytest.raises(ValorInvalido, match="repetido"):
        Cotizacion.generar("COT-1", NumeroOrden("OS-1"), TipoCotizacion.INICIAL, VersionCotizacion(1),
                           [_linea(1), _linea(1)], PoliticaPorMontoDeCotizacionInicial(), INICIO)


def test_presentar_inicia_el_plazo_de_48_horas():
    cotizacion = _cotizacion()
    cotizacion.marcar_presentada(INICIO)
    assert cotizacion.fecha_presentacion == INICIO


def test_no_se_autoriza_un_trabajo_que_no_esta_en_la_cotizacion():
    with pytest.raises(ValorInvalido, match="no tiene los trabajos"):
        _cotizacion().registrar_decision({1, 7}, Autorizante("María López", RolDeAutorizante.CLIENTE),
                                         INICIO)


def test_la_decision_del_cliente_se_registra_una_sola_vez():
    cotizacion = _cotizacion()
    autorizante = Autorizante("María López", RolDeAutorizante.CLIENTE)
    cotizacion.registrar_decision({1}, autorizante, INICIO)
    with pytest.raises(OperacionDeCotizacionNoPermitida):
        cotizacion.registrar_decision({1}, autorizante, INICIO)


# ------------------------------------------------------------------ Orden de Servicio: estados
def test_transicion_no_permitida_se_rechaza():
    with pytest.raises(TransicionDeEstadoNoPermitida, match="Recibida"):
        validar_transicion(EstadoOrden.RECIBIDA, EstadoOrden.CERRADA)


def test_el_diagnostico_solo_se_registra_en_diagnostico():
    orden = OrdenDeServicio(NumeroOrden("OS-1"), "CLI-001", False, Placas(PLACAS), "Revisión", INICIO)
    with pytest.raises(TransicionDeEstadoNoPermitida):
        orden.registrar_diagnostico("Balatas gastadas", INICIO)


def test_rechazo_total_solo_de_una_orden_cotizada():
    orden = _orden_autorizada()
    with pytest.raises(TransicionDeEstadoNoPermitida, match="Cotizada"):
        orden.aplicar_decision(_decision([]))


def test_cotizacion_adicional_autorizada_agrega_trabajos_sin_cambiar_el_estado():
    """CA-017/CA-018: la falla adicional autorizada se suma y la orden sigue su curso."""
    orden = _orden_autorizada()
    orden.aplicar_decision(_decision([TrabajoDecidido(1, "Bomba de agua", MIL)],
                                     tipo=TipoCotizacion.ADICIONAL))
    assert orden.estado is EstadoOrden.AUTORIZADA
    assert str(orden.total_autorizado) == "$2,000.00 MXN"


# ------------------------------------------------------------------ Refacciones (CA-019, CA-020, CA-022)
def test_no_se_piden_refacciones_con_la_orden_lista_para_entrega():
    with pytest.raises(SolicitudNoPermitida, match="Lista para Entrega"):
        _terminada().crear_solicitud_de_compra(1, "Balatas", 1, INICIO)


@pytest.mark.parametrize(("refaccion", "cantidad"), [("Balatas", 0), ("   ", 1)])
def test_la_solicitud_necesita_refaccion_y_cantidad(refaccion, cantidad):
    with pytest.raises(SolicitudNoPermitida, match="cantidad mayor a cero"):
        _orden_autorizada().crear_solicitud_de_compra(1, refaccion, cantidad, INICIO)


def test_la_orden_sigue_en_espera_hasta_que_llegan_todas_las_refacciones():
    orden = _orden_autorizada()
    orden.crear_solicitud_de_compra(1, "Balatas", 1, INICIO)
    orden.crear_solicitud_de_compra(1, "Disco", 2, INICIO)            # ya estaba en espera
    orden.registrar_llegada_de_refaccion(1, INICIO)
    assert orden.estado is EstadoOrden.EN_ESPERA_DE_REFACCION        # falta el disco
    orden.registrar_llegada_de_refaccion(2, INICIO)
    assert orden.estado is EstadoOrden.AUTORIZADA


def test_una_refaccion_no_se_registra_dos_veces_como_disponible():
    solicitud = SolicitudDeCompra(1, 1, "Balatas", 1, INICIO)
    solicitud.marcar_disponible(INICIO)
    with pytest.raises(TransicionDeEstadoNoPermitida):
        solicitud.marcar_disponible(INICIO)


def test_un_trabajo_pendiente_no_se_puede_completar_sin_iniciarlo():
    with pytest.raises(TransicionDeEstadoNoPermitida):
        Trabajo(1, "Afinación", MIL, EstadoTrabajo.PENDIENTE).completar()


def test_trabajo_inexistente_responde_con_error_del_negocio():
    with pytest.raises(TrabajoNoEncontrado, match="trabajo 9"):
        _orden_autorizada().iniciar_trabajo(9, INICIO)


def test_la_orden_queda_lista_solo_cuando_terminan_todos_los_trabajos():
    """CA-015."""
    orden = _orden_autorizada(trabajos=2)
    orden.iniciar_trabajo(1, INICIO)
    orden.completar_trabajo(1, INICIO)
    assert orden.estado is EstadoOrden.EN_REPARACION
    orden.iniciar_trabajo(2, INICIO)
    orden.completar_trabajo(2, INICIO)
    assert orden.estado is EstadoOrden.LISTA_PARA_ENTREGA


# ------------------------------------------------------------------ Caja (CA-026, CA-039)
def test_una_flotilla_no_paga_de_contado():
    with pytest.raises(PagoNoPermitido, match="cargo a crédito"):
        _terminada(CLIENTE_FLOTILLA).registrar_pago(Pago(MIL, FormaDePago.EFECTIVO, INICIO))


def test_un_cliente_particular_no_tiene_credito():
    with pytest.raises(PagoNoPermitido, match="solo aplica a clientes de flotilla"):
        _terminada(CLIENTE_PARTICULAR).registrar_cargo_a_credito(INICIO)
