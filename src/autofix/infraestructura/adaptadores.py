"""Adaptadores de infraestructura: reloj, alertas internas y documentos.

Son implementaciones sencillas (boilerplate) de los puertos de la aplicación.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from autofix.aplicacion.puertos import GeneradorDeDocumentos, PublicadorDeEventos, Reloj
from autofix.dominio.compartido.eventos import EventoDeDominio
from autofix.dominio.cotizaciones import eventos as ev_cot
from autofix.dominio.cotizaciones.cotizacion import Cotizacion
from autofix.dominio.ordenes import eventos as ev_ord


class RelojDelSistema(Reloj):
    def ahora(self) -> datetime:
        return datetime.now()  # noqa: DTZ005 - hora local del taller, sin zona horaria


class RelojFijo(Reloj):
    """Para pruebas: el tiempo solo avanza cuando la prueba lo indica."""

    def __init__(self, inicio: datetime) -> None:
        self._actual = inicio

    def ahora(self) -> datetime:
        return self._actual

    def avanzar(self, **delta) -> None:
        self._actual += timedelta(**delta)


@dataclass(frozen=True)
class AlertaInterna:
    """Glosario: aviso en el panel de un usuario (no es correo ni SMS)."""

    destinatario: str
    mensaje: str


class PublicadorDeAlertasInternas(PublicadorDeEventos):
    """Convierte ciertos Domain Events en alertas para los paneles de los usuarios."""

    def __init__(self) -> None:
        self.publicados: list[EventoDeDominio] = []
        self.alertas: list[AlertaInterna] = []

    def publicar(self, eventos: list[EventoDeDominio]) -> None:
        for evento in eventos:
            self.publicados.append(evento)
            alerta = self._alerta_para(evento)
            if alerta:
                self.alertas.append(alerta)

    @staticmethod
    def _alerta_para(evento: EventoDeDominio) -> AlertaInterna | None:
        if isinstance(evento, ev_cot.AprobacionGerencialRequerida):
            return AlertaInterna("Gerente de Taller",
                                 f"Cotización {evento.id_cotizacion} de la orden {evento.numero_orden} "
                                 f"({evento.total}) requiere su aprobación.")
        if isinstance(evento, ev_cot.CotizacionAprobadaPorGerente):
            return AlertaInterna("Asesor de Servicio", f"La cotización {evento.id_cotizacion} fue aprobada; ya puede presentarla.")
        if isinstance(evento, ev_cot.CotizacionRechazadaPorGerente):
            return AlertaInterna("Asesor de Servicio",
                                 f"La cotización {evento.id_cotizacion} requiere ajuste: {evento.observaciones}")
        if isinstance(evento, ev_ord.SolicitudDeCompraCreada):
            return AlertaInterna("Personal de Compras",
                                 f"Nueva solicitud: {evento.cantidad} x {evento.refaccion} (orden {evento.numero_orden}).")
        return None


class GeneradorDeDocumentosSimulado(GeneradorDeDocumentos):
    """No genera un PDF real: devuelve la ruta donde quedaría. Se sustituye en la fase de implementación."""

    def generar_pdf_de_cotizacion(self, cotizacion: Cotizacion) -> str:
        return f"documentos/cotizaciones/{cotizacion.id}_{cotizacion.version}.pdf"
