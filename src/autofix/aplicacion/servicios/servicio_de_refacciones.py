"""CU-04 Crear solicitud de compra (US-010; CA-019, CA-020)."""
from __future__ import annotations

from autofix.aplicacion.comandos import CrearSolicitudDeCompra
from autofix.aplicacion.puertos import PublicadorDeEventos, Reloj
from autofix.aplicacion.resultados import ResultadoDeSolicitud
from autofix.aplicacion.unidad_de_trabajo import UnidadDeTrabajo
from autofix.dominio.compartido.valores import NumeroOrden


class ServicioDeRefacciones:
    def __init__(self, uow: UnidadDeTrabajo, reloj: Reloj, publicador: PublicadorDeEventos) -> None:
        self._uow = uow
        self._reloj = reloj
        self._publicador = publicador

    def crear_solicitud_de_compra(self, comando: CrearSolicitudDeCompra) -> ResultadoDeSolicitud:
        ahora = self._reloj.ahora()
        with self._uow as uow:
            orden = uow.ordenes.obtener(NumeroOrden(comando.numero_orden))
            solicitud = orden.crear_solicitud_de_compra(comando.id_trabajo, comando.refaccion,
                                                        comando.cantidad, ahora)
            uow.ordenes.guardar(orden)
            uow.confirmar()
        self._publicador.publicar(uow.eventos_confirmados())
        return ResultadoDeSolicitud(str(orden.numero), solicitud.id, solicitud.estado.value, orden.estado.value)
