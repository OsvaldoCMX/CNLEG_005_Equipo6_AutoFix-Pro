"""Datos y pasos previos compartidos por las pruebas.

Los pasos que no son parte de los 5 casos de uso detallados (recepción, diagnóstico,
inicio de trabajos, pago) se ejecutan directamente sobre el dominio dentro de una
Unidad de Trabajo, para preparar el escenario.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from autofix.aplicacion.comandos import (
    GenerarCotizacion,
    RefaccionPropuesta,
    RegistrarDecisionDelCliente,
    TrabajoPropuesto,
)
from autofix.composicion import construir_aplicacion, construir_aplicacion_con_base_de_datos
from autofix.dominio.clientes.cliente import Cliente, ResponsableDeFlotilla, TipoCliente
from autofix.dominio.compartido.valores import Dinero, NumeroOrden, Placas
from autofix.dominio.cotizaciones.cotizacion import Cotizacion
from autofix.dominio.ordenes.orden_de_servicio import OrdenDeServicio
from autofix.dominio.ordenes.valores import FormaDePago, Pago
from autofix.infraestructura.adaptadores import RelojFijo

INICIO = datetime(2026, 10, 12, 9, 0)  # noqa: DTZ001 - lunes, hora local
PLACAS = "ABC-123-D"

CLIENTE_PARTICULAR = Cliente("CLI-001", "María López", TipoCliente.PARTICULAR)
CLIENTE_FLOTILLA = Cliente("CLI-002", "Transportes del Norte", TipoCliente.FLOTILLA,
                           empresa="Transportes del Norte",
                           responsable=ResponsableDeFlotilla("Carlos Ruiz", "8112345678", "carlos@tdn.mx"))

# Cotización de $6,300 (no requiere Gerente): balatas $2,400 + afinación $3,900
TRABAJOS_NORMALES = (
    TrabajoPropuesto("Cambio de balatas delanteras", Decimal(900),
                     (RefaccionPropuesta("Juego de balatas", 1, Decimal(1500)),)),
    TrabajoPropuesto("Afinación mayor", Decimal(1500),
                     (RefaccionPropuesta("Bujía", 4, Decimal(600)),)),
)
# Cotización de $18,500 (requiere Gerente)
TRABAJOS_COSTOSOS = (
    TrabajoPropuesto("Reparación de transmisión", Decimal(6500),
                     (RefaccionPropuesta("Kit de embrague", 1, Decimal(12000)),)),
)


def nueva_app(**adaptadores):
    return construir_aplicacion(RelojFijo(INICIO), **adaptadores)


MOTORES_ABIERTOS: list = []      # conftest.py los cierra al terminar cada prueba


def nueva_app_con_base_de_datos(**adaptadores):
    """U5: los mismos servicios sobre SQLAlchemy + SQLite en memoria (base nueva y vacía)."""
    app = construir_aplicacion_con_base_de_datos(reloj=RelojFijo(INICIO), **adaptadores)
    MOTORES_ABIERTOS.append(app.motor)
    return app


IMPLEMENTACIONES = ("memoria", "base_de_datos")


def crear_app(implementacion: str, **adaptadores):
    """adaptadores: publicador= y/o documentos= (por ejemplo, un Mock)."""
    if implementacion == "memoria":
        return nueva_app(**adaptadores)
    return nueva_app_con_base_de_datos(**adaptadores)


def orden_con_diagnostico(app, cliente: Cliente = CLIENTE_PARTICULAR) -> str:
    """Recepción (US-001), asignación (US-020) y diagnóstico (US-019)."""
    with app.uow as uow:
        uow.clientes.agregar(cliente)
        numero = uow.ordenes.siguiente_numero()
        orden = OrdenDeServicio(numero, cliente.id, cliente.es_de_flotilla, Placas(PLACAS),
                                "Ruido al frenar", app.reloj.ahora())
        orden.asignar_tecnico_para_diagnostico("Técnico Juan", app.reloj.ahora())
        orden.registrar_diagnostico("Balatas gastadas y bujías dañadas", app.reloj.ahora())
        uow.ordenes.agregar(orden)
        uow.confirmar()
    return str(numero)


def orden_cotizada(app, cliente: Cliente = CLIENTE_PARTICULAR, trabajos=TRABAJOS_NORMALES):
    numero = orden_con_diagnostico(app, cliente)
    resultado = app.cotizacion.generar_cotizacion(GenerarCotizacion(numero, trabajos))
    return numero, resultado.id_cotizacion


def orden_autorizada(app, lineas=(1, 2)):
    numero, id_cot = orden_cotizada(app)
    app.autorizacion.registrar_decision_del_cliente(
        RegistrarDecisionDelCliente(id_cot, tuple(lineas), "María López"))
    return numero, id_cot


def completar_y_pagar(app, numero: str) -> None:
    """US-008 y US-014: se ejecutan los trabajos y Caja registra el pago."""
    with app.uow as uow:
        orden = uow.ordenes.obtener(NumeroOrden(numero))
        for trabajo in orden.trabajos:
            if trabajo.esta_autorizado:
                orden.iniciar_trabajo(trabajo.id, app.reloj.ahora())
                orden.completar_trabajo(trabajo.id, app.reloj.ahora())
        orden.registrar_pago(Pago(orden.total_autorizado, FormaDePago.TARJETA, app.reloj.ahora()))
        uow.ordenes.guardar(orden)
        uow.confirmar()


def orden(app, numero: str) -> OrdenDeServicio:
    return app.almacen.datos.ordenes[numero]


def leer_orden(app, numero: str) -> OrdenDeServicio:
    """U5: lee lo que quedó confirmado, sin importar si es memoria o base de datos."""
    with app.uow as uow:                    # sin confirmar(): solo lectura
        return uow.ordenes.obtener(NumeroOrden(numero))


def leer_cotizacion(app, id_cotizacion: str) -> Cotizacion:
    with app.uow as uow:
        return uow.cotizaciones.obtener(id_cotizacion)


def orden_en_diagnostico_sin_diagnostico(app, cliente: Cliente = CLIENTE_PARTICULAR) -> str:
    """U5: la orden ya tiene técnico asignado, pero todavía no hay diagnóstico."""
    with app.uow as uow:
        uow.clientes.agregar(cliente)
        numero = uow.ordenes.siguiente_numero()
        nueva = OrdenDeServicio(numero, cliente.id, cliente.es_de_flotilla, Placas(PLACAS),
                                "Ruido al frenar", app.reloj.ahora())
        nueva.asignar_tecnico_para_diagnostico("Técnico Juan", app.reloj.ahora())
        uow.ordenes.agregar(nueva)
        uow.confirmar()
    return str(numero)


__all__ = ["Dinero"]
