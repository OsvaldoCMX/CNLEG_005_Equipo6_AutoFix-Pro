"""CU-01 Generar cotización (US-004, US-005; CA-005, CA-007).

Coordina: obtener la orden, pedir al dominio que la marque como cotizada, crear la
Cotización con la política de aprobación, confirmar y publicar eventos.
No decide si se requiere al Gerente: eso lo resuelve la PoliticaDeAprobacionGerencial.
"""
from __future__ import annotations

from decimal import Decimal

from autofix.aplicacion.comandos import GenerarCotizacion, TrabajoPropuesto
from autofix.aplicacion.puertos import GeneradorDeDocumentos, PublicadorDeEventos, Reloj
from autofix.aplicacion.resultados import ResultadoDeCotizacion
from autofix.aplicacion.unidad_de_trabajo import UnidadDeTrabajo
from autofix.dominio.compartido.valores import Dinero, NumeroOrden
from autofix.dominio.cotizaciones.cotizacion import Cotizacion
from autofix.dominio.cotizaciones.linea_de_cotizacion import LineaDeCotizacion
from autofix.dominio.cotizaciones.politica_de_aprobacion import PoliticaDeAprobacionGerencial
from autofix.dominio.cotizaciones.valores import (
    RefaccionCotizada,
    TipoCotizacion,
    VersionCotizacion,
)


class ServicioDeCotizacion:
    def __init__(self, uow: UnidadDeTrabajo, politica: PoliticaDeAprobacionGerencial, reloj: Reloj,
                 publicador: PublicadorDeEventos, documentos: GeneradorDeDocumentos) -> None:
        self._uow = uow
        self._politica = politica
        self._reloj = reloj
        self._publicador = publicador
        self._documentos = documentos

    def generar_cotizacion(self, comando: GenerarCotizacion) -> ResultadoDeCotizacion:
        ahora = self._reloj.ahora()
        with self._uow as uow:
            orden = uow.ordenes.obtener(NumeroOrden(comando.numero_orden))
            orden.marcar_cotizada(ahora)
            cotizacion = Cotizacion.generar(
                uow.cotizaciones.siguiente_identidad(), orden.numero, TipoCotizacion.INICIAL,
                VersionCotizacion(1), _a_lineas(comando.trabajos), self._politica, ahora)
            uow.cotizaciones.agregar(cotizacion)
            uow.ordenes.guardar(orden)
            uow.confirmar()
        self._publicador.publicar(uow.eventos_confirmados())
        pdf = self._documentos.generar_pdf_de_cotizacion(cotizacion)
        return ResultadoDeCotizacion(cotizacion.id, str(cotizacion.version), cotizacion.estado.value,
                                     str(cotizacion.total), pdf)


def _a_lineas(trabajos: tuple[TrabajoPropuesto, ...]) -> list[LineaDeCotizacion]:
    """Traduce los datos de entrada a objetos del dominio (sin reglas de negocio)."""
    return [
        LineaDeCotizacion(
            numero, t.descripcion, Dinero(Decimal(t.mano_de_obra)),
            tuple(RefaccionCotizada(r.descripcion, r.cantidad, Dinero(Decimal(r.precio_unitario)))
                  for r in t.refacciones))
        for numero, t in enumerate(trabajos, start=1)
    ]
