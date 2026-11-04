"""Aggregate Orden de Servicio (raíz: OrdenDeServicio).

Es el expediente del servicio (Glosario). Invariantes que protege:
- El estado solo cambia por transiciones válidas (tabla en estados.py).
- No se cotiza sin diagnóstico y el diagnóstico no cambia después de cotizar (CA-005, CA-033).
- Solo se piden refacciones para trabajos autorizados (CA-020).
- La orden queda «En Espera de Refacción» mientras exista una solicitud «Solicitada» (CA-019, CA-022).
- Pasa a «Lista para Entrega» cuando todos los trabajos autorizados están completados (CA-015).
- El pago debe cubrir el total autorizado y las flotillas no pagan de contado (CA-026, CA-039).
- El vehículo solo se entrega con pago o cargo a crédito, o tras un rechazo total (CA-041 a CA-043).
"""
from __future__ import annotations

from datetime import datetime

from autofix.dominio.compartido.errores import (
    DiagnosticoNoModificable,
    DiagnosticoRequerido,
    EntregaNoPermitida,
    PagoNoPermitido,
    SolicitudNoPermitida,
    TrabajoNoAutorizado,
    TrabajoNoEncontrado,
    TransicionDeEstadoNoPermitida,
    ValorInvalido,
)
from autofix.dominio.compartido.eventos import RaizDeAgregado
from autofix.dominio.compartido.valores import Dinero, NumeroOrden, Placas
from autofix.dominio.cotizaciones.valores import DecisionDelCliente, TipoCotizacion
from autofix.dominio.ordenes import eventos as ev
from autofix.dominio.ordenes.estados import EstadoOrden, EstadoTrabajo, validar_transicion
from autofix.dominio.ordenes.trabajo import SolicitudDeCompra, Trabajo
from autofix.dominio.ordenes.valores import CargoACredito, Pago

EO = EstadoOrden


class OrdenDeServicio(RaizDeAgregado):
    def __init__(self, numero: NumeroOrden, id_cliente: str, es_cliente_de_flotilla: bool,
                 placas: Placas, motivo_de_ingreso: str, fecha_ingreso: datetime) -> None:
        super().__init__()
        self.numero = numero
        self.id_cliente = id_cliente
        self.es_cliente_de_flotilla = es_cliente_de_flotilla
        self.placas = placas
        self.motivo_de_ingreso = motivo_de_ingreso
        self.fecha_ingreso = fecha_ingreso
        self.ultima_actualizacion = fecha_ingreso
        self.estado = EO.RECIBIDA
        self.tecnico_de_diagnostico: str | None = None
        self.diagnostico: str | None = None
        self.cotizada = False
        self.rechazo_total = False
        self.fecha_ingreso_a_fila: datetime | None = None
        self._trabajos: dict[int, Trabajo] = {}
        self._solicitudes: dict[int, SolicitudDeCompra] = {}
        self._estado_antes_de_espera: EstadoOrden | None = None
        self.pago: Pago | None = None
        self.cargo_a_credito: CargoACredito | None = None
        self.fecha_entrega: datetime | None = None

    # ------------------------------------------------------------------ consultas
    @property
    def trabajos(self) -> tuple[Trabajo, ...]:
        return tuple(self._trabajos[i] for i in sorted(self._trabajos))

    @property
    def solicitudes(self) -> tuple[SolicitudDeCompra, ...]:
        return tuple(self._solicitudes[i] for i in sorted(self._solicitudes))

    @property
    def total_autorizado(self) -> Dinero:
        total = Dinero.cero()
        for trabajo in self._trabajos.values():
            if trabajo.esta_autorizado:
                total = total + trabajo.importe
        return total

    # ------------------------------------------------------------------ diagnóstico (US-019, US-020)
    def asignar_tecnico_para_diagnostico(self, tecnico: str, fecha: datetime) -> None:
        self._cambiar_estado(EO.EN_DIAGNOSTICO, fecha)
        self.tecnico_de_diagnostico = tecnico

    def registrar_diagnostico(self, descripcion: str, fecha: datetime) -> None:
        if self.cotizada:
            raise DiagnosticoNoModificable(
                "La orden ya tiene una cotización; cualquier hallazgo nuevo se registra como falla adicional.")
        if self.estado is not EO.EN_DIAGNOSTICO:
            raise TransicionDeEstadoNoPermitida("Solo se registra el diagnóstico de una orden «En Diagnóstico».")
        if not descripcion or not descripcion.strip():      # U5 · TDD (CA-005)
            raise ValorInvalido("El diagnóstico debe describir la falla encontrada por el técnico.")
        self.diagnostico = descripcion.strip()
        self.ultima_actualizacion = fecha

    # ------------------------------------------------------------------ cotización (CU-01)
    def marcar_cotizada(self, fecha: datetime) -> None:
        if not self.diagnostico:
            raise DiagnosticoRequerido("No se puede cotizar una orden sin diagnóstico registrado por el técnico.")
        self._cambiar_estado(EO.COTIZADA, fecha)
        self.cotizada = True

    # ------------------------------------------------------------------ decisión del cliente (CU-03)
    def aplicar_decision(self, decision: DecisionDelCliente) -> None:
        """Convierte la decisión sobre la cotización en Trabajos de la orden."""
        es_adicional = decision.tipo_cotizacion is TipoCotizacion.ADICIONAL
        if decision.es_rechazo_total and not es_adicional:
            if self.estado is not EO.COTIZADA:
                raise TransicionDeEstadoNoPermitida("Solo se rechaza totalmente una orden «Cotizada».")
            self.rechazo_total = True          # habilita «Entregar sin reparación» (CA-012)
            self.ultima_actualizacion = decision.registrada_en
            return
        for trabajo in decision.autorizados:
            self._agregar_trabajo(trabajo.descripcion, trabajo.importe, EstadoTrabajo.PENDIENTE)
        for trabajo in decision.no_autorizados:
            self._agregar_trabajo(trabajo.descripcion, trabajo.importe, EstadoTrabajo.NO_AUTORIZADO)
        if es_adicional:                       # CA-017 / CA-018: la orden sigue su curso
            self.ultima_actualizacion = decision.registrada_en
            return
        self._cambiar_estado(EO.AUTORIZADA, decision.registrada_en)
        self.fecha_ingreso_a_fila = decision.registrada_en
        self._registrar(ev.OrdenAutorizada(decision.registrada_en, str(self.numero)))

    # ------------------------------------------------------------------ refacciones (CU-04, US-011)
    def crear_solicitud_de_compra(self, id_trabajo: int, refaccion: str, cantidad: int,
                                  fecha: datetime) -> SolicitudDeCompra:
        trabajo = self._trabajo(id_trabajo)
        if not trabajo.esta_autorizado:
            raise TrabajoNoAutorizado(
                f"No se puede solicitar «{refaccion}»: el trabajo «{trabajo.descripcion}» no fue autorizado por el cliente.")
        if self.estado not in (EO.AUTORIZADA, EO.EN_REPARACION, EO.EN_ESPERA_DE_REFACCION):
            raise SolicitudNoPermitida(
                f"No se pueden solicitar refacciones con la orden en «{self.estado.value}».")
        if cantidad <= 0 or not refaccion.strip():
            raise SolicitudNoPermitida("La solicitud necesita la descripción de la refacción y una cantidad mayor a cero.")
        solicitud = SolicitudDeCompra(len(self._solicitudes) + 1, id_trabajo, refaccion.strip(), cantidad, fecha)
        self._solicitudes[solicitud.id] = solicitud
        if self.estado is not EO.EN_ESPERA_DE_REFACCION:
            self._estado_antes_de_espera = self.estado
            self._cambiar_estado(EO.EN_ESPERA_DE_REFACCION, fecha)
        else:
            self.ultima_actualizacion = fecha
        self._registrar(ev.SolicitudDeCompraCreada(fecha, str(self.numero), solicitud.id,
                                                   solicitud.refaccion, cantidad))
        return solicitud

    def registrar_llegada_de_refaccion(self, id_solicitud: int, fecha: datetime) -> None:
        self._solicitudes[id_solicitud].marcar_disponible(fecha)
        self._registrar(ev.RefaccionDisponible(fecha, str(self.numero), id_solicitud))
        if not any(s.esta_pendiente for s in self._solicitudes.values()) \
                and self.estado is EO.EN_ESPERA_DE_REFACCION:
            self._cambiar_estado(self._estado_antes_de_espera, fecha)

    # ------------------------------------------------------------------ reparación (US-008)
    def iniciar_trabajo(self, id_trabajo: int, fecha: datetime) -> None:
        self._trabajo(id_trabajo).iniciar()
        if self.estado is EO.AUTORIZADA:
            self._cambiar_estado(EO.EN_REPARACION, fecha)
        else:
            self.ultima_actualizacion = fecha

    def completar_trabajo(self, id_trabajo: int, fecha: datetime) -> None:
        self._trabajo(id_trabajo).completar()
        autorizados = [t for t in self._trabajos.values() if t.esta_autorizado]
        if all(t.estado is EstadoTrabajo.COMPLETADO for t in autorizados):
            self._cambiar_estado(EO.LISTA_PARA_ENTREGA, fecha)
            self._registrar(ev.OrdenListaParaEntrega(fecha, str(self.numero)))
        else:
            self.ultima_actualizacion = fecha

    # ------------------------------------------------------------------ caja (US-014, US-022)
    def registrar_pago(self, pago: Pago) -> None:
        if self.es_cliente_de_flotilla:
            raise PagoNoPermitido("Las órdenes de flotilla se registran como cargo a crédito, no como pago de contado.")
        if pago.monto != self.total_autorizado:
            raise PagoNoPermitido(f"El pago debe cubrir el total autorizado de {self.total_autorizado}.")
        self._cambiar_estado(EO.PAGADA, pago.registrado_en)
        self.pago = pago
        self._registrar(ev.PagoRegistrado(pago.registrado_en, str(self.numero), str(pago.monto)))

    def registrar_cargo_a_credito(self, fecha: datetime) -> None:
        if not self.es_cliente_de_flotilla:
            raise PagoNoPermitido("El cargo a crédito solo aplica a clientes de flotilla.")
        self._cambiar_estado(EO.POR_COBRAR_CREDITO, fecha)
        self.cargo_a_credito = CargoACredito(self.total_autorizado, fecha)
        self._registrar(ev.CargoACreditoRegistrado(fecha, str(self.numero), str(self.total_autorizado),
                                                   self.cargo_a_credito.fecha_vencimiento.isoformat()))

    # ------------------------------------------------------------------ entrega (CU-05)
    def registrar_entrega(self, fecha: datetime) -> None:
        if self.estado in (EO.PAGADA, EO.POR_COBRAR_CREDITO):
            self._cambiar_estado(EO.CERRADA, fecha)
            sin_reparacion = False
        elif self.rechazo_total and self.estado is EO.COTIZADA:
            self._cambiar_estado(EO.CERRADA_SIN_REPARACION, fecha)
            sin_reparacion = True
        else:
            raise EntregaNoPermitida(
                f"No se puede entregar el vehículo de la orden {self.numero} (estado «{self.estado.value}»): "
                "primero debe registrarse el pago o el cargo a crédito.")
        self.fecha_entrega = fecha
        self._registrar(ev.VehiculoEntregado(fecha, str(self.numero), sin_reparacion))

    # ------------------------------------------------------------------ apoyo
    def _agregar_trabajo(self, descripcion: str, importe: Dinero, estado: EstadoTrabajo) -> None:
        nuevo_id = len(self._trabajos) + 1
        self._trabajos[nuevo_id] = Trabajo(nuevo_id, descripcion, importe, estado)

    def _trabajo(self, id_trabajo: int) -> Trabajo:
        try:
            return self._trabajos[id_trabajo]
        except KeyError:
            raise TrabajoNoEncontrado(f"La orden {self.numero} no tiene el trabajo {id_trabajo}.") from None

    def _cambiar_estado(self, nuevo: EstadoOrden, fecha: datetime) -> None:
        validar_transicion(self.estado, nuevo)
        self.estado = nuevo
        self.ultima_actualizacion = fecha
