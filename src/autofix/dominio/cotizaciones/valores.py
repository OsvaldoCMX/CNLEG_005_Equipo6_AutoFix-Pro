"""Value Objects y estados del Aggregate Cotización."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from autofix.dominio.compartido.errores import ValorInvalido
from autofix.dominio.compartido.valores import Dinero


class TipoCotizacion(Enum):
    INICIAL = "Inicial"
    ADICIONAL = "Adicional"


class EstadoCotizacion(Enum):
    """Glosario, sección «Estados del sistema» (Cotización)."""

    PENDIENTE_DE_APROBACION_GERENCIAL = "Pendiente de Aprobación Gerencial"
    REQUIERE_AJUSTE = "Requiere Ajuste"
    PENDIENTE_DE_AUTORIZACION_DEL_CLIENTE = "Pendiente de Autorización del Cliente"
    AUTORIZADA = "Autorizada"
    AUTORIZADA_PARCIALMENTE = "Autorizada Parcialmente"
    RECHAZADA = "Rechazada"


@dataclass(frozen=True)
class VersionCotizacion:
    """La cotización inicial es v.1; las adicionales son v.2, v.3… (Glosario)."""

    numero: int

    def __post_init__(self) -> None:
        if self.numero < 1:
            raise ValorInvalido("La versión de una cotización empieza en 1.")

    def __str__(self) -> str:
        return f"v.{self.numero}"


@dataclass(frozen=True)
class RefaccionCotizada:
    """Refacción incluida en una línea de cotización."""

    descripcion: str
    cantidad: int
    precio_unitario: Dinero

    def __post_init__(self) -> None:
        if not self.descripcion.strip():
            raise ValorInvalido("La refacción debe tener descripción.")
        if self.cantidad <= 0:
            raise ValorInvalido("La cantidad de una refacción debe ser mayor a cero.")

    @property
    def importe(self) -> Dinero:
        return self.precio_unitario.por(self.cantidad)


class RolDeAutorizante(Enum):
    CLIENTE = "Cliente"
    RESPONSABLE_DE_FLOTILLA = "Responsable de Flotilla"


@dataclass(frozen=True)
class Autorizante:
    """Persona a cuyo nombre se registra la decisión (CA-010, CA-029)."""

    nombre: str
    rol: RolDeAutorizante

    def __post_init__(self) -> None:
        if not self.nombre or not self.nombre.strip():
            raise ValorInvalido("Debe indicarse el nombre de quien autoriza.")
        object.__setattr__(self, "nombre", self.nombre.strip())


@dataclass(frozen=True)
class TrabajoDecidido:
    """Resultado de la decisión sobre una línea: lo que la Orden necesita para crear su Trabajo."""

    numero_linea: int
    descripcion: str
    importe: Dinero


@dataclass(frozen=True)
class DecisionDelCliente:
    """Decisión registrada sobre una cotización (US-006)."""

    autorizados: tuple[TrabajoDecidido, ...]
    no_autorizados: tuple[TrabajoDecidido, ...]
    autorizante: Autorizante
    registrada_en: datetime
    tipo_cotizacion: TipoCotizacion = field(default=TipoCotizacion.INICIAL)

    @property
    def es_rechazo_total(self) -> bool:
        return not self.autorizados
