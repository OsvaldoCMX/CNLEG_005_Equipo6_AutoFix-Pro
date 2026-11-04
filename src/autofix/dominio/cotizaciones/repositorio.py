"""Repository del Aggregate Cotización (interfaz del dominio; la implementación vive en infraestructura)."""
from __future__ import annotations

from abc import ABC, abstractmethod

from autofix.dominio.compartido.valores import NumeroOrden
from autofix.dominio.cotizaciones.cotizacion import Cotizacion


class RepositorioDeCotizaciones(ABC):
    @abstractmethod
    def obtener(self, id_cotizacion: str) -> Cotizacion:
        """Devuelve la cotización o lanza CotizacionNoEncontrada."""

    @abstractmethod
    def agregar(self, cotizacion: Cotizacion) -> None: ...

    @abstractmethod
    def guardar(self, cotizacion: Cotizacion) -> None: ...

    @abstractmethod
    def cotizaciones_de_la_orden(self, numero_orden: NumeroOrden) -> list[Cotizacion]: ...

    @abstractmethod
    def siguiente_identidad(self) -> str: ...
