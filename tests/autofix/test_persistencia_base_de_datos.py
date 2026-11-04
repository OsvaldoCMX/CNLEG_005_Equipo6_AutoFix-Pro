"""Paso 9 · Integración con la base de datos (SQLAlchemy + SQLite en memoria).

SQLite en memoria es el motor de PRUEBA: cada prueba crea una base nueva y vacía que
desaparece al terminar, así nunca se tocan datos reales. La base de datos del
Data Center se conectará en el proyecto final con otra URL (ADR-004).
"""
from __future__ import annotations

import pytest
from escenarios import (
    CLIENTE_FLOTILLA,
    IMPLEMENTACIONES,
    TRABAJOS_COSTOSOS,
    crear_app,
    leer_cotizacion,
    leer_orden,
    nueva_app_con_base_de_datos,
    orden_autorizada,
    orden_con_diagnostico,
    orden_cotizada,
    orden_en_diagnostico_sin_diagnostico,
)
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from autofix.aplicacion.comandos import (
    CrearSolicitudDeCompra,
    GenerarCotizacion,
    RegistrarDecisionDelCliente,
    RegistrarEntrega,
    RevisarCotizacion,
)
from autofix.aplicacion.consultas.consultas import (
    ConsultarEstadoDeOrden,
    ListarCotizacionesPendientesDeAprobacion,
    ListarSolicitudesPendientes,
)
from autofix.dominio.compartido.errores import (
    AutorizanteNoValido,
    ClienteNoEncontrado,
    CotizacionNoEncontrada,
    CotizacionSinTrabajos,
    DiagnosticoRequerido,
    OrdenNoEncontrada,
    ValorInvalido,
)
from autofix.dominio.compartido.valores import NumeroOrden, Placas
from autofix.dominio.ordenes.orden_de_servicio import OrdenDeServicio
from autofix.dominio.ordenes.valores import FormaDePago, Pago
from autofix.infraestructura.base_de_datos.tablas import (
    CotizacionFila,
    LineaDeCotizacionFila,
    OrdenFila,
    RefaccionCotizadaFila,
    TrabajoFila,
)


@pytest.fixture
def app():
    return nueva_app_con_base_de_datos()      # conftest.py cierra la base al terminar


def contar(app, tabla) -> int:
    with Session(app.motor) as sesion:
        return sesion.scalar(select(func.count()).select_from(tabla))


# ------------------------------------------------------------------ commit
def test_commit_la_cotizacion_queda_guardada_con_sus_lineas_y_refacciones(app):
    numero, id_cot = orden_cotizada(app)

    with Session(app.motor) as sesion:                      # consulta directa a las tablas
        fila = sesion.get(CotizacionFila, id_cot)
        assert (fila.version, fila.estado, fila.total_centavos) == (
            1, "Pendiente de Autorización del Cliente", 630_000)
        assert sesion.get(OrdenFila, numero).estado == "Cotizada"
    assert contar(app, LineaDeCotizacionFila) == 2
    assert contar(app, RefaccionCotizadaFila) == 2

    cotizacion = leer_cotizacion(app, id_cot)             # y se reconstruye el Aggregate
    assert str(cotizacion.total) == "$6,300.00 MXN"
    assert [linea.descripcion for linea in cotizacion.lineas] == [
        "Cambio de balatas delanteras", "Afinación mayor"]
    assert cotizacion.lineas[1].refacciones[0].cantidad == 4


# ------------------------------------------------------------------ rollback
def test_rollback_sin_diagnostico_no_se_guarda_nada(app):
    numero = orden_en_diagnostico_sin_diagnostico(app)

    with pytest.raises(DiagnosticoRequerido):
        app.cotizacion.generar_cotizacion(GenerarCotizacion(numero, TRABAJOS_COSTOSOS))

    assert contar(app, CotizacionFila) == 0
    assert leer_orden(app, numero).estado.value == "En Diagnóstico"


def test_rollback_deshace_lo_que_ya_se_habia_escrito_en_la_transaccion(app):
    """El folio COT-0001 ya se había escrito (flush) cuando falló la regla; el rollback lo revierte."""
    numero = orden_con_diagnostico(app)

    with pytest.raises(CotizacionSinTrabajos):                # cotización sin ningún trabajo
        app.cotizacion.generar_cotizacion(GenerarCotizacion(numero, ()))

    with Session(app.motor) as sesion:
        folios = sesion.execute(text("SELECT COUNT(*) FROM secuencias WHERE nombre = 'cotizaciones'"))
        assert folios.scalar() == 0
    assert leer_orden(app, numero).estado.value == "En Diagnóstico"
    r = app.cotizacion.generar_cotizacion(GenerarCotizacion(numero, TRABAJOS_COSTOSOS))
    assert r.id_cotizacion == "COT-0001"                      # el folio no se "gastó"


def test_rollback_si_falla_a_la_mitad_no_queda_nada_a_medias(app):
    numero = orden_con_diagnostico(app)
    with pytest.raises(RuntimeError), app.uow as uow:
        uow.ordenes.obtener(NumeroOrden(numero)).marcar_cotizada(app.reloj.ahora())
        raise RuntimeError("falla simulada antes de confirmar")
    assert leer_orden(app, numero).estado.value == "En Diagnóstico"


# ------------------------------------------------------------------ ADR-002: dos Aggregates juntos o ninguno
def test_decision_rechazada_no_modifica_ni_cotizacion_ni_orden(app):
    numero, id_cot = orden_cotizada(app, cliente=CLIENTE_FLOTILLA)

    with pytest.raises(AutorizanteNoValido):
        app.autorizacion.registrar_decision_del_cliente(
            RegistrarDecisionDelCliente(id_cot, (1, 2), "Pedro, conductor"))

    with Session(app.motor) as sesion:
        assert sesion.get(CotizacionFila, id_cot).estado == "Pendiente de Autorización del Cliente"
        assert sesion.get(OrdenFila, numero).estado == "Cotizada"
    assert contar(app, TrabajoFila) == 0


def test_decision_valida_guarda_cotizacion_orden_y_trabajos_en_la_misma_transaccion(app):
    numero, id_cot = orden_cotizada(app)
    app.autorizacion.registrar_decision_del_cliente(
        RegistrarDecisionDelCliente(id_cot, (1,), "María López"))

    with Session(app.motor) as sesion:
        assert sesion.get(CotizacionFila, id_cot).estado == "Autorizada Parcialmente"
        assert sesion.get(OrdenFila, numero).estado == "Autorizada"
        trabajos = sesion.scalars(select(TrabajoFila).order_by(TrabajoFila.id)).all()
        assert [(t.estado, t.importe_centavos) for t in trabajos] == [
            ("Pendiente", 240_000), ("No Autorizado", 390_000)]
    decision = leer_cotizacion(app, id_cot).decision
    assert decision.autorizante.nombre == "María López"
    assert len(decision.autorizados) == 1


# ------------------------------------------------------------------ flujo completo persistido
def test_flujo_completo_hasta_la_entrega_queda_guardado(app):
    numero, id_cot = orden_cotizada(app, trabajos=TRABAJOS_COSTOSOS)
    app.aprobacion_gerencial.revisar_cotizacion(RevisarCotizacion(id_cot, aprobada=True))
    app.autorizacion.registrar_decision_del_cliente(RegistrarDecisionDelCliente(id_cot, (1,), "María López"))
    app.refacciones.crear_solicitud_de_compra(CrearSolicitudDeCompra(numero, 1, "Kit de embrague", 1))
    with app.uow as uow:
        orden = uow.ordenes.obtener(NumeroOrden(numero))
        orden.registrar_llegada_de_refaccion(1, app.reloj.ahora())
        orden.iniciar_trabajo(1, app.reloj.ahora())
        orden.completar_trabajo(1, app.reloj.ahora())
        orden.registrar_pago(Pago(orden.total_autorizado, FormaDePago.TARJETA, app.reloj.ahora()))
        uow.confirmar()

    r = app.entrega.registrar_entrega(RegistrarEntrega(numero))

    assert r.estado_orden == "Cerrada"
    final = leer_orden(app, numero)
    assert final.pago.forma is FormaDePago.TARJETA
    assert str(final.pago.monto) == "$18,500.00 MXN"
    assert final.solicitudes[0].estado.value == "Disponible"
    assert final.fecha_entrega == app.reloj.ahora()


# ------------------------------------------------------------------ lado de lectura (CQRS) sobre la base
def test_consultas_leen_lo_guardado_en_la_base(app):
    numero, _ = orden_autorizada(app)
    app.refacciones.crear_solicitud_de_compra(CrearSolicitudDeCompra(numero, 1, "Juego de balatas", 1))
    _, id_costosa = orden_cotizada(app, trabajos=TRABAJOS_COSTOSOS)
    app.reloj.avanzar(days=3)                                   # lunes -> jueves

    vista = app.consultar_estado.ejecutar(ConsultarEstadoDeOrden(numero, "abc-123 d"))
    assert vista.estado == "En Espera de Refacción"
    assert app.consultar_estado.ejecutar(ConsultarEstadoDeOrden(numero, "OTRA")) == \
        "No se encontró una orden con esos datos"
    assert app.consultar_estado.ejecutar(ConsultarEstadoDeOrden("", "ABC")) == \
        "No se encontró una orden con esos datos"
    pendientes = app.solicitudes_pendientes.ejecutar(ListarSolicitudesPendientes())
    assert [(s.refaccion, s.dias_habiles_transcurridos) for s in pendientes] == [("Juego de balatas", 3)]
    por_aprobar = app.cotizaciones_por_aprobar.ejecutar(ListarCotizacionesPendientesDeAprobacion())
    assert [(c.id_cotizacion, c.total) for c in por_aprobar] == [(id_costosa, "$18,500.00 MXN")]


# ------------------------------------------------------------------ restricciones de la base
def test_la_base_rechaza_una_orden_de_un_cliente_que_no_existe(app):
    with pytest.raises(IntegrityError), app.uow as uow:      # llave foránea activa en SQLite
        uow.ordenes.agregar(OrdenDeServicio(NumeroOrden("OS-0500"), "CLI-NO-EXISTE", False,
                                            Placas("XYZ1"), "Revisión", app.reloj.ahora()))
        uow.confirmar()
    assert contar(app, OrdenFila) == 0


# ------------------------------------------------------------------ mismo contrato en memoria y en base (principio L)
@pytest.mark.parametrize("implementacion", IMPLEMENTACIONES)
def test_contrato_obtener_inexistente_responde_con_error_del_negocio(implementacion):
    app = crear_app(implementacion)
    with app.uow as uow:
        with pytest.raises(OrdenNoEncontrada):
            uow.ordenes.obtener(NumeroOrden("OS-9999"))
        with pytest.raises(CotizacionNoEncontrada):
            uow.cotizaciones.obtener("COT-9999")
        with pytest.raises(ClienteNoEncontrado):
            uow.clientes.obtener("CLI-9999")


@pytest.mark.parametrize("implementacion", IMPLEMENTACIONES)
def test_contrato_no_se_puede_agregar_dos_veces_la_misma_orden(implementacion):
    app = crear_app(implementacion)
    numero = orden_con_diagnostico(app)
    with pytest.raises(ValorInvalido, match="ya existe"), app.uow as uow:
        uow.ordenes.agregar(OrdenDeServicio(NumeroOrden(numero), "CLI-001", False, Placas("XYZ1"),
                                            "Revisión", app.reloj.ahora()))


@pytest.mark.parametrize("implementacion", IMPLEMENTACIONES)
def test_contrato_folios_consecutivos(implementacion):
    app = crear_app(implementacion)
    assert [orden_con_diagnostico(app) for _ in range(3)] == ["OS-0001", "OS-0002", "OS-0003"]
