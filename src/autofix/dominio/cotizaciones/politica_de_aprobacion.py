"""Política de aprobación gerencial (BRD, Reglas de negocio implícitas; N-04; US-005).

Se modela como abstracción para poder agregar otra política sin editar la clase
Cotizacion (principio Open/Closed, hallazgo SOLID H2).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal

from autofix.dominio.compartido.valores import Dinero
from autofix.dominio.cotizaciones.valores import TipoCotizacion

UMBRAL_DE_APROBACION = Dinero(Decimal(15000))     # BRD: «mayor a $15,000 MXN»


class PoliticaDeAprobacionGerencial(ABC):
    @abstractmethod
    def requiere_aprobacion(self, tipo: TipoCotizacion, total: Dinero) -> bool:
        """Indica si la cotización debe pasar por el Gerente de Taller antes de presentarse."""


class PoliticaPorMontoDeCotizacionInicial(PoliticaDeAprobacionGerencial):
    """La cotización inicial mayor a $15,000 MXN requiere aprobación; las adicionales no."""

    def __init__(self, umbral: Dinero = UMBRAL_DE_APROBACION) -> None:
        self._umbral = umbral

    def requiere_aprobacion(self, tipo: TipoCotizacion, total: Dinero) -> bool:
        return tipo is TipoCotizacion.INICIAL and total > self._umbral
