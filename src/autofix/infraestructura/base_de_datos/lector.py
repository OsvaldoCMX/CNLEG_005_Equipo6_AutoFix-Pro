"""Lado de lectura (CQRS) con SQLAlchemy: consulta las tablas y arma vistas planas."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from autofix.aplicacion.consultas.consultas import (
    CotizacionPendienteVista,
    EstadoDeOrdenVista,
    LectorDeOrdenes,
    SolicitudPendienteVista,
)
from autofix.dominio.compartido.calendario import CalendarioHabil
from autofix.dominio.compartido.errores import ValorInvalido
from autofix.dominio.compartido.valores import NumeroOrden, Placas
from autofix.dominio.cotizaciones.valores import EstadoCotizacion
from autofix.dominio.ordenes.estados import EstadoSolicitud
from autofix.infraestructura.base_de_datos.mapeo import de_centavos
from autofix.infraestructura.base_de_datos.tablas import (
    CotizacionFila,
    OrdenFila,
    SolicitudDeCompraFila,
)


class LectorDeOrdenesSqlAlchemy(LectorDeOrdenes):
    def __init__(self, fabrica_de_sesiones: sessionmaker[Session], calendario: CalendarioHabil) -> None:
        self._fabrica = fabrica_de_sesiones
        self._calendario = calendario

    def estado_de_orden(self, numero_orden: str, placas: str) -> EstadoDeOrdenVista | None:
        try:
            numero, placas_vo = NumeroOrden(numero_orden), Placas(placas)
        except ValorInvalido:
            return None
        with self._fabrica() as sesion:
            fila = sesion.get(OrdenFila, str(numero))
            if fila is None or fila.placas != str(placas_vo):    # CA-038: no revela si existe
                return None
            return EstadoDeOrdenVista(fila.numero, fila.estado,
                                      fila.fecha_ingreso.isoformat(sep=" ", timespec="minutes"),
                                      fila.ultima_actualizacion.isoformat(sep=" ", timespec="minutes"))

    def solicitudes_pendientes(self, hoy) -> list[SolicitudPendienteVista]:
        consulta = (select(SolicitudDeCompraFila)
                    .where(SolicitudDeCompraFila.estado == EstadoSolicitud.SOLICITADA.value)
                    .order_by(SolicitudDeCompraFila.fecha_solicitud))
        with self._fabrica() as sesion:
            return [SolicitudPendienteVista(
                        s.numero_orden, s.refaccion, s.cantidad, s.fecha_solicitud.date().isoformat(),
                        self._calendario.dias_habiles_entre(s.fecha_solicitud.date(), hoy))
                    for s in sesion.scalars(consulta)]

    def cotizaciones_pendientes_de_aprobacion(self) -> list[CotizacionPendienteVista]:
        consulta = (select(CotizacionFila)
                    .where(CotizacionFila.estado == EstadoCotizacion.PENDIENTE_DE_APROBACION_GERENCIAL.value)
                    .order_by(CotizacionFila.id))
        with self._fabrica() as sesion:
            return [CotizacionPendienteVista(c.id, c.numero_orden, f"v.{c.version}",
                                             str(de_centavos(c.total_centavos)))
                    for c in sesion.scalars(consulta)]
