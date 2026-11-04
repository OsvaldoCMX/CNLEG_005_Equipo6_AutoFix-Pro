"""Repository del Aggregate Cliente (interfaz del dominio)."""
from __future__ import annotations

from abc import ABC, abstractmethod

from autofix.dominio.clientes.cliente import Cliente


class RepositorioDeClientes(ABC):
    @abstractmethod
    def obtener(self, id_cliente: str) -> Cliente:
        """Devuelve el cliente o lanza ClienteNoEncontrado."""

    @abstractmethod
    def agregar(self, cliente: Cliente) -> None: ...
