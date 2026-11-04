"""Queries (CQRS), sus vistas de lectura (DTO) y sus manejadores.

Las vistas son modelos de lectura planos: no son los objetos del dominio ni se usan para escribir.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from autofix.aplicacion.puertos import Reloj


# ----------------------------------------------------------------------- Queries
@dataclass(frozen=True)
class ConsultarEstadoDeOrden:
    """US-021 (CA-037, CA-038): el cliente consulta con número de orden y placas."""

    numero_orden: str
    placas: str


@dataclass(frozen=True)
class ListarSolicitudesPendientes:
    """US-011 (CA-021): panel de Compras."""


@dataclass(frozen=True)
class ListarCotizacionesPendientesDeAprobacion:
    """US-005 (CA-007): panel del Gerente."""


# ----------------------------------------------------------------------- Vistas (DTO)
@dataclass(frozen=True)
class EstadoDeOrdenVista:
    numero_orden: str
    estado: str
    fecha_ingreso: str
    ultima_actualizacion: str


@dataclass(frozen=True)
class SolicitudPendienteVista:
    numero_orden: str
    refaccion: str
    cantidad: int
    fecha_solicitud: str
    dias_habiles_transcurridos: int


@dataclass(frozen=True)
class CotizacionPendienteVista:
    id_cotizacion: str
    numero_orden: str
    version: str
    total: str


# ----------------------------------------------------------------------- Puerto de lectura
class LectorDeOrdenes(ABC):
    """Interfaz solo de lectura, separada de los Repositories (principio I)."""

    @abstractmethod
    def estado_de_orden(self, numero_orden: str, placas: str) -> EstadoDeOrdenVista | None: ...

    @abstractmethod
    def solicitudes_pendientes(self, hoy) -> list[SolicitudPendienteVista]: ...

    @abstractmethod
    def cotizaciones_pendientes_de_aprobacion(self) -> list[CotizacionPendienteVista]: ...


# ----------------------------------------------------------------------- Manejadores
class ManejadorConsultarEstadoDeOrden:
    MENSAJE_NO_ENCONTRADA = "No se encontró una orden con esos datos"

    def __init__(self, lector: LectorDeOrdenes) -> None:
        self._lector = lector

    def ejecutar(self, consulta: ConsultarEstadoDeOrden) -> EstadoDeOrdenVista | str:
        vista = self._lector.estado_de_orden(consulta.numero_orden, consulta.placas)
        return vista if vista is not None else self.MENSAJE_NO_ENCONTRADA


class ManejadorListarSolicitudesPendientes:
    def __init__(self, lector: LectorDeOrdenes, reloj: Reloj) -> None:
        self._lector = lector
        self._reloj = reloj

    def ejecutar(self, consulta: ListarSolicitudesPendientes) -> list[SolicitudPendienteVista]:
        return self._lector.solicitudes_pendientes(self._reloj.ahora().date())


class ManejadorListarCotizacionesPendientesDeAprobacion:
    def __init__(self, lector: LectorDeOrdenes) -> None:
        self._lector = lector

    def ejecutar(self, consulta: ListarCotizacionesPendientesDeAprobacion) -> list[CotizacionPendienteVista]:
        return self._lector.cotizaciones_pendientes_de_aprobacion()
