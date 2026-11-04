"""Domain Events del Aggregate Orden de Servicio."""
from __future__ import annotations

from dataclasses import dataclass

from autofix.dominio.compartido.eventos import EventoDeDominio


@dataclass(frozen=True)
class OrdenAutorizada(EventoDeDominio):
    numero_orden: str


@dataclass(frozen=True)
class SolicitudDeCompraCreada(EventoDeDominio):
    """Hace aparecer la solicitud en el panel de Compras (CA-019)."""

    numero_orden: str
    id_solicitud: int
    refaccion: str
    cantidad: int


@dataclass(frozen=True)
class RefaccionDisponible(EventoDeDominio):
    numero_orden: str
    id_solicitud: int


@dataclass(frozen=True)
class OrdenListaParaEntrega(EventoDeDominio):
    numero_orden: str


@dataclass(frozen=True)
class PagoRegistrado(EventoDeDominio):
    numero_orden: str
    monto: str


@dataclass(frozen=True)
class CargoACreditoRegistrado(EventoDeDominio):
    numero_orden: str
    monto: str
    vence: str


@dataclass(frozen=True)
class VehiculoEntregado(EventoDeDominio):
    numero_orden: str
    sin_reparacion: bool
