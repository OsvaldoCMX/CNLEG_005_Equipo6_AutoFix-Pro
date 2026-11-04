"""Paso 9 · Matriz del PIA AutoFix Pro (datos/matriz_pia_autofix.csv).

Cada fila del CSV es un caso (éxito, error o límite) de una regla aprobada en las User
Stories. La prueba arma el escenario, ejecuta el caso con los Application Services y
compara el resultado real contra el esperado. Cada caso corre dos veces: con los
repositorios en memoria y con la base de datos (SQLAlchemy + SQLite en memoria).
La matriz final queda en reportes/matriz_pia_autofix_resultados.csv.
"""
from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path

import pytest
from escenarios import (
    CLIENTE_FLOTILLA,
    CLIENTE_PARTICULAR,
    IMPLEMENTACIONES,
    TRABAJOS_NORMALES,
    crear_app,
    leer_cotizacion,
    leer_orden,
    orden_con_diagnostico,
    orden_cotizada,
    orden_en_diagnostico_sin_diagnostico,
)

from autofix.aplicacion.comandos import (
    GenerarCotizacion,
    RegistrarDecisionDelCliente,
    RegistrarEntrega,
    TrabajoPropuesto,
)
from autofix.dominio.compartido.errores import ErrorDeDominio
from autofix.dominio.compartido.valores import Dinero, NumeroOrden
from autofix.dominio.cotizaciones import eventos as ev
from autofix.dominio.cotizaciones.cotizacion import Cotizacion
from autofix.dominio.cotizaciones.linea_de_cotizacion import LineaDeCotizacion
from autofix.dominio.cotizaciones.politica_de_aprobacion import PoliticaPorMontoDeCotizacionInicial
from autofix.dominio.cotizaciones.valores import TipoCotizacion, VersionCotizacion
from autofix.dominio.ordenes.valores import FormaDePago, Pago

MATRIZ = Path(__file__).resolve().parents[2] / "datos" / "matriz_pia_autofix.csv"


def leer_matriz() -> list[dict[str, str]]:
    with MATRIZ.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


CASOS = leer_matriz()


def _parametros(texto: str) -> dict[str, str]:
    """'cliente=flotilla|pago=credito' -> {'cliente': 'flotilla', 'pago': 'credito'} (sin recortar valores)."""
    if not texto:
        return {}
    pares = (parte.split("=", 1) for parte in texto.split("|"))
    return {clave.strip(): valor for clave, valor in pares}


def _error(e: ErrorDeDominio) -> str:
    return type(e).__name__


def _alerta(app) -> str:
    alertas = [a.destinatario for a in getattr(app.publicador, "alertas", [])]
    return "alerta a Gerente de Taller" if "Gerente de Taller" in alertas else "sin alerta al Gerente"


def _un_trabajo(monto: str) -> tuple[TrabajoPropuesto, ...]:
    return (TrabajoPropuesto("Reparación de transmisión", Decimal(monto)),)


# ---------------------------------------------------------------------- R1 (CA-007, CA-016)
def cotizar_inicial(app, p):
    numero = orden_con_diagnostico(app)
    r = app.cotizacion.generar_cotizacion(GenerarCotizacion(numero, _un_trabajo(p["monto"])))
    return f"{r.estado}; {_alerta(app)}"


def presentar_sin_aprobacion(app, p):
    _, id_cot = orden_cotizada(app, trabajos=_un_trabajo(p["monto"]))
    try:
        with app.uow as uow:
            uow.cotizaciones.obtener(id_cot).marcar_presentada(app.reloj.ahora())
            uow.confirmar()
    except ErrorDeDominio as e:
        return f"{_error(e)}; cotización {leer_cotizacion(app, id_cot).estado.value}"
    return "presentada"


def cotizar_adicional(app, p):
    """CA-016: las adicionales (v.2 en adelante) no pasan por el Gerente, sin importar el monto."""
    numero, _ = orden_cotizada(app)
    lineas = [LineaDeCotizacion(1, "Falla adicional: bomba de agua", Dinero(Decimal(p["monto"])))]
    adicional = Cotizacion.generar("COT-ADIC", NumeroOrden(numero), TipoCotizacion.ADICIONAL,
                                   VersionCotizacion(2), lineas, PoliticaPorMontoDeCotizacionInicial(),
                                   app.reloj.ahora())
    pide_gerente = any(isinstance(e, ev.AprobacionGerencialRequerida) for e in adicional.extraer_eventos())
    alerta = "alerta a Gerente de Taller" if pide_gerente else "sin alerta al Gerente"
    return f"{adicional.estado.value}; {alerta}"


# ---------------------------------------------------------------------- R2 (CA-005, CA-033)
def cotizar_con_diagnostico(app, p):
    numero = orden_con_diagnostico(app)
    r = app.cotizacion.generar_cotizacion(GenerarCotizacion(numero, TRABAJOS_NORMALES))
    return f"{r.version}; orden {leer_orden(app, numero).estado.value}"


def cotizar_sin_diagnostico(app, p):
    numero = orden_en_diagnostico_sin_diagnostico(app)
    try:
        app.cotizacion.generar_cotizacion(GenerarCotizacion(numero, TRABAJOS_NORMALES))
    except ErrorDeDominio as e:
        with app.uow as uow:
            guardadas = len(uow.cotizaciones.cotizaciones_de_la_orden(NumeroOrden(numero)))
        return (f"{_error(e)}; cotizaciones guardadas: {guardadas}; "
                f"orden {leer_orden(app, numero).estado.value}")
    return "cotizada"


def diagnostico_vacio(app, p):
    numero = orden_en_diagnostico_sin_diagnostico(app)
    partes = []
    try:
        with app.uow as uow:
            uow.ordenes.obtener(NumeroOrden(numero)).registrar_diagnostico(p["texto"], app.reloj.ahora())
            uow.confirmar()
        partes.append("diagnóstico aceptado")
    except ErrorDeDominio as e:
        partes.append(_error(e))
    try:
        app.cotizacion.generar_cotizacion(GenerarCotizacion(numero, TRABAJOS_NORMALES))
        partes.append("al cotizar: cotizada")
    except ErrorDeDominio as e:
        partes.append(f"al cotizar: {_error(e)}")
    return "; ".join(partes)


def modificar_diagnostico_cotizado(app, p):
    numero, _ = orden_cotizada(app)
    original = leer_orden(app, numero).diagnostico
    try:
        with app.uow as uow:
            uow.ordenes.obtener(NumeroOrden(numero)).registrar_diagnostico("Otro diagnóstico",
                                                                           app.reloj.ahora())
            uow.confirmar()
    except ErrorDeDominio as e:
        conservado = leer_orden(app, numero).diagnostico == original
        return f"{_error(e)}; diagnóstico original {'conservado' if conservado else 'modificado'}"
    return "diagnóstico modificado"


# ---------------------------------------------------------------------- R3 (CA-029)
def registrar_decision(app, p):
    cliente = CLIENTE_FLOTILLA if p["cliente"] == "flotilla" else CLIENTE_PARTICULAR
    numero, id_cot = orden_cotizada(app, cliente=cliente)
    comando = RegistrarDecisionDelCliente(id_cot, (1, 2), p["autorizante"],
                                          es_responsable_de_flotilla=p["responsable"] == "si")
    try:
        r = app.autorizacion.registrar_decision_del_cliente(comando)
    except ErrorDeDominio as e:
        return (f"{_error(e)}; cotización {leer_cotizacion(app, id_cot).estado.value}; "
                f"orden {leer_orden(app, numero).estado.value}")
    return f"cotización {r.estado_cotizacion}; orden {r.estado_orden}"


# ---------------------------------------------------------------------- R4 (CA-026, CA-039, CA-041..043)
def entregar(app, p):
    cliente = CLIENTE_FLOTILLA if p["cliente"] == "flotilla" else CLIENTE_PARTICULAR
    numero, id_cot = orden_cotizada(app, cliente=cliente)
    partes = []
    if p.get("decision") == "rechazo_total":
        app.autorizacion.registrar_decision_del_cliente(
            RegistrarDecisionDelCliente(id_cot, (), cliente.nombre))
    else:
        autorizante = cliente.responsable.nombre if cliente.es_de_flotilla else cliente.nombre
        app.autorizacion.registrar_decision_del_cliente(
            RegistrarDecisionDelCliente(id_cot, (1, 2), autorizante, cliente.es_de_flotilla))
        partes += _terminar_y_cobrar(app, numero, p["pago"])
    try:
        r = app.entrega.registrar_entrega(RegistrarEntrega(numero))
    except ErrorDeDominio as e:
        return "; ".join([*partes, _error(e), f"orden {leer_orden(app, numero).estado.value}"])
    final = leer_orden(app, numero)
    partes.append(f"orden {r.estado_orden}")
    if final.cargo_a_credito:
        partes.append(f"crédito vence {final.cargo_a_credito.fecha_vencimiento.isoformat()}")
    if final.rechazo_total and final.pago is None:
        partes.append("sin cobro")
    return "; ".join(partes)


def _terminar_y_cobrar(app, numero: str, pago: str) -> list[str]:
    """Los técnicos terminan los trabajos y Caja registra el pago o el crédito (US-008, US-014)."""
    ahora = app.reloj.ahora()
    with app.uow as uow:
        orden = uow.ordenes.obtener(NumeroOrden(numero))
        for trabajo in orden.trabajos:
            orden.iniciar_trabajo(trabajo.id, ahora)
            orden.completar_trabajo(trabajo.id, ahora)
        uow.ordenes.guardar(orden)
        uow.confirmar()
    if pago == "ninguno":
        return []
    try:
        with app.uow as uow:
            orden = uow.ordenes.obtener(NumeroOrden(numero))
            if pago == "credito":
                orden.registrar_cargo_a_credito(ahora)
            else:
                monto = orden.total_autorizado if pago == "total" else Dinero(Decimal(pago))
                orden.registrar_pago(Pago(monto, FormaDePago.EFECTIVO, ahora))
            uow.ordenes.guardar(orden)
            uow.confirmar()
    except ErrorDeDominio as e:
        return [_error(e)]
    return []


ESCENARIOS = {
    "cotizar_inicial": cotizar_inicial,
    "presentar_sin_aprobacion": presentar_sin_aprobacion,
    "cotizar_adicional": cotizar_adicional,
    "cotizar_con_diagnostico": cotizar_con_diagnostico,
    "cotizar_sin_diagnostico": cotizar_sin_diagnostico,
    "diagnostico_vacio": diagnostico_vacio,
    "modificar_diagnostico_cotizado": modificar_diagnostico_cotizado,
    "registrar_decision": registrar_decision,
    "entregar": entregar,
}


def ejecutar_caso(caso: dict[str, str], implementacion: str) -> str:
    app = crear_app(implementacion)
    return ESCENARIOS[caso["escenario"]](app, _parametros(caso["parametros"]))


@pytest.mark.parametrize("implementacion", IMPLEMENTACIONES)
@pytest.mark.parametrize("caso", CASOS, ids=[c["id"] for c in CASOS])
def test_caso_de_la_matriz_pia(caso, implementacion, matriz):
    real = ejecutar_caso(caso, implementacion)
    fila = {
        "id": caso["id"], "implementacion": implementacion, "regla": caso["regla"],
        "criterio": caso["criterio"], "tipo": caso["tipo"], "entrada": caso["entrada"],
        "resultado_esperado": caso["resultado_esperado"],
    }
    matriz.anotar("matriz_pia_autofix_resultados.csv", fila, real, real == caso["resultado_esperado"])
    assert real == caso["resultado_esperado"]


def test_la_matriz_cubre_3_tipos_en_al_menos_3_reglas():
    """Requisito del paso 9: mínimo 3 reglas, cada una con éxito, error y límite (≥ 9 casos)."""
    tipos_por_regla: dict[str, set[str]] = {}
    for caso in CASOS:
        tipos_por_regla.setdefault(caso["regla"], set()).add(caso["tipo"])
    completas = [r for r, tipos in tipos_por_regla.items() if tipos == {"Éxito", "Error", "Límite"}]
    assert len(completas) >= 3
    assert len(CASOS) >= 9
    assert all(c["escenario"] in ESCENARIOS for c in CASOS)
