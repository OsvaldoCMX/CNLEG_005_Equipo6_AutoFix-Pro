"""Unit of Work: define qué cambios se confirman juntos.

Uso en cada Application Service:

    with self._uow as uow:          # inicia la transacción
        ...                         # obtiene Aggregates, invoca al dominio
        uow.confirmar()             # guarda todo junto
    # si ocurre un error antes de confirmar(), __exit__ deshace todos los cambios.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Self

from autofix.dominio.clientes.repositorio import RepositorioDeClientes
from autofix.dominio.compartido.eventos import EventoDeDominio
from autofix.dominio.cotizaciones.repositorio import RepositorioDeCotizaciones
from autofix.dominio.ordenes.repositorio import RepositorioDeOrdenes


class UnidadDeTrabajo(ABC):
    ordenes: RepositorioDeOrdenes
    cotizaciones: RepositorioDeCotizaciones
    clientes: RepositorioDeClientes

    def __enter__(self) -> Self:
        self._confirmada = False
        self._eventos: list[EventoDeDominio] = []
        self._iniciar()
        return self

    def __exit__(self, tipo_error, error, traza) -> None:
        if tipo_error is not None or not self._confirmada:
            self._deshacer()

    def confirmar(self) -> None:
        self._eventos = self._recolectar_eventos()
        self._confirmar()
        self._confirmada = True

    def eventos_confirmados(self) -> list[EventoDeDominio]:
        return list(self._eventos)

    @abstractmethod
    def _iniciar(self) -> None: ...

    @abstractmethod
    def _confirmar(self) -> None: ...

    @abstractmethod
    def _deshacer(self) -> None: ...

    @abstractmethod
    def _recolectar_eventos(self) -> list[EventoDeDominio]: ...
