"""Entidades internas del Aggregate Orden de Servicio."""
from __future__ import annotations

from datetime import datetime

from autofix.dominio.compartido.errores import TransicionDeEstadoNoPermitida
from autofix.dominio.compartido.valores import Dinero
from autofix.dominio.ordenes.estados import EstadoSolicitud, EstadoTrabajo


class Trabajo:
    """Servicio de mano de obra autorizado (o no) que se asigna a un técnico (Glosario: Trabajo)."""

    def __init__(self, id_trabajo: int, descripcion: str, importe: Dinero, estado: EstadoTrabajo) -> None:
        self.id = id_trabajo
        self.descripcion = descripcion
        self.importe = importe
        self.estado = estado
        self.tecnico: str | None = None

    @property
    def esta_autorizado(self) -> bool:
        return self.estado is not EstadoTrabajo.NO_AUTORIZADO

    def iniciar(self) -> None:
        self._cambiar(EstadoTrabajo.PENDIENTE, EstadoTrabajo.EN_PROGRESO)

    def completar(self) -> None:
        self._cambiar(EstadoTrabajo.EN_PROGRESO, EstadoTrabajo.COMPLETADO)

    def _cambiar(self, desde: EstadoTrabajo, hacia: EstadoTrabajo) -> None:
        if self.estado is not desde:
            raise TransicionDeEstadoNoPermitida(
                f"El trabajo «{self.descripcion}» está en «{self.estado.value}» y no puede pasar a «{hacia.value}»."
            )
        self.estado = hacia


class SolicitudDeCompra:
    """Petición de una refacción no disponible para un trabajo autorizado (US-010)."""

    def __init__(self, id_solicitud: int, id_trabajo: int, refaccion: str, cantidad: int,
                 fecha: datetime) -> None:
        self.id = id_solicitud
        self.id_trabajo = id_trabajo
        self.refaccion = refaccion
        self.cantidad = cantidad
        self.fecha_solicitud = fecha
        self.estado = EstadoSolicitud.SOLICITADA
        self.fecha_llegada: datetime | None = None

    @property
    def esta_pendiente(self) -> bool:
        return self.estado is EstadoSolicitud.SOLICITADA

    def marcar_disponible(self, fecha: datetime) -> None:
        if not self.esta_pendiente:
            raise TransicionDeEstadoNoPermitida("La refacción ya estaba registrada como disponible.")
        self.estado = EstadoSolicitud.DISPONIBLE
        self.fecha_llegada = fecha
