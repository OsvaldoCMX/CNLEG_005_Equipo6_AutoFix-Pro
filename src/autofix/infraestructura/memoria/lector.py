"""Lado de lectura (CQRS) en memoria: arma vistas planas a partir de los datos confirmados."""
from __future__ import annotations

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
from autofix.infraestructura.memoria.almacen import AlmacenEnMemoria


class LectorDeOrdenesEnMemoria(LectorDeOrdenes):
    def __init__(self, almacen: AlmacenEnMemoria, calendario: CalendarioHabil) -> None:
        self._almacen = almacen
        self._calendario = calendario

    def estado_de_orden(self, numero_orden: str, placas: str) -> EstadoDeOrdenVista | None:
        try:
            numero, placas_vo = NumeroOrden(numero_orden), Placas(placas)
        except ValorInvalido:
            return None
        orden = self._almacen.datos.ordenes.get(str(numero))
        if orden is None or orden.placas != placas_vo:      # CA-038: no revela si existe
            return None
        return EstadoDeOrdenVista(str(orden.numero), orden.estado.value,
                                  orden.fecha_ingreso.isoformat(sep=" ", timespec="minutes"),
                                  orden.ultima_actualizacion.isoformat(sep=" ", timespec="minutes"))

    def solicitudes_pendientes(self, hoy) -> list[SolicitudPendienteVista]:
        vistas = []
        for orden in self._almacen.datos.ordenes.values():
            for s in orden.solicitudes:
                if s.esta_pendiente:
                    vistas.append(SolicitudPendienteVista(
                        str(orden.numero), s.refaccion, s.cantidad, s.fecha_solicitud.date().isoformat(),
                        self._calendario.dias_habiles_entre(s.fecha_solicitud.date(), hoy)))
        return sorted(vistas, key=lambda v: v.fecha_solicitud)

    def cotizaciones_pendientes_de_aprobacion(self) -> list[CotizacionPendienteVista]:
        return [CotizacionPendienteVista(c.id, str(c.numero_orden), str(c.version), str(c.total))
                for c in self._almacen.datos.cotizaciones.values()
                if c.estado is EstadoCotizacion.PENDIENTE_DE_APROBACION_GERENCIAL]
