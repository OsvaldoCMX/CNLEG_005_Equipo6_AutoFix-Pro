"""Value Objects compartidos por el dominio de AutoFix Pro.

Un Value Object se define por sus valores, no tiene identidad propia y es inmutable.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from autofix.dominio.compartido.errores import ValorInvalido


@dataclass(frozen=True, order=True)
class Dinero:
    """Importe en pesos mexicanos (MXN). Nunca es negativo."""

    monto: Decimal

    def __post_init__(self) -> None:
        monto = Decimal(str(self.monto)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if monto < 0:
            raise ValorInvalido("Un importe en MXN no puede ser negativo.")
        object.__setattr__(self, "monto", monto)

    @staticmethod
    def cero() -> Dinero:
        return Dinero(Decimal(0))

    def __add__(self, otro: Dinero) -> Dinero:
        return Dinero(self.monto + otro.monto)

    def por(self, cantidad: int) -> Dinero:
        return Dinero(self.monto * cantidad)

    def __str__(self) -> str:
        return f"${self.monto:,.2f} MXN"


@dataclass(frozen=True)
class NumeroOrden:
    """Folio único de la Orden de Servicio (Glosario: Orden de Servicio)."""

    valor: str

    def __post_init__(self) -> None:
        if not self.valor or not self.valor.strip():
            raise ValorInvalido("El número de orden no puede estar vacío.")
        object.__setattr__(self, "valor", self.valor.strip().upper())

    def __str__(self) -> str:
        return self.valor


@dataclass(frozen=True)
class Placas:
    """Placas del vehículo. Se comparan sin importar mayúsculas, espacios ni guiones."""

    valor: str

    def __post_init__(self) -> None:
        normalizado = "".join(self.valor.replace("-", " ").split()).upper() if self.valor else ""
        if not normalizado:
            raise ValorInvalido("Las placas no pueden estar vacías.")
        object.__setattr__(self, "valor", normalizado)

    def __str__(self) -> str:
        return self.valor
