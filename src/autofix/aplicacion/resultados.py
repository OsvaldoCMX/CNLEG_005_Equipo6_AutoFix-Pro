"""Resultados que devuelven los Application Services (no exponen objetos del dominio)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResultadoDeCotizacion:
    id_cotizacion: str
    version: str
    estado: str
    total: str
    documento_pdf: str | None = None


@dataclass(frozen=True)
class ResultadoDeDecision:
    id_cotizacion: str
    estado_cotizacion: str
    estado_orden: str
    trabajos_autorizados: int
    trabajos_no_autorizados: int


@dataclass(frozen=True)
class ResultadoDeSolicitud:
    numero_orden: str
    id_solicitud: int
    estado_solicitud: str
    estado_orden: str


@dataclass(frozen=True)
class ResultadoDeEntrega:
    numero_orden: str
    estado_orden: str
    fecha_entrega: str
