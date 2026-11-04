"""Domain Service: ¿quién puede autorizar una cotización? (US-006, US-016, CA-029).

La regla necesita datos de dos Aggregates (el Cliente y la decisión sobre la
Cotización), por eso no pertenece naturalmente a ninguno de los dos.
"""
from __future__ import annotations

from autofix.dominio.clientes.cliente import Cliente
from autofix.dominio.compartido.errores import AutorizanteNoValido
from autofix.dominio.cotizaciones.valores import Autorizante, RolDeAutorizante


class VerificadorDeAutorizante:
    def verificar(self, cliente: Cliente, autorizante: Autorizante) -> None:
        if cliente.es_de_flotilla:
            responsable = cliente.responsable
            if (autorizante.rol is not RolDeAutorizante.RESPONSABLE_DE_FLOTILLA
                    or autorizante.nombre.casefold() != responsable.nombre.casefold()):
                raise AutorizanteNoValido(
                    f"Para la flotilla de {cliente.empresa} solo puede autorizar el Responsable de Flotilla "
                    f"({responsable.nombre}); el conductor no puede autorizar.")
        elif autorizante.rol is not RolDeAutorizante.CLIENTE:
            raise AutorizanteNoValido("En un cliente particular, la decisión la registra el propio cliente.")
