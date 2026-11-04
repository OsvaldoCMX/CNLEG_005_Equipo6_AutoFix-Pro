"""Almacenamiento en memoria (no hay base de datos en esta fase, ver ADR-004)."""
from __future__ import annotations

from dataclasses import dataclass, field

from autofix.dominio.clientes.cliente import Cliente
from autofix.dominio.cotizaciones.cotizacion import Cotizacion
from autofix.dominio.ordenes.orden_de_servicio import OrdenDeServicio


@dataclass
class DatosEnMemoria:
    ordenes: dict[str, OrdenDeServicio] = field(default_factory=dict)
    cotizaciones: dict[str, Cotizacion] = field(default_factory=dict)
    clientes: dict[str, Cliente] = field(default_factory=dict)
    contador_ordenes: int = 0
    contador_cotizaciones: int = 0


class AlmacenEnMemoria:
    """Hace el papel de la base de datos: solo contiene datos confirmados."""

    def __init__(self) -> None:
        self.datos = DatosEnMemoria()
