"""CU-03 Registrar decisión del cliente (US-006, US-016; CA-010 a CA-012, CA-029).

Es la operación que modifica dos Aggregates (Cotización y Orden de Servicio).
La Unidad de Trabajo garantiza que ambos cambios se guarden juntos o ninguno (ADR-002).
"""
from __future__ import annotations

from autofix.aplicacion.comandos import RegistrarDecisionDelCliente
from autofix.aplicacion.puertos import PublicadorDeEventos, Reloj
from autofix.aplicacion.resultados import ResultadoDeDecision
from autofix.aplicacion.unidad_de_trabajo import UnidadDeTrabajo
from autofix.dominio.cotizaciones.valores import Autorizante, RolDeAutorizante
from autofix.dominio.servicios.verificador_de_autorizante import VerificadorDeAutorizante


class ServicioDeAutorizacion:
    def __init__(self, uow: UnidadDeTrabajo, verificador: VerificadorDeAutorizante, reloj: Reloj,
                 publicador: PublicadorDeEventos) -> None:
        self._uow = uow
        self._verificador = verificador
        self._reloj = reloj
        self._publicador = publicador

    def registrar_decision_del_cliente(self, comando: RegistrarDecisionDelCliente) -> ResultadoDeDecision:
        ahora = self._reloj.ahora()
        rol = (RolDeAutorizante.RESPONSABLE_DE_FLOTILLA if comando.es_responsable_de_flotilla
               else RolDeAutorizante.CLIENTE)
        autorizante = Autorizante(comando.nombre_autorizante, rol)
        with self._uow as uow:
            cotizacion = uow.cotizaciones.obtener(comando.id_cotizacion)
            orden = uow.ordenes.obtener(cotizacion.numero_orden)
            cliente = uow.clientes.obtener(orden.id_cliente)
            self._verificador.verificar(cliente, autorizante)
            decision = cotizacion.registrar_decision(set(comando.lineas_autorizadas), autorizante, ahora)
            orden.aplicar_decision(decision)
            uow.cotizaciones.guardar(cotizacion)
            uow.ordenes.guardar(orden)
            uow.confirmar()
        self._publicador.publicar(uow.eventos_confirmados())
        return ResultadoDeDecision(cotizacion.id, cotizacion.estado.value, orden.estado.value,
                                   len(decision.autorizados), len(decision.no_autorizados))
