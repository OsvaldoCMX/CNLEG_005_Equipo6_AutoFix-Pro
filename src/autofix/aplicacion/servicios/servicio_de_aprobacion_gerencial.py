"""CU-02 Revisar cotización por el Gerente (US-005; CA-008, CA-009)."""
from __future__ import annotations

from autofix.aplicacion.comandos import RevisarCotizacion
from autofix.aplicacion.puertos import PublicadorDeEventos, Reloj
from autofix.aplicacion.resultados import ResultadoDeCotizacion
from autofix.aplicacion.unidad_de_trabajo import UnidadDeTrabajo


class ServicioDeAprobacionGerencial:
    def __init__(self, uow: UnidadDeTrabajo, reloj: Reloj, publicador: PublicadorDeEventos) -> None:
        self._uow = uow
        self._reloj = reloj
        self._publicador = publicador

    def revisar_cotizacion(self, comando: RevisarCotizacion) -> ResultadoDeCotizacion:
        ahora = self._reloj.ahora()
        with self._uow as uow:
            cotizacion = uow.cotizaciones.obtener(comando.id_cotizacion)
            # Elegir aprobar o rechazar es la intención del Gerente, no una regla del negocio;
            # las condiciones (estado válido, observaciones obligatorias) las valida Cotizacion.
            if comando.aprobada:
                cotizacion.aprobar_por_gerente(ahora)
            else:
                cotizacion.rechazar_por_gerente(comando.observaciones or "", ahora)
            uow.cotizaciones.guardar(cotizacion)
            uow.confirmar()
        self._publicador.publicar(uow.eventos_confirmados())
        return ResultadoDeCotizacion(cotizacion.id, str(cotizacion.version), cotizacion.estado.value,
                                     str(cotizacion.total))
