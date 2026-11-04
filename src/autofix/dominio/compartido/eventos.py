"""Base para Domain Events y raíces de Aggregate."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class EventoDeDominio:
    """Hecho del negocio que ya ocurrió (se nombra en pasado)."""

    ocurrido_en: datetime


class RaizDeAgregado:
    """Acumula los eventos que produce el Aggregate hasta que la Unidad de Trabajo los extrae."""

    def __init__(self) -> None:
        self._eventos: list[EventoDeDominio] = []

    def _registrar(self, evento: EventoDeDominio) -> None:
        self._eventos.append(evento)

    def extraer_eventos(self) -> list[EventoDeDominio]:
        eventos, self._eventos = self._eventos, []
        return eventos
