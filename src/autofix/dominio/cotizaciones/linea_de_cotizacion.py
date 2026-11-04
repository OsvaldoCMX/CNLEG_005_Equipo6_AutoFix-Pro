"""Entidad interna del Aggregate Cotización."""
from __future__ import annotations

from enum import Enum

from autofix.dominio.compartido.errores import ValorInvalido
from autofix.dominio.compartido.valores import Dinero
from autofix.dominio.cotizaciones.valores import RefaccionCotizada


class DecisionDeLinea(Enum):
    AUTORIZADA = "Autorizada"
    NO_AUTORIZADA = "No Autorizado"


class LineaDeCotizacion:
    """Un Trabajo propuesto (mano de obra) con sus refacciones.

    Es entidad porque se identifica por su número dentro de la cotización y su
    decisión cambia (autorizada o no) sin que deje de ser la misma línea.
    """

    def __init__(self, numero: int, descripcion: str, mano_de_obra: Dinero,
                 refacciones: tuple[RefaccionCotizada, ...] = ()) -> None:
        if numero < 1:
            raise ValorInvalido("El número de línea empieza en 1.")
        if not descripcion.strip():
            raise ValorInvalido("Cada trabajo de la cotización debe tener descripción.")
        self.numero = numero
        self.descripcion = descripcion.strip()
        self.mano_de_obra = mano_de_obra
        self.refacciones = tuple(refacciones)
        self.decision: DecisionDeLinea | None = None

    @property
    def subtotal(self) -> Dinero:
        total = self.mano_de_obra
        for refaccion in self.refacciones:
            total = total + refaccion.importe
        return total
