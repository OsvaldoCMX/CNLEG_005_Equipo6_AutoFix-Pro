"""Traducción entre los Aggregates del dominio y las filas de la base de datos.

Leer = reconstruir el Aggregate exactamente como estaba (sin volver a ejecutar reglas
ni generar eventos). Escribir = copiar su estado a las filas, incluidas sus partes
internas (trabajos, solicitudes, líneas y refacciones).
"""
from __future__ import annotations

from decimal import Decimal

from autofix.dominio.clientes.cliente import Cliente, ResponsableDeFlotilla, TipoCliente
from autofix.dominio.compartido.valores import Dinero, NumeroOrden, Placas
from autofix.dominio.cotizaciones.cotizacion import Cotizacion
from autofix.dominio.cotizaciones.linea_de_cotizacion import DecisionDeLinea, LineaDeCotizacion
from autofix.dominio.cotizaciones.valores import (
    Autorizante,
    DecisionDelCliente,
    EstadoCotizacion,
    RefaccionCotizada,
    RolDeAutorizante,
    TipoCotizacion,
    TrabajoDecidido,
    VersionCotizacion,
)
from autofix.dominio.ordenes.estados import EstadoOrden, EstadoSolicitud, EstadoTrabajo
from autofix.dominio.ordenes.orden_de_servicio import OrdenDeServicio
from autofix.dominio.ordenes.trabajo import SolicitudDeCompra, Trabajo
from autofix.dominio.ordenes.valores import CargoACredito, FormaDePago, Pago
from autofix.infraestructura.base_de_datos.tablas import (
    ClienteFila,
    CotizacionFila,
    LineaDeCotizacionFila,
    OrdenFila,
    RefaccionCotizadaFila,
    SolicitudDeCompraFila,
    TrabajoFila,
)


# ------------------------------------------------------------------ dinero
def a_centavos(dinero: Dinero) -> int:
    return int(dinero.monto * 100)


def de_centavos(centavos: int) -> Dinero:
    return Dinero(Decimal(centavos) / 100)


# ------------------------------------------------------------------ Cliente
def escribir_cliente(cliente: Cliente, fila: ClienteFila) -> None:
    fila.nombre = cliente.nombre
    fila.tipo = cliente.tipo.value
    fila.empresa = cliente.empresa
    responsable = cliente.responsable
    fila.responsable_nombre = responsable.nombre if responsable else None
    fila.responsable_telefono = responsable.telefono if responsable else None
    fila.responsable_correo = responsable.correo if responsable else None


def leer_cliente(fila: ClienteFila) -> Cliente:
    responsable = None
    if fila.responsable_nombre:
        responsable = ResponsableDeFlotilla(fila.responsable_nombre, fila.responsable_telefono or "",
                                            fila.responsable_correo or "")
    return Cliente(fila.id, fila.nombre, TipoCliente(fila.tipo), fila.empresa, responsable)


# ------------------------------------------------------------------ Orden de Servicio
def escribir_orden(orden: OrdenDeServicio, fila: OrdenFila) -> None:
    fila.id_cliente = orden.id_cliente
    fila.es_cliente_de_flotilla = orden.es_cliente_de_flotilla
    fila.placas = str(orden.placas)
    fila.motivo_de_ingreso = orden.motivo_de_ingreso
    fila.estado = orden.estado.value
    fila.fecha_ingreso = orden.fecha_ingreso
    fila.ultima_actualizacion = orden.ultima_actualizacion
    fila.tecnico_de_diagnostico = orden.tecnico_de_diagnostico
    fila.diagnostico = orden.diagnostico
    fila.cotizada = orden.cotizada
    fila.rechazo_total = orden.rechazo_total
    fila.fecha_ingreso_a_fila = orden.fecha_ingreso_a_fila
    antes = orden._estado_antes_de_espera
    fila.estado_antes_de_espera = antes.value if antes else None
    fila.pago_centavos = a_centavos(orden.pago.monto) if orden.pago else None
    fila.pago_forma = orden.pago.forma.value if orden.pago else None
    fila.pago_registrado_en = orden.pago.registrado_en if orden.pago else None
    credito = orden.cargo_a_credito
    fila.credito_centavos = a_centavos(credito.monto) if credito else None
    fila.credito_registrado_en = credito.registrado_en if credito else None
    fila.fecha_entrega = orden.fecha_entrega

    existentes = {t.id: t for t in fila.trabajos}
    for trabajo in orden.trabajos:
        t = existentes.pop(trabajo.id, None)
        if t is None:
            t = TrabajoFila(id=trabajo.id)
            fila.trabajos.append(t)
        t.descripcion = trabajo.descripcion
        t.importe_centavos = a_centavos(trabajo.importe)
        t.estado = trabajo.estado.value
        t.tecnico = trabajo.tecnico
    for sobrante in existentes.values():
        fila.trabajos.remove(sobrante)

    existentes_s = {s.id: s for s in fila.solicitudes}
    for solicitud in orden.solicitudes:
        s = existentes_s.pop(solicitud.id, None)
        if s is None:
            s = SolicitudDeCompraFila(id=solicitud.id)
            fila.solicitudes.append(s)
        s.id_trabajo = solicitud.id_trabajo
        s.refaccion = solicitud.refaccion
        s.cantidad = solicitud.cantidad
        s.fecha_solicitud = solicitud.fecha_solicitud
        s.estado = solicitud.estado.value
        s.fecha_llegada = solicitud.fecha_llegada
    for sobrante in existentes_s.values():
        fila.solicitudes.remove(sobrante)


def leer_orden(fila: OrdenFila) -> OrdenDeServicio:
    orden = OrdenDeServicio(NumeroOrden(fila.numero), fila.id_cliente, fila.es_cliente_de_flotilla,
                            Placas(fila.placas), fila.motivo_de_ingreso, fila.fecha_ingreso)
    orden.estado = EstadoOrden(fila.estado)
    orden.ultima_actualizacion = fila.ultima_actualizacion
    orden.tecnico_de_diagnostico = fila.tecnico_de_diagnostico
    orden.diagnostico = fila.diagnostico
    orden.cotizada = fila.cotizada
    orden.rechazo_total = fila.rechazo_total
    orden.fecha_ingreso_a_fila = fila.fecha_ingreso_a_fila
    orden.fecha_entrega = fila.fecha_entrega
    if fila.estado_antes_de_espera:
        orden._estado_antes_de_espera = EstadoOrden(fila.estado_antes_de_espera)
    if fila.pago_centavos is not None:
        orden.pago = Pago(de_centavos(fila.pago_centavos), FormaDePago(fila.pago_forma),
                          fila.pago_registrado_en)
    if fila.credito_centavos is not None:
        orden.cargo_a_credito = CargoACredito(de_centavos(fila.credito_centavos),
                                              fila.credito_registrado_en)
    for t in fila.trabajos:
        trabajo = Trabajo(t.id, t.descripcion, de_centavos(t.importe_centavos), EstadoTrabajo(t.estado))
        trabajo.tecnico = t.tecnico
        orden._trabajos[trabajo.id] = trabajo
    for s in fila.solicitudes:
        solicitud = SolicitudDeCompra(s.id, s.id_trabajo, s.refaccion, s.cantidad, s.fecha_solicitud)
        solicitud.estado = EstadoSolicitud(s.estado)
        solicitud.fecha_llegada = s.fecha_llegada
        orden._solicitudes[solicitud.id] = solicitud
    return orden


# ------------------------------------------------------------------ Cotización
def escribir_cotizacion(cotizacion: Cotizacion, fila: CotizacionFila) -> None:
    fila.numero_orden = str(cotizacion.numero_orden)
    fila.tipo = cotizacion.tipo.value
    fila.version = cotizacion.version.numero
    fila.estado = cotizacion.estado.value
    fila.total_centavos = a_centavos(cotizacion.total)
    fila.generada_en = cotizacion.generada_en
    fila.fecha_presentacion = cotizacion.fecha_presentacion
    fila.observaciones_del_gerente = cotizacion.observaciones_del_gerente
    decision = cotizacion.decision
    fila.decision_autorizante = decision.autorizante.nombre if decision else None
    fila.decision_rol = decision.autorizante.rol.value if decision else None
    fila.decision_registrada_en = decision.registrada_en if decision else None

    existentes = {linea.numero: linea for linea in fila.lineas}
    for linea in cotizacion.lineas:
        f = existentes.pop(linea.numero, None)
        if f is None:
            f = LineaDeCotizacionFila(numero=linea.numero)
            fila.lineas.append(f)
        f.descripcion = linea.descripcion
        f.mano_de_obra_centavos = a_centavos(linea.mano_de_obra)
        f.decision = linea.decision.value if linea.decision else None
        # Las refacciones son Value Objects: se reemplazan completas.
        f.refacciones = [
            RefaccionCotizadaFila(posicion=i, descripcion=r.descripcion, cantidad=r.cantidad,
                                  precio_unitario_centavos=a_centavos(r.precio_unitario))
            for i, r in enumerate(linea.refacciones, start=1)
        ]
    for sobrante in existentes.values():
        fila.lineas.remove(sobrante)


def leer_cotizacion(fila: CotizacionFila) -> Cotizacion:
    lineas = []
    for f in fila.lineas:
        refacciones = tuple(RefaccionCotizada(r.descripcion, r.cantidad,
                                              de_centavos(r.precio_unitario_centavos))
                            for r in f.refacciones)
        linea = LineaDeCotizacion(f.numero, f.descripcion, de_centavos(f.mano_de_obra_centavos),
                                  refacciones)
        linea.decision = DecisionDeLinea(f.decision) if f.decision else None
        lineas.append(linea)
    tipo = TipoCotizacion(fila.tipo)
    cotizacion = Cotizacion(fila.id, NumeroOrden(fila.numero_orden), tipo,
                            VersionCotizacion(fila.version), lineas, fila.generada_en)
    cotizacion.estado = EstadoCotizacion(fila.estado)
    cotizacion.fecha_presentacion = fila.fecha_presentacion
    cotizacion.observaciones_del_gerente = fila.observaciones_del_gerente
    if fila.decision_registrada_en is not None:
        def decididos(decision: DecisionDeLinea) -> tuple[TrabajoDecidido, ...]:
            return tuple(TrabajoDecidido(linea.numero, linea.descripcion, linea.subtotal)
                         for linea in cotizacion.lineas if linea.decision is decision)

        cotizacion.decision = DecisionDelCliente(
            decididos(DecisionDeLinea.AUTORIZADA), decididos(DecisionDeLinea.NO_AUTORIZADA),
            Autorizante(fila.decision_autorizante, RolDeAutorizante(fila.decision_rol)),
            fila.decision_registrada_en, tipo)
    return cotizacion
