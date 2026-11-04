"""Estados de la Orden de Servicio, del Trabajo y de la Solicitud de Compra.

Los nombres son exactamente los del Glosario (sección «Estados del sistema»).
Las transiciones viven en una tabla separada para que OrdenDeServicio no crezca
con condicionales por cada estado (hallazgo SOLID H6).
"""
from __future__ import annotations

from enum import Enum

from autofix.dominio.compartido.errores import TransicionDeEstadoNoPermitida


class EstadoOrden(Enum):
    RECIBIDA = "Recibida"
    EN_DIAGNOSTICO = "En Diagnóstico"
    COTIZADA = "Cotizada"
    AUTORIZADA = "Autorizada"
    EN_REPARACION = "En Reparación"
    EN_ESPERA_DE_REFACCION = "En Espera de Refacción"
    PAUSADA_POR_RETIRO_DE_VEHICULO = "Pausada por Retiro de Vehículo"
    LISTA_PARA_ENTREGA = "Lista para Entrega"
    PAGADA = "Pagada"
    POR_COBRAR_CREDITO = "Por Cobrar (Crédito)"
    CERRADA = "Cerrada"
    CERRADA_SIN_REPARACION = "Cerrada sin Reparación"


class EstadoTrabajo(Enum):
    PENDIENTE = "Pendiente"
    EN_PROGRESO = "En Progreso"
    COMPLETADO = "Completado"
    NO_AUTORIZADO = "No Autorizado"


class EstadoSolicitud(Enum):
    SOLICITADA = "Solicitada"
    DISPONIBLE = "Disponible"


EO = EstadoOrden

TRANSICIONES_DE_ORDEN: dict[EstadoOrden, set[EstadoOrden]] = {
    EO.RECIBIDA: {EO.EN_DIAGNOSTICO},
    EO.EN_DIAGNOSTICO: {EO.COTIZADA},
    EO.COTIZADA: {EO.AUTORIZADA, EO.CERRADA_SIN_REPARACION},
    EO.AUTORIZADA: {EO.EN_REPARACION, EO.EN_ESPERA_DE_REFACCION},
    EO.EN_REPARACION: {EO.EN_ESPERA_DE_REFACCION, EO.LISTA_PARA_ENTREGA},
    EO.EN_ESPERA_DE_REFACCION: {EO.AUTORIZADA, EO.EN_REPARACION, EO.PAUSADA_POR_RETIRO_DE_VEHICULO},
    EO.PAUSADA_POR_RETIRO_DE_VEHICULO: {EO.EN_ESPERA_DE_REFACCION, EO.AUTORIZADA},
    EO.LISTA_PARA_ENTREGA: {EO.PAGADA, EO.POR_COBRAR_CREDITO},
    EO.PAGADA: {EO.CERRADA},
    EO.POR_COBRAR_CREDITO: {EO.CERRADA},
    EO.CERRADA: set(),
    EO.CERRADA_SIN_REPARACION: set(),
}


def validar_transicion(actual: EstadoOrden, nuevo: EstadoOrden) -> None:
    if nuevo not in TRANSICIONES_DE_ORDEN[actual]:
        raise TransicionDeEstadoNoPermitida(
            f"La orden no puede pasar de «{actual.value}» a «{nuevo.value}»."
        )
