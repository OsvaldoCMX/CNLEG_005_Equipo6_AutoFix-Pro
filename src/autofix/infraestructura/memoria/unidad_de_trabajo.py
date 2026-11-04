"""Unit of Work en memoria.

Trabaja sobre una copia de los datos confirmados: confirmar() reemplaza los datos
del almacén con la copia y _deshacer() la descarta. Así, si una regla falla a la
mitad de la operación, ningún Aggregate queda modificado a medias.
"""
from __future__ import annotations

import copy

from autofix.aplicacion.unidad_de_trabajo import UnidadDeTrabajo
from autofix.dominio.compartido.eventos import EventoDeDominio
from autofix.infraestructura.memoria.almacen import AlmacenEnMemoria
from autofix.infraestructura.memoria.repositorios import (
    RepositorioDeClientesEnMemoria,
    RepositorioDeCotizacionesEnMemoria,
    RepositorioDeOrdenesEnMemoria,
)


class UnidadDeTrabajoEnMemoria(UnidadDeTrabajo):
    def __init__(self, almacen: AlmacenEnMemoria) -> None:
        self._almacen = almacen

    def _iniciar(self) -> None:
        self._copia = copy.deepcopy(self._almacen.datos)
        self._vistos: list = []
        self.ordenes = RepositorioDeOrdenesEnMemoria(self._copia, self._vistos)
        self.cotizaciones = RepositorioDeCotizacionesEnMemoria(self._copia, self._vistos)
        self.clientes = RepositorioDeClientesEnMemoria(self._copia)

    def _recolectar_eventos(self) -> list[EventoDeDominio]:
        eventos: list[EventoDeDominio] = []
        vistos_ids = set()
        for agregado in self._vistos:
            if id(agregado) not in vistos_ids:
                vistos_ids.add(id(agregado))
                eventos.extend(agregado.extraer_eventos())
        return sorted(eventos, key=lambda e: e.ocurrido_en)

    def _confirmar(self) -> None:
        self._almacen.datos = self._copia

    def _deshacer(self) -> None:
        self._copia = None
        self._vistos = []
