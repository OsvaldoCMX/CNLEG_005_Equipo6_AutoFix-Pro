"""Aggregate Cotización (raíz: Cotizacion).

Invariantes que protege:
- Una cotización tiene al menos un trabajo y su total es la suma de sus líneas.
- La inicial es v.1; las adicionales son v.2 en adelante y no modifican la original.
- No se presenta al cliente mientras espera aprobación del Gerente (CA-007).
- El rechazo del Gerente exige observaciones y la versión ajustada no regresa a revisión (CA-009).
- La decisión del cliente solo se registra una vez y solo sobre líneas existentes (CA-010).
"""
from __future__ import annotations

from datetime import datetime

from autofix.dominio.compartido.errores import (
    CotizacionSinTrabajos,
    OperacionDeCotizacionNoPermitida,
    ValorInvalido,
)
from autofix.dominio.compartido.eventos import RaizDeAgregado
from autofix.dominio.compartido.valores import Dinero, NumeroOrden
from autofix.dominio.cotizaciones import eventos as ev
from autofix.dominio.cotizaciones.linea_de_cotizacion import DecisionDeLinea, LineaDeCotizacion
from autofix.dominio.cotizaciones.politica_de_aprobacion import PoliticaDeAprobacionGerencial
from autofix.dominio.cotizaciones.valores import (
    Autorizante,
    DecisionDelCliente,
    EstadoCotizacion,
    TipoCotizacion,
    TrabajoDecidido,
    VersionCotizacion,
)

E = EstadoCotizacion


class Cotizacion(RaizDeAgregado):
    def __init__(self, id_cotizacion: str, numero_orden: NumeroOrden, tipo: TipoCotizacion,
                 version: VersionCotizacion, lineas: list[LineaDeCotizacion], fecha: datetime) -> None:
        super().__init__()
        self.id = id_cotizacion
        self.numero_orden = numero_orden
        self.tipo = tipo
        self.version = version
        self._lineas: dict[int, LineaDeCotizacion] = {}
        self._asignar_lineas(lineas)
        self.estado: EstadoCotizacion | None = None
        self.generada_en = fecha
        self.fecha_presentacion: datetime | None = None
        self.observaciones_del_gerente: str | None = None
        self.decision: DecisionDelCliente | None = None

    # ------------------------------------------------------------------ creación
    @classmethod
    def generar(cls, id_cotizacion: str, numero_orden: NumeroOrden, tipo: TipoCotizacion,
                version: VersionCotizacion, lineas: list[LineaDeCotizacion],
                politica: PoliticaDeAprobacionGerencial, fecha: datetime) -> Cotizacion:
        if tipo is TipoCotizacion.INICIAL and version.numero != 1:
            raise ValorInvalido("La cotización inicial siempre es la versión 1.")
        if tipo is TipoCotizacion.ADICIONAL and version.numero < 2:
            raise ValorInvalido("Una cotización adicional es la versión 2 o posterior.")
        cotizacion = cls(id_cotizacion, numero_orden, tipo, version, lineas, fecha)
        cotizacion._registrar(ev.CotizacionGenerada(fecha, id_cotizacion, str(numero_orden),
                                                    str(version), str(cotizacion.total)))
        if politica.requiere_aprobacion(tipo, cotizacion.total):
            cotizacion.estado = E.PENDIENTE_DE_APROBACION_GERENCIAL
            cotizacion._registrar(ev.AprobacionGerencialRequerida(
                fecha, id_cotizacion, str(numero_orden), str(cotizacion.total)))
        else:
            cotizacion.estado = E.PENDIENTE_DE_AUTORIZACION_DEL_CLIENTE
        return cotizacion

    # ------------------------------------------------------------------ consultas
    @property
    def lineas(self) -> tuple[LineaDeCotizacion, ...]:
        return tuple(self._lineas[n] for n in sorted(self._lineas))

    @property
    def total(self) -> Dinero:
        total = Dinero.cero()
        for linea in self._lineas.values():
            total = total + linea.subtotal
        return total

    # ------------------------------------------------------------------ Gerente (US-005)
    def aprobar_por_gerente(self, fecha: datetime) -> None:
        self._exigir_estado(E.PENDIENTE_DE_APROBACION_GERENCIAL, "aprobar")
        self.estado = E.PENDIENTE_DE_AUTORIZACION_DEL_CLIENTE
        self._registrar(ev.CotizacionAprobadaPorGerente(fecha, self.id, str(self.numero_orden)))

    def rechazar_por_gerente(self, observaciones: str, fecha: datetime) -> None:
        self._exigir_estado(E.PENDIENTE_DE_APROBACION_GERENCIAL, "rechazar")
        if not observaciones or not observaciones.strip():
            raise ValorInvalido("El Gerente debe capturar sus observaciones al rechazar una cotización.")
        self.estado = E.REQUIERE_AJUSTE
        self.observaciones_del_gerente = observaciones.strip()
        self._registrar(ev.CotizacionRechazadaPorGerente(fecha, self.id, str(self.numero_orden),
                                                         self.observaciones_del_gerente))

    def ajustar(self, lineas: list[LineaDeCotizacion]) -> None:
        """CA-009: la versión ajustada sigue las indicaciones del Gerente y no regresa a revisión."""
        self._exigir_estado(E.REQUIERE_AJUSTE, "ajustar")
        self._lineas = {}
        self._asignar_lineas(lineas)
        self.estado = E.PENDIENTE_DE_AUTORIZACION_DEL_CLIENTE

    # ------------------------------------------------------------------ Asesor y cliente
    def marcar_presentada(self, fecha: datetime) -> None:
        """CA-006: inicia el plazo de 48 horas. CA-007: no se presenta sin aprobación gerencial."""
        self._exigir_estado(E.PENDIENTE_DE_AUTORIZACION_DEL_CLIENTE, "presentar")
        self.fecha_presentacion = fecha
        self._registrar(ev.CotizacionPresentada(fecha, self.id, str(self.numero_orden)))

    def registrar_decision(self, lineas_autorizadas: set[int], autorizante: Autorizante,
                           fecha: datetime) -> DecisionDelCliente:
        """US-006: autorización total, parcial o rechazo total."""
        self._exigir_estado(E.PENDIENTE_DE_AUTORIZACION_DEL_CLIENTE, "registrar la decisión de")
        desconocidas = set(lineas_autorizadas) - set(self._lineas)
        if desconocidas:
            raise ValorInvalido(f"La cotización no tiene los trabajos: {sorted(desconocidas)}.")

        autorizados, no_autorizados = [], []
        for linea in self.lineas:
            decidido = TrabajoDecidido(linea.numero, linea.descripcion, linea.subtotal)
            if linea.numero in lineas_autorizadas:
                linea.decision = DecisionDeLinea.AUTORIZADA
                autorizados.append(decidido)
            else:
                linea.decision = DecisionDeLinea.NO_AUTORIZADA
                no_autorizados.append(decidido)

        if not autorizados:
            self.estado = E.RECHAZADA
            self._registrar(ev.CotizacionRechazadaPorCliente(fecha, self.id, str(self.numero_orden),
                                                             autorizante.nombre))
        else:
            parcial = bool(no_autorizados)
            self.estado = E.AUTORIZADA_PARCIALMENTE if parcial else E.AUTORIZADA
            self._registrar(ev.CotizacionAutorizada(fecha, self.id, str(self.numero_orden),
                                                    parcial, autorizante.nombre))
        self.decision = DecisionDelCliente(tuple(autorizados), tuple(no_autorizados),
                                           autorizante, fecha, self.tipo)
        return self.decision

    # ------------------------------------------------------------------ apoyo
    def _asignar_lineas(self, lineas: list[LineaDeCotizacion]) -> None:
        if not lineas:
            raise CotizacionSinTrabajos("Una cotización debe incluir al menos un trabajo.")
        for linea in lineas:
            if linea.numero in self._lineas:
                raise ValorInvalido(f"El trabajo {linea.numero} está repetido en la cotización.")
            self._lineas[linea.numero] = linea

    def _exigir_estado(self, esperado: EstadoCotizacion, accion: str) -> None:
        if self.estado is not esperado:
            raise OperacionDeCotizacionNoPermitida(
                f"No se puede {accion} la cotización {self.version} porque está en "
                f"«{self.estado.value}»; debe estar en «{esperado.value}»."
            )
