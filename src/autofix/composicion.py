"""Raíz de composición: único lugar donde se eligen las implementaciones concretas.

Cambiar la memoria por la base de datos del Data Center solo modifica este archivo
y la carpeta infraestructura; dominio y aplicación no se tocan (principio D, ADR-004).

Unidad 5: además de la versión en memoria, construir_aplicacion_con_base_de_datos()
arma los mismos servicios sobre el adaptador SQLAlchemy (en pruebas, SQLite en memoria).
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine

from autofix.aplicacion.consultas.consultas import (
    LectorDeOrdenes,
    ManejadorConsultarEstadoDeOrden,
    ManejadorListarCotizacionesPendientesDeAprobacion,
    ManejadorListarSolicitudesPendientes,
)
from autofix.aplicacion.puertos import GeneradorDeDocumentos, PublicadorDeEventos, Reloj
from autofix.aplicacion.servicios.servicio_de_aprobacion_gerencial import (
    ServicioDeAprobacionGerencial,
)
from autofix.aplicacion.servicios.servicio_de_autorizacion import ServicioDeAutorizacion
from autofix.aplicacion.servicios.servicio_de_cotizacion import ServicioDeCotizacion
from autofix.aplicacion.servicios.servicio_de_entrega import ServicioDeEntrega
from autofix.aplicacion.servicios.servicio_de_refacciones import ServicioDeRefacciones
from autofix.aplicacion.unidad_de_trabajo import UnidadDeTrabajo
from autofix.dominio.compartido.calendario import CalendarioHabil
from autofix.dominio.cotizaciones.politica_de_aprobacion import PoliticaPorMontoDeCotizacionInicial
from autofix.dominio.servicios.verificador_de_autorizante import VerificadorDeAutorizante
from autofix.infraestructura.adaptadores import (
    GeneradorDeDocumentosSimulado,
    PublicadorDeAlertasInternas,
    RelojDelSistema,
)
from autofix.infraestructura.base_de_datos.lector import LectorDeOrdenesSqlAlchemy
from autofix.infraestructura.base_de_datos.motor import crear_fabrica_de_sesiones, crear_motor
from autofix.infraestructura.base_de_datos.unidad_de_trabajo import UnidadDeTrabajoSqlAlchemy
from autofix.infraestructura.memoria.almacen import AlmacenEnMemoria
from autofix.infraestructura.memoria.lector import LectorDeOrdenesEnMemoria
from autofix.infraestructura.memoria.unidad_de_trabajo import UnidadDeTrabajoEnMemoria


@dataclass
class Aplicacion:
    almacen: AlmacenEnMemoria | None
    reloj: Reloj
    publicador: PublicadorDeEventos
    uow: UnidadDeTrabajo
    cotizacion: ServicioDeCotizacion
    aprobacion_gerencial: ServicioDeAprobacionGerencial
    autorizacion: ServicioDeAutorizacion
    refacciones: ServicioDeRefacciones
    entrega: ServicioDeEntrega
    consultar_estado: ManejadorConsultarEstadoDeOrden
    solicitudes_pendientes: ManejadorListarSolicitudesPendientes
    cotizaciones_por_aprobar: ManejadorListarCotizacionesPendientesDeAprobacion
    motor: Engine | None = None


def construir_aplicacion(reloj: Reloj | None = None, publicador: PublicadorDeEventos | None = None,
                         documentos: GeneradorDeDocumentos | None = None) -> Aplicacion:
    """Versión en memoria (Unidad 3): sin base de datos."""
    almacen = AlmacenEnMemoria()
    return _armar(UnidadDeTrabajoEnMemoria(almacen), LectorDeOrdenesEnMemoria(almacen, CalendarioHabil()),
                  reloj, almacen=almacen, publicador=publicador, documentos=documentos)


def construir_aplicacion_con_base_de_datos(motor: Engine | None = None, reloj: Reloj | None = None,
                                           publicador: PublicadorDeEventos | None = None,
                                           documentos: GeneradorDeDocumentos | None = None) -> Aplicacion:
    """Mismos servicios, ahora sobre la base de datos (SQLite en memoria si no se indica otra)."""
    motor = motor or crear_motor()
    fabrica = crear_fabrica_de_sesiones(motor)
    return _armar(UnidadDeTrabajoSqlAlchemy(fabrica), LectorDeOrdenesSqlAlchemy(fabrica, CalendarioHabil()),
                  reloj, publicador=publicador, documentos=documentos, motor=motor)


def _armar(uow: UnidadDeTrabajo, lector: LectorDeOrdenes, reloj: Reloj | None, *,
           almacen: AlmacenEnMemoria | None = None, publicador: PublicadorDeEventos | None = None,
           documentos: GeneradorDeDocumentos | None = None, motor: Engine | None = None) -> Aplicacion:
    reloj = reloj or RelojDelSistema()
    publicador = publicador or PublicadorDeAlertasInternas()
    documentos = documentos or GeneradorDeDocumentosSimulado()
    return Aplicacion(
        almacen=almacen, reloj=reloj, publicador=publicador, uow=uow, motor=motor,
        cotizacion=ServicioDeCotizacion(uow, PoliticaPorMontoDeCotizacionInicial(), reloj, publicador,
                                        documentos),
        aprobacion_gerencial=ServicioDeAprobacionGerencial(uow, reloj, publicador),
        autorizacion=ServicioDeAutorizacion(uow, VerificadorDeAutorizante(), reloj, publicador),
        refacciones=ServicioDeRefacciones(uow, reloj, publicador),
        entrega=ServicioDeEntrega(uow, reloj, publicador),
        consultar_estado=ManejadorConsultarEstadoDeOrden(lector),
        solicitudes_pendientes=ManejadorListarSolicitudesPendientes(lector, reloj),
        cotizaciones_por_aprobar=ManejadorListarCotizacionesPendientesDeAprobacion(lector),
    )
