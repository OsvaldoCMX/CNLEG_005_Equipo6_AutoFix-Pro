"""Paso 9 · Servicios externos simulados con Mock (sin generar PDF reales ni enviar alertas).

AutoFix Pro depende de dos servicios externos a través de puertos (ADR-003/ADR-004):
- GeneradorDeDocumentos: genera el PDF de la cotización (CA-005).
- PublicadorDeEventos: convierte los Domain Events en alertas internas (CA-007, CA-019).
Con Mock(spec=...) la prueba controla su respuesta y revisa cómo los llamó el servicio.
"""
from __future__ import annotations

from unittest.mock import Mock

import pytest
from escenarios import (
    IMPLEMENTACIONES,
    TRABAJOS_COSTOSOS,
    TRABAJOS_NORMALES,
    crear_app,
    leer_cotizacion,
    orden_autorizada,
    orden_con_diagnostico,
    orden_en_diagnostico_sin_diagnostico,
)

from autofix.aplicacion.comandos import CrearSolicitudDeCompra, GenerarCotizacion
from autofix.aplicacion.puertos import GeneradorDeDocumentos, PublicadorDeEventos
from autofix.dominio.compartido.errores import DiagnosticoRequerido, TrabajoNoAutorizado
from autofix.dominio.cotizaciones import eventos as ev_cot
from autofix.dominio.ordenes import eventos as ev_ord


def _mocks():
    documentos = Mock(spec=GeneradorDeDocumentos)
    documentos.generar_pdf_de_cotizacion.return_value = "pdf/COT-0001_v.1.pdf"
    publicador = Mock(spec=PublicadorDeEventos)
    return documentos, publicador


def _eventos_publicados(publicador) -> list:
    return [e for llamada in publicador.publicar.call_args_list for e in llamada.args[0]]


@pytest.mark.parametrize("implementacion", IMPLEMENTACIONES)
def test_pdf_se_genera_una_vez_y_se_devuelve_al_asesor(implementacion):
    documentos, publicador = _mocks()
    app = crear_app(implementacion, documentos=documentos, publicador=publicador)
    numero = orden_con_diagnostico(app)

    r = app.cotizacion.generar_cotizacion(GenerarCotizacion(numero, TRABAJOS_NORMALES))

    documentos.generar_pdf_de_cotizacion.assert_called_once()
    cotizacion_enviada = documentos.generar_pdf_de_cotizacion.call_args.args[0]
    assert (cotizacion_enviada.id, str(cotizacion_enviada.total)) == ("COT-0001", "$6,300.00 MXN")
    assert r.documento_pdf == "pdf/COT-0001_v.1.pdf"


@pytest.mark.parametrize("implementacion", IMPLEMENTACIONES)
def test_cotizacion_mayor_a_15000_publica_aviso_para_el_gerente(implementacion):
    documentos, publicador = _mocks()
    app = crear_app(implementacion, documentos=documentos, publicador=publicador)
    numero = orden_con_diagnostico(app)

    app.cotizacion.generar_cotizacion(GenerarCotizacion(numero, TRABAJOS_COSTOSOS))

    publicador.publicar.assert_called_once()
    tipos = [type(e) for e in _eventos_publicados(publicador)]
    assert tipos == [ev_cot.CotizacionGenerada, ev_cot.AprobacionGerencialRequerida]


@pytest.mark.parametrize("implementacion", IMPLEMENTACIONES)
def test_si_la_regla_falla_no_se_genera_pdf_ni_se_publica_nada(implementacion):
    documentos, publicador = _mocks()
    app = crear_app(implementacion, documentos=documentos, publicador=publicador)
    numero = orden_en_diagnostico_sin_diagnostico(app)

    with pytest.raises(DiagnosticoRequerido):
        app.cotizacion.generar_cotizacion(GenerarCotizacion(numero, TRABAJOS_NORMALES))

    documentos.generar_pdf_de_cotizacion.assert_not_called()
    publicador.publicar.assert_not_called()


@pytest.mark.parametrize("implementacion", IMPLEMENTACIONES)
def test_solicitud_de_compra_avisa_a_compras_y_la_rechazada_no(implementacion):
    documentos, publicador = _mocks()
    app = crear_app(implementacion, documentos=documentos, publicador=publicador)
    numero, _ = orden_autorizada(app, lineas=(1,))
    publicador.reset_mock()

    app.refacciones.crear_solicitud_de_compra(CrearSolicitudDeCompra(numero, 1, "Juego de balatas", 1))
    with pytest.raises(TrabajoNoAutorizado):
        app.refacciones.crear_solicitud_de_compra(CrearSolicitudDeCompra(numero, 2, "Bujía", 4))

    publicador.publicar.assert_called_once()          # solo la solicitud válida generó aviso
    (evento,) = _eventos_publicados(publicador)
    assert isinstance(evento, ev_ord.SolicitudDeCompraCreada)
    assert (evento.refaccion, evento.cantidad) == ("Juego de balatas", 1)


# ------------------------------------------------------------------ fallas del servicio externo
@pytest.mark.parametrize("implementacion", IMPLEMENTACIONES)
def test_si_falla_el_pdf_la_cotizacion_ya_quedo_guardada(implementacion):
    """El PDF se genera DESPUÉS del commit: si el generador falla, la cotización no se pierde
    y el Asesor puede volver a pedir el PDF. (Ver propuesta de mejora en el README.)"""
    documentos, publicador = _mocks()
    documentos.generar_pdf_de_cotizacion.side_effect = OSError("servicio de PDF no disponible")
    app = crear_app(implementacion, documentos=documentos, publicador=publicador)
    numero = orden_con_diagnostico(app)

    with pytest.raises(OSError, match="no disponible"):
        app.cotizacion.generar_cotizacion(GenerarCotizacion(numero, TRABAJOS_NORMALES))

    assert leer_cotizacion(app, "COT-0001").estado.value == "Pendiente de Autorización del Cliente"


@pytest.mark.parametrize("implementacion", IMPLEMENTACIONES)
def test_timeout_del_publicador_no_revierte_la_cotizacion(implementacion):
    """Los eventos se publican DESPUÉS del commit (sin outbox): si el aviso falla por timeout,
    los datos quedan bien guardados, pero el aviso al Gerente se pierde. Riesgo documentado."""
    documentos, publicador = _mocks()
    publicador.publicar.side_effect = TimeoutError("el panel de alertas no respondió")
    app = crear_app(implementacion, documentos=documentos, publicador=publicador)
    numero = orden_con_diagnostico(app)

    with pytest.raises(TimeoutError):
        app.cotizacion.generar_cotizacion(GenerarCotizacion(numero, TRABAJOS_COSTOSOS))

    assert leer_cotizacion(app, "COT-0001").estado.value == "Pendiente de Aprobación Gerencial"
    documentos.generar_pdf_de_cotizacion.assert_not_called()
