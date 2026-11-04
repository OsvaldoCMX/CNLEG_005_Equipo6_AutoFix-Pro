"""Errores del dominio expresados en términos del negocio.

Cada error explica qué regla del negocio se intentó violar, para que la interfaz
pueda mostrar el mensaje tal cual al usuario.
"""


class ErrorDeDominio(Exception):
    """Base de todos los errores de negocio."""


class ValorInvalido(ErrorDeDominio):
    pass


class TransicionDeEstadoNoPermitida(ErrorDeDominio):
    pass


class OrdenNoEncontrada(ErrorDeDominio):
    pass


class CotizacionNoEncontrada(ErrorDeDominio):
    pass


class ClienteNoEncontrado(ErrorDeDominio):
    pass


class DiagnosticoRequerido(ErrorDeDominio):
    """CA-005: la cotización se genera a partir de un diagnóstico registrado."""


class DiagnosticoNoModificable(ErrorDeDominio):
    """CA-033: una vez generada la cotización, el diagnóstico no se modifica."""


class CotizacionSinTrabajos(ErrorDeDominio):
    pass


class OperacionDeCotizacionNoPermitida(ErrorDeDominio):
    pass


class AutorizanteNoValido(ErrorDeDominio):
    """CA-029: en flotillas solo el Responsable de Flotilla puede autorizar."""


class TrabajoNoEncontrado(ErrorDeDominio):
    pass


class TrabajoNoAutorizado(ErrorDeDominio):
    """CA-020: no se piden refacciones para trabajos no autorizados."""


class SolicitudNoPermitida(ErrorDeDominio):
    pass


class PagoNoPermitido(ErrorDeDominio):
    pass


class EntregaNoPermitida(ErrorDeDominio):
    """CA-042: el vehículo solo se entrega con pago o cargo a crédito registrado."""
