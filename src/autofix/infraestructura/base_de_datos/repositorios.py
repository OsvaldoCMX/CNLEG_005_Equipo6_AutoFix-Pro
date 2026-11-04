"""Repositories con SQLAlchemy: implementan las mismas interfaces del dominio que la versión en memoria.

Contrato común (principio L): obtener() de algo inexistente responde con el error del
negocio (OrdenNoEncontrada, CotizacionNoEncontrada, ClienteNoEncontrado), nunca con None.
Los cambios se escriben en la sesión al confirmar la Unidad de Trabajo.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

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
from autofix.infraestructura.base_de_datos import mapeo
from autofix.infraestructura.base_de_datos.tablas import (
    ClienteFila,
    CotizacionFila,
    OrdenFila,
    SecuenciaFila,
)


def siguiente_valor(sesion: Session, nombre: str) -> int:
    fila = sesion.get(SecuenciaFila, nombre)
    if fila is None:
        fila = SecuenciaFila(nombre=nombre, ultimo_valor=0)
        sesion.add(fila)
    fila.ultimo_valor += 1
    sesion.flush()
    return fila.ultimo_valor


class RepositorioDeOrdenesSqlAlchemy(RepositorioDeOrdenes):
    def __init__(self, sesion: Session, vistos: list) -> None:
        self._sesion, self._vistos = sesion, vistos
        self._cargadas: dict[str, OrdenDeServicio] = {}
        self._nuevas: set[str] = set()

    def obtener(self, numero: NumeroOrden) -> OrdenDeServicio:
        clave = str(numero)
        if clave not in self._cargadas:
            fila = self._sesion.get(OrdenFila, clave)
            if fila is None:
                raise OrdenNoEncontrada(f"No existe la orden de servicio {numero}.")
            self._recordar(mapeo.leer_orden(fila))
        return self._cargadas[clave]

    def agregar(self, orden: OrdenDeServicio) -> None:
        clave = str(orden.numero)
        if clave in self._cargadas or self._sesion.get(OrdenFila, clave) is not None:
            raise ValorInvalido(f"La orden {orden.numero} ya existe.")
        self._nuevas.add(clave)
        self._recordar(orden)

    def guardar(self, orden: OrdenDeServicio) -> None:
        self._recordar(orden)

    def siguiente_numero(self) -> NumeroOrden:
        return NumeroOrden(f"OS-{siguiente_valor(self._sesion, 'ordenes'):04d}")

    def escribir_cambios(self) -> None:
        for clave, orden in self._cargadas.items():
            if clave in self._nuevas:
                fila = OrdenFila(numero=clave)
                self._sesion.add(fila)
            else:
                fila = self._sesion.get(OrdenFila, clave)
            mapeo.escribir_orden(orden, fila)

    def _recordar(self, orden: OrdenDeServicio) -> None:
        self._cargadas[str(orden.numero)] = orden
        self._vistos.append(orden)


class RepositorioDeCotizacionesSqlAlchemy(RepositorioDeCotizaciones):
    def __init__(self, sesion: Session, vistos: list) -> None:
        self._sesion, self._vistos = sesion, vistos
        self._cargadas: dict[str, Cotizacion] = {}

    def obtener(self, id_cotizacion: str) -> Cotizacion:
        if id_cotizacion not in self._cargadas:
            fila = self._sesion.get(CotizacionFila, id_cotizacion)
            if fila is None:
                raise CotizacionNoEncontrada(f"No existe la cotización {id_cotizacion}.")
            self._recordar(mapeo.leer_cotizacion(fila))
        return self._cargadas[id_cotizacion]

    def agregar(self, cotizacion: Cotizacion) -> None:
        self._recordar(cotizacion)

    def guardar(self, cotizacion: Cotizacion) -> None:
        self._recordar(cotizacion)

    def cotizaciones_de_la_orden(self, numero_orden: NumeroOrden) -> list[Cotizacion]:
        ids = self._sesion.scalars(select(CotizacionFila.id)
                                   .where(CotizacionFila.numero_orden == str(numero_orden))
                                   .order_by(CotizacionFila.version)).all()
        return [self.obtener(i) for i in ids]

    def siguiente_identidad(self) -> str:
        return f"COT-{siguiente_valor(self._sesion, 'cotizaciones'):04d}"

    def escribir_cambios(self) -> None:
        for id_cotizacion, cotizacion in self._cargadas.items():
            fila = self._sesion.get(CotizacionFila, id_cotizacion)
            if fila is None:
                fila = CotizacionFila(id=id_cotizacion)
                self._sesion.add(fila)
            mapeo.escribir_cotizacion(cotizacion, fila)

    def _recordar(self, cotizacion: Cotizacion) -> None:
        self._cargadas[cotizacion.id] = cotizacion
        self._vistos.append(cotizacion)


class RepositorioDeClientesSqlAlchemy(RepositorioDeClientes):
    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion
        self._pendientes: dict[str, Cliente] = {}

    def obtener(self, id_cliente: str) -> Cliente:
        if id_cliente in self._pendientes:
            return self._pendientes[id_cliente]
        fila = self._sesion.get(ClienteFila, id_cliente)
        if fila is None:
            raise ClienteNoEncontrado(f"No existe el cliente {id_cliente}.")
        return mapeo.leer_cliente(fila)

    def agregar(self, cliente: Cliente) -> None:
        # Igual que en memoria: registrar de nuevo al mismo cliente actualiza sus datos.
        self._pendientes[cliente.id] = cliente

    def escribir_cambios(self) -> None:
        for id_cliente, cliente in self._pendientes.items():
            fila = self._sesion.get(ClienteFila, id_cliente)
            if fila is None:
                fila = ClienteFila(id=id_cliente)
                self._sesion.add(fila)
            mapeo.escribir_cliente(cliente, fila)
