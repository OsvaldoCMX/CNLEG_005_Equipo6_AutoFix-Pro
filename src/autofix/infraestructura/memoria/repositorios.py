"""Implementaciones en memoria de los Repositories del dominio.

En el proyecto final, los repositorios de la base de datos del Data Center
implementarán estas mismas interfaces sin que el dominio ni la aplicación
cambien (principios L y D).
"""
from __future__ import annotations

from autofix.dominio.clientes.cliente import Cliente
from autofix.dominio.clientes.repositorio import RepositorioDeClientes
from autofix.dominio.compartido.errores import (
    ClienteNoEncontrado,
    CotizacionNoEncontrada,
    OrdenNoEncontrada,
    ValorInvalido,
)
from autofix.dominio.compartido.valores import NumeroOrden
from autofix.dominio.cotizaciones.cotizacion import Cotizacion
from autofix.dominio.cotizaciones.repositorio import RepositorioDeCotizaciones
from autofix.dominio.ordenes.orden_de_servicio import OrdenDeServicio
from autofix.dominio.ordenes.repositorio import RepositorioDeOrdenes
from autofix.infraestructura.memoria.almacen import DatosEnMemoria


class RepositorioDeOrdenesEnMemoria(RepositorioDeOrdenes):
    def __init__(self, datos: DatosEnMemoria, vistos: list) -> None:
        self._datos, self._vistos = datos, vistos

    def obtener(self, numero: NumeroOrden) -> OrdenDeServicio:
        try:
            orden = self._datos.ordenes[str(numero)]
        except KeyError:
            raise OrdenNoEncontrada(f"No existe la orden de servicio {numero}.") from None
        self._vistos.append(orden)
        return orden

    def agregar(self, orden: OrdenDeServicio) -> None:
        if str(orden.numero) in self._datos.ordenes:
            raise ValorInvalido(f"La orden {orden.numero} ya existe.")
        self._datos.ordenes[str(orden.numero)] = orden
        self._vistos.append(orden)

    def guardar(self, orden: OrdenDeServicio) -> None:
        self._datos.ordenes[str(orden.numero)] = orden

    def siguiente_numero(self) -> NumeroOrden:
        self._datos.contador_ordenes += 1
        return NumeroOrden(f"OS-{self._datos.contador_ordenes:04d}")


class RepositorioDeCotizacionesEnMemoria(RepositorioDeCotizaciones):
    def __init__(self, datos: DatosEnMemoria, vistos: list) -> None:
        self._datos, self._vistos = datos, vistos

    def obtener(self, id_cotizacion: str) -> Cotizacion:
        try:
            cotizacion = self._datos.cotizaciones[id_cotizacion]
        except KeyError:
            raise CotizacionNoEncontrada(f"No existe la cotización {id_cotizacion}.") from None
        self._vistos.append(cotizacion)
        return cotizacion

    def agregar(self, cotizacion: Cotizacion) -> None:
        self._datos.cotizaciones[cotizacion.id] = cotizacion
        self._vistos.append(cotizacion)

    def guardar(self, cotizacion: Cotizacion) -> None:
        self._datos.cotizaciones[cotizacion.id] = cotizacion

    def cotizaciones_de_la_orden(self, numero_orden: NumeroOrden) -> list[Cotizacion]:
        return [c for c in self._datos.cotizaciones.values() if c.numero_orden == numero_orden]

    def siguiente_identidad(self) -> str:
        self._datos.contador_cotizaciones += 1
        return f"COT-{self._datos.contador_cotizaciones:04d}"


class RepositorioDeClientesEnMemoria(RepositorioDeClientes):
    def __init__(self, datos: DatosEnMemoria) -> None:
        self._datos = datos

    def obtener(self, id_cliente: str) -> Cliente:
        try:
            return self._datos.clientes[id_cliente]
        except KeyError:
            raise ClienteNoEncontrado(f"No existe el cliente {id_cliente}.") from None

    def agregar(self, cliente: Cliente) -> None:
        self._datos.clientes[cliente.id] = cliente
