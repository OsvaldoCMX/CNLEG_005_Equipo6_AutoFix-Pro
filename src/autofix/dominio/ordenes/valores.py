"""Value Objects del Aggregate Orden de Servicio."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import Enum

from autofix.dominio.compartido.valores import Dinero


class FormaDePago(Enum):
    EFECTIVO = "Efectivo"
    TARJETA = "Tarjeta"
    TRANSFERENCIA = "Transferencia"


@dataclass(frozen=True)
class Pago:
    """CA-026: pago de contado de un cliente particular."""

    monto: Dinero
    forma: FormaDePago
    registrado_en: datetime


@dataclass(frozen=True)
class CargoACredito:
    """CA-039: crédito de flotilla a 15 días naturales."""

    DIAS_DE_CREDITO = 15

    monto: Dinero
    registrado_en: datetime

    @property
    def fecha_vencimiento(self) -> date:
        return (self.registrado_en + timedelta(days=self.DIAS_DE_CREDITO)).date()
