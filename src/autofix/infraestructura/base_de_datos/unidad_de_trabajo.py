"""Unit of Work con SQLAlchemy: la sesión es el límite de la transacción.

confirmar() escribe todos los Aggregates usados en la operación y hace commit;
si algo falla antes, _deshacer() hace rollback y la base queda como estaba (ADR-002).
"""
from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from autofix.aplicacion.unidad_de_trabajo import UnidadDeTrabajo
from autofix.dominio.compartido.eventos import EventoDeDominio
from autofix.infraestructura.base_de_datos.repositorios import (
    RepositorioDeClientesSqlAlchemy,
    RepositorioDeCotizacionesSqlAlchemy,
    RepositorioDeOrdenesSqlAlchemy,
)


class UnidadDeTrabajoSqlAlchemy(UnidadDeTrabajo):
    def __init__(self, fabrica_de_sesiones: sessionmaker[Session]) -> None:
        self._fabrica = fabrica_de_sesiones
        self._sesion: Session | None = None

    def _iniciar(self) -> None:
        self._sesion = self._fabrica()
        self._vistos: list = []
        self.clientes = RepositorioDeClientesSqlAlchemy(self._sesion)
        self.ordenes = RepositorioDeOrdenesSqlAlchemy(self._sesion, self._vistos)
        self.cotizaciones = RepositorioDeCotizacionesSqlAlchemy(self._sesion, self._vistos)

    def _recolectar_eventos(self) -> list[EventoDeDominio]:
        eventos: list[EventoDeDominio] = []
        vistos_ids = set()
        for agregado in self._vistos:
            if id(agregado) not in vistos_ids:
                vistos_ids.add(id(agregado))
                eventos.extend(agregado.extraer_eventos())
        return sorted(eventos, key=lambda e: e.ocurrido_en)

    def _confirmar(self) -> None:
        try:
            # Orden de escritura según las llaves foráneas: cliente -> orden -> cotización.
            self.clientes.escribir_cambios()
            self._sesion.flush()
            self.ordenes.escribir_cambios()
            self._sesion.flush()
            self.cotizaciones.escribir_cambios()
            self._sesion.commit()
        finally:
            self._sesion.close()

    def _deshacer(self) -> None:
        if self._sesion is not None:
            self._sesion.rollback()
            self._sesion.close()
        self._vistos = []
