"""Domain Events del Aggregate Cotización."""
from __future__ import annotations

from dataclasses import dataclass

from autofix.dominio.compartido.eventos import EventoDeDominio


@dataclass(frozen=True)
class CotizacionGenerada(EventoDeDominio):
    id_cotizacion: str
    numero_orden: str
    version: str
    total: str


@dataclass(frozen=True)
class AprobacionGerencialRequerida(EventoDeDominio):
    """CA-007: dispara la alerta interna en el panel del Gerente."""

    id_cotizacion: str
    numero_orden: str
    total: str


@dataclass(frozen=True)
class CotizacionAprobadaPorGerente(EventoDeDominio):
    id_cotizacion: str
    numero_orden: str


@dataclass(frozen=True)
class CotizacionRechazadaPorGerente(EventoDeDominio):
    id_cotizacion: str
    numero_orden: str
    observaciones: str


@dataclass(frozen=True)
class CotizacionPresentada(EventoDeDominio):
    id_cotizacion: str
    numero_orden: str


@dataclass(frozen=True)
class CotizacionAutorizada(EventoDeDominio):
    id_cotizacion: str
    numero_orden: str
    parcialmente: bool
    autorizante: str


@dataclass(frozen=True)
class CotizacionRechazadaPorCliente(EventoDeDominio):
    id_cotizacion: str
    numero_orden: str
    autorizante: str
