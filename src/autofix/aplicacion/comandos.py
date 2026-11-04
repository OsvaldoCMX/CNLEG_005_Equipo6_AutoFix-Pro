"""Commands (CQRS): intenciones que cambian el estado. Un Command por caso de uso."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True)
class RefaccionPropuesta:
    descripcion: str
    cantidad: int
    precio_unitario: Decimal


@dataclass(frozen=True)
class TrabajoPropuesto:
    descripcion: str
    mano_de_obra: Decimal
    refacciones: tuple[RefaccionPropuesta, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class GenerarCotizacion:
    """CU-01 (US-004, US-005)."""

    numero_orden: str
    trabajos: tuple[TrabajoPropuesto, ...]


@dataclass(frozen=True)
class RevisarCotizacion:
    """CU-02 (US-005): el Gerente aprueba o rechaza con observaciones."""

    id_cotizacion: str
    aprobada: bool
    observaciones: str | None = None


@dataclass(frozen=True)
class RegistrarDecisionDelCliente:
    """CU-03 (US-006, US-016). lineas_autorizadas vacío = rechazo total."""

    id_cotizacion: str
    lineas_autorizadas: tuple[int, ...]
    nombre_autorizante: str
    es_responsable_de_flotilla: bool = False


@dataclass(frozen=True)
class CrearSolicitudDeCompra:
    """CU-04 (US-010)."""

    numero_orden: str
    id_trabajo: int
    refaccion: str
    cantidad: int


@dataclass(frozen=True)
class RegistrarEntrega:
    """CU-05 (US-024)."""

    numero_orden: str
