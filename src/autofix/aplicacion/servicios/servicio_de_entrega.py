"""CU-05 Registrar entrega del vehículo (US-024; CA-041 a CA-043)."""
from __future__ import annotations

from autofix.aplicacion.comandos import RegistrarEntrega
from autofix.aplicacion.puertos import PublicadorDeEventos, Reloj
from autofix.aplicacion.resultados import ResultadoDeEntrega
from autofix.aplicacion.unidad_de_trabajo import UnidadDeTrabajo
from autofix.dominio.compartido.valores import NumeroOrden


class ServicioDeEntrega:
    def __init__(self, uow: UnidadDeTrabajo, reloj: Reloj, publicador: PublicadorDeEventos) -> None:
        self._uow = uow
        self._reloj = reloj
        self._publicador = publicador

    def registrar_entrega(self, comando: RegistrarEntrega) -> ResultadoDeEntrega:
        ahora = self._reloj.ahora()
        with self._uow as uow:
            orden = uow.ordenes.obtener(NumeroOrden(comando.numero_orden))
            orden.registrar_entrega(ahora)
            uow.ordenes.guardar(orden)
            uow.confirmar()
        self._publicador.publicar(uow.eventos_confirmados())
        return ResultadoDeEntrega(str(orden.numero), orden.estado.value, orden.fecha_entrega.isoformat())
