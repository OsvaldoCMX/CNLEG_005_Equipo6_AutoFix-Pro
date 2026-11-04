"""Escenarios de los 5 casos de uso (flujos normales y de rechazo), redactados desde los criterios Gherkin."""
from __future__ import annotations

import unittest

from escenarios import (
    CLIENTE_FLOTILLA,
    TRABAJOS_COSTOSOS,
    TRABAJOS_NORMALES,
    completar_y_pagar,
    nueva_app,
    orden,
    orden_autorizada,
    orden_con_diagnostico,
    orden_cotizada,
)

from autofix.aplicacion.comandos import (
    CrearSolicitudDeCompra,
    GenerarCotizacion,
    RegistrarDecisionDelCliente,
    RegistrarEntrega,
    RevisarCotizacion,
)
from autofix.aplicacion.consultas.consultas import (
    ConsultarEstadoDeOrden,
    ListarCotizacionesPendientesDeAprobacion,
    ListarSolicitudesPendientes,
)
from autofix.dominio.compartido.errores import (
    AutorizanteNoValido,
    DiagnosticoRequerido,
    EntregaNoPermitida,
    OperacionDeCotizacionNoPermitida,
    TrabajoNoAutorizado,
    ValorInvalido,
)
from autofix.dominio.compartido.valores import NumeroOrden
from autofix.dominio.ordenes.orden_de_servicio import OrdenDeServicio


class CU01GenerarCotizacion(unittest.TestCase):
    def test_ca005_cotizacion_normal_queda_pendiente_de_autorizacion_del_cliente(self):
        app = nueva_app()
        numero = orden_con_diagnostico(app)
        r = app.cotizacion.generar_cotizacion(GenerarCotizacion(numero, TRABAJOS_NORMALES))
        self.assertEqual(r.version, "v.1")
        self.assertEqual(r.total, "$6,300.00 MXN")
        self.assertEqual(r.estado, "Pendiente de Autorización del Cliente")
        self.assertTrue(r.documento_pdf.endswith(".pdf"))
        self.assertEqual(orden(app, numero).estado.value, "Cotizada")

    def test_ca007_cotizacion_inicial_mayor_a_15000_requiere_gerente_y_alerta(self):
        app = nueva_app()
        numero = orden_con_diagnostico(app)
        r = app.cotizacion.generar_cotizacion(GenerarCotizacion(numero, TRABAJOS_COSTOSOS))
        self.assertEqual(r.estado, "Pendiente de Aprobación Gerencial")
        self.assertEqual(app.publicador.alertas[-1].destinatario, "Gerente de Taller")
        pendientes = app.cotizaciones_por_aprobar.ejecutar(ListarCotizacionesPendientesDeAprobacion())
        self.assertEqual([p.id_cotizacion for p in pendientes], [r.id_cotizacion])

    def test_ca007_no_se_puede_presentar_sin_aprobacion_gerencial(self):
        app = nueva_app()
        _, id_cot = orden_cotizada(app, trabajos=TRABAJOS_COSTOSOS)
        cotizacion = app.almacen.datos.cotizaciones[id_cot]
        with self.assertRaises(OperacionDeCotizacionNoPermitida):
            cotizacion.marcar_presentada(app.reloj.ahora())

    def test_rechazo_sin_diagnostico_no_se_cotiza_y_no_se_guarda_nada(self):
        app = nueva_app()
        with app.uow as uow:
            uow.clientes.agregar(CLIENTE_FLOTILLA)
            from autofix.dominio.compartido.valores import Placas
            nueva = OrdenDeServicio(NumeroOrden("OS-0099"), "CLI-002", True, Placas("XYZ1"), "Revisión",
                                    app.reloj.ahora())
            uow.ordenes.agregar(nueva)
            uow.confirmar()
        with self.assertRaises(DiagnosticoRequerido):
            app.cotizacion.generar_cotizacion(GenerarCotizacion("OS-0099", TRABAJOS_NORMALES))
        self.assertEqual(app.almacen.datos.cotizaciones, {})          # Unit of Work deshizo todo
        self.assertEqual(orden(app, "OS-0099").estado.value, "Recibida")


class CU02RevisarCotizacionPorGerente(unittest.TestCase):
    def test_ca008_gerente_aprueba(self):
        app = nueva_app()
        _, id_cot = orden_cotizada(app, trabajos=TRABAJOS_COSTOSOS)
        r = app.aprobacion_gerencial.revisar_cotizacion(RevisarCotizacion(id_cot, aprobada=True))
        self.assertEqual(r.estado, "Pendiente de Autorización del Cliente")
        self.assertEqual(app.publicador.alertas[-1].destinatario, "Asesor de Servicio")

    def test_ca009_gerente_rechaza_y_la_version_ajustada_no_regresa_a_revision(self):
        app = nueva_app()
        _, id_cot = orden_cotizada(app, trabajos=TRABAJOS_COSTOSOS)
        r = app.aprobacion_gerencial.revisar_cotizacion(
            RevisarCotizacion(id_cot, aprobada=False, observaciones="Usar kit de embrague alternativo"))
        self.assertEqual(r.estado, "Requiere Ajuste")
        cotizacion = app.almacen.datos.cotizaciones[id_cot]
        cotizacion.ajustar(list(cotizacion.lineas))
        self.assertEqual(cotizacion.estado.value, "Pendiente de Autorización del Cliente")

    def test_rechazo_sin_observaciones_no_se_permite(self):
        app = nueva_app()
        _, id_cot = orden_cotizada(app, trabajos=TRABAJOS_COSTOSOS)
        with self.assertRaises(ValorInvalido):
            app.aprobacion_gerencial.revisar_cotizacion(RevisarCotizacion(id_cot, aprobada=False))
        self.assertEqual(app.almacen.datos.cotizaciones[id_cot].estado.value,
                         "Pendiente de Aprobación Gerencial")


class CU03RegistrarDecisionDelCliente(unittest.TestCase):
    def test_ca010_autorizacion_parcial_crea_trabajos_y_autoriza_la_orden(self):
        app = nueva_app()
        numero, id_cot = orden_cotizada(app)
        r = app.autorizacion.registrar_decision_del_cliente(
            RegistrarDecisionDelCliente(id_cot, (1,), "María López"))
        self.assertEqual(r.estado_cotizacion, "Autorizada Parcialmente")
        self.assertEqual(r.estado_orden, "Autorizada")
        estados = [t.estado.value for t in orden(app, numero).trabajos]
        self.assertEqual(estados, ["Pendiente", "No Autorizado"])
        self.assertEqual(str(orden(app, numero).total_autorizado), "$2,400.00 MXN")

    def test_ca012_rechazo_total_no_crea_trabajos_y_habilita_entrega_sin_reparacion(self):
        app = nueva_app()
        numero, id_cot = orden_cotizada(app)
        r = app.autorizacion.registrar_decision_del_cliente(
            RegistrarDecisionDelCliente(id_cot, (), "María López"))
        self.assertEqual(r.estado_cotizacion, "Rechazada")
        self.assertEqual(r.estado_orden, "Cotizada")
        self.assertTrue(orden(app, numero).rechazo_total)

    def test_ca029_en_flotilla_el_conductor_no_puede_autorizar(self):
        app = nueva_app()
        numero, id_cot = orden_cotizada(app, cliente=CLIENTE_FLOTILLA)
        with self.assertRaises(AutorizanteNoValido):
            app.autorizacion.registrar_decision_del_cliente(
                RegistrarDecisionDelCliente(id_cot, (1, 2), "Pedro, conductor"))
        # La Unit of Work deshizo los cambios en ambos Aggregates
        self.assertEqual(app.almacen.datos.cotizaciones[id_cot].estado.value,
                         "Pendiente de Autorización del Cliente")
        self.assertEqual(orden(app, numero).estado.value, "Cotizada")

    def test_ca029_el_responsable_de_flotilla_si_autoriza(self):
        app = nueva_app()
        _, id_cot = orden_cotizada(app, cliente=CLIENTE_FLOTILLA)
        r = app.autorizacion.registrar_decision_del_cliente(
            RegistrarDecisionDelCliente(id_cot, (1, 2), "Carlos Ruiz", es_responsable_de_flotilla=True))
        self.assertEqual(r.estado_cotizacion, "Autorizada")


class CU04CrearSolicitudDeCompra(unittest.TestCase):
    def test_ca019_solicitud_pone_la_orden_en_espera_y_aparece_en_compras(self):
        app = nueva_app()
        numero, _ = orden_autorizada(app)
        r = app.refacciones.crear_solicitud_de_compra(
            CrearSolicitudDeCompra(numero, id_trabajo=1, refaccion="Juego de balatas", cantidad=1))
        self.assertEqual((r.estado_solicitud, r.estado_orden), ("Solicitada", "En Espera de Refacción"))
        app.reloj.avanzar(days=4)                                # lunes -> viernes
        pendientes = app.solicitudes_pendientes.ejecutar(ListarSolicitudesPendientes())
        self.assertEqual(pendientes[0].dias_habiles_transcurridos, 4)
        self.assertEqual(app.publicador.alertas[-1].destinatario, "Personal de Compras")

    def test_ca020_rechazo_si_el_trabajo_no_fue_autorizado(self):
        app = nueva_app()
        numero, _ = orden_autorizada(app, lineas=(1,))           # trabajo 2 = No Autorizado
        with self.assertRaises(TrabajoNoAutorizado):
            app.refacciones.crear_solicitud_de_compra(
                CrearSolicitudDeCompra(numero, id_trabajo=2, refaccion="Bujía", cantidad=4))
        self.assertEqual(orden(app, numero).estado.value, "Autorizada")
        self.assertEqual(orden(app, numero).solicitudes, ())


class CU05RegistrarEntrega(unittest.TestCase):
    def test_ca041_entrega_con_pago_cierra_la_orden(self):
        app = nueva_app()
        numero, _ = orden_autorizada(app)
        completar_y_pagar(app, numero)
        r = app.entrega.registrar_entrega(RegistrarEntrega(numero))
        self.assertEqual(r.estado_orden, "Cerrada")

    def test_ca042_rechazo_entrega_sin_pago(self):
        app = nueva_app()
        numero, _ = orden_autorizada(app)
        with self.assertRaises(EntregaNoPermitida) as error:
            app.entrega.registrar_entrega(RegistrarEntrega(numero))
        self.assertIn("primero debe registrarse el pago", str(error.exception))
        self.assertEqual(orden(app, numero).estado.value, "Autorizada")

    def test_ca043_entrega_sin_reparacion_tras_rechazo_total(self):
        app = nueva_app()
        numero, id_cot = orden_cotizada(app)
        app.autorizacion.registrar_decision_del_cliente(RegistrarDecisionDelCliente(id_cot, (), "María López"))
        r = app.entrega.registrar_entrega(RegistrarEntrega(numero))
        self.assertEqual(r.estado_orden, "Cerrada sin Reparación")


class ConsultaDelCliente(unittest.TestCase):
    def test_ca037_y_ca038_consulta_por_folio_y_placas(self):
        app = nueva_app()
        numero, _ = orden_cotizada(app)
        vista = app.consultar_estado.ejecutar(ConsultarEstadoDeOrden(numero, "abc 123 d"))
        self.assertEqual(vista.estado, "Cotizada")
        respuesta = app.consultar_estado.ejecutar(ConsultarEstadoDeOrden(numero, "OTRA-PLACA"))
        self.assertEqual(respuesta, "No se encontró una orden con esos datos")


if __name__ == "__main__":
    unittest.main()
