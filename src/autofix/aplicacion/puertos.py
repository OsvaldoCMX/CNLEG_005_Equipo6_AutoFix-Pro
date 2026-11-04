"""Puertos (abstracciones) que la aplicación necesita del exterior.

Los servicios dependen de estas interfaces y no de detalles concretos (principio D).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from autofix.dominio.compartido.eventos import EventoDeDominio
from autofix.dominio.cotizaciones.cotizacion import Cotizacion


class Reloj(ABC):
    @abstractmethod
    def ahora(self) -> datetime: ...


class PublicadorDeEventos(ABC):
    """Entrega los Domain Events confirmados a quien los necesite (p. ej. alertas internas)."""

    @abstractmethod
    def publicar(self, eventos: list[EventoDeDominio]) -> None: ...


class GeneradorDeDocumentos(ABC):
    """CA-005: la cotización se entrega en PDF. Generar el archivo es un detalle de infraestructura."""

    @abstractmethod
    def generar_pdf_de_cotizacion(self, cotizacion: Cotizacion) -> str:
        """Devuelve la ruta o identificador del PDF generado."""
