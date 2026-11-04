"""Aggregate Cliente (raíz: Cliente)."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from autofix.dominio.compartido.errores import ValorInvalido


class TipoCliente(Enum):
    PARTICULAR = "Particular"
    FLOTILLA = "Flotilla"


@dataclass(frozen=True)
class ResponsableDeFlotilla:
    """Contacto de la empresa que autoriza; no usa el sistema (Glosario)."""

    nombre: str
    telefono: str
    correo: str


class Cliente:
    """Invariante: un cliente de flotilla siempre tiene empresa y Responsable de Flotilla (CA-028)."""

    def __init__(self, id_cliente: str, nombre: str, tipo: TipoCliente, empresa: str | None = None,
                 responsable: ResponsableDeFlotilla | None = None) -> None:
        if tipo is TipoCliente.FLOTILLA and (not empresa or responsable is None):
            raise ValorInvalido("Un cliente de flotilla requiere su empresa y su Responsable de Flotilla.")
        self.id = id_cliente
        self.nombre = nombre
        self.tipo = tipo
        self.empresa = empresa
        self.responsable = responsable

    @property
    def es_de_flotilla(self) -> bool:
        return self.tipo is TipoCliente.FLOTILLA
