"""Tablas de la base de datos de AutoFix Pro.

El dominio no conoce estas clases: los repositorios traducen filas <-> Aggregates.
Los importes se guardan en centavos (enteros) para no perder precisión.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, ForeignKeyConstraint, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class ClienteFila(Base):
    __tablename__ = "clientes"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    tipo: Mapped[str] = mapped_column(String(20))
    empresa: Mapped[str | None] = mapped_column(String(120))
    responsable_nombre: Mapped[str | None] = mapped_column(String(120))
    responsable_telefono: Mapped[str | None] = mapped_column(String(20))
    responsable_correo: Mapped[str | None] = mapped_column(String(120))


class OrdenFila(Base):
    __tablename__ = "ordenes"

    numero: Mapped[str] = mapped_column(String(20), primary_key=True)
    id_cliente: Mapped[str] = mapped_column(ForeignKey("clientes.id"))
    es_cliente_de_flotilla: Mapped[bool]
    placas: Mapped[str] = mapped_column(String(15))
    motivo_de_ingreso: Mapped[str] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(String(40))
    fecha_ingreso: Mapped[datetime]
    ultima_actualizacion: Mapped[datetime]
    tecnico_de_diagnostico: Mapped[str | None] = mapped_column(String(120))
    diagnostico: Mapped[str | None] = mapped_column(Text)
    cotizada: Mapped[bool] = mapped_column(default=False)
    rechazo_total: Mapped[bool] = mapped_column(default=False)
    fecha_ingreso_a_fila: Mapped[datetime | None]
    estado_antes_de_espera: Mapped[str | None] = mapped_column(String(40))
    pago_centavos: Mapped[int | None]
    pago_forma: Mapped[str | None] = mapped_column(String(20))
    pago_registrado_en: Mapped[datetime | None]
    credito_centavos: Mapped[int | None]
    credito_registrado_en: Mapped[datetime | None]
    fecha_entrega: Mapped[datetime | None]

    trabajos: Mapped[list[TrabajoFila]] = relationship(
        cascade="all, delete-orphan", order_by="TrabajoFila.id")
    solicitudes: Mapped[list[SolicitudDeCompraFila]] = relationship(
        cascade="all, delete-orphan", order_by="SolicitudDeCompraFila.id")


class TrabajoFila(Base):
    __tablename__ = "trabajos"

    numero_orden: Mapped[str] = mapped_column(ForeignKey("ordenes.numero"), primary_key=True)
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    descripcion: Mapped[str] = mapped_column(Text)
    importe_centavos: Mapped[int]
    estado: Mapped[str] = mapped_column(String(20))
    tecnico: Mapped[str | None] = mapped_column(String(120))


class SolicitudDeCompraFila(Base):
    __tablename__ = "solicitudes_de_compra"

    numero_orden: Mapped[str] = mapped_column(ForeignKey("ordenes.numero"), primary_key=True)
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    id_trabajo: Mapped[int]
    refaccion: Mapped[str] = mapped_column(String(200))
    cantidad: Mapped[int]
    fecha_solicitud: Mapped[datetime]
    estado: Mapped[str] = mapped_column(String(20))
    fecha_llegada: Mapped[datetime | None]


class CotizacionFila(Base):
    __tablename__ = "cotizaciones"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    numero_orden: Mapped[str] = mapped_column(ForeignKey("ordenes.numero"))
    tipo: Mapped[str] = mapped_column(String(20))
    version: Mapped[int]
    estado: Mapped[str] = mapped_column(String(50))
    total_centavos: Mapped[int]          # dato derivado: lo usa el lado de lectura (CQRS)
    generada_en: Mapped[datetime]
    fecha_presentacion: Mapped[datetime | None]
    observaciones_del_gerente: Mapped[str | None] = mapped_column(Text)
    decision_autorizante: Mapped[str | None] = mapped_column(String(120))
    decision_rol: Mapped[str | None] = mapped_column(String(40))
    decision_registrada_en: Mapped[datetime | None]

    lineas: Mapped[list[LineaDeCotizacionFila]] = relationship(
        cascade="all, delete-orphan", order_by="LineaDeCotizacionFila.numero")


class LineaDeCotizacionFila(Base):
    __tablename__ = "lineas_de_cotizacion"

    id_cotizacion: Mapped[str] = mapped_column(ForeignKey("cotizaciones.id"), primary_key=True)
    numero: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    descripcion: Mapped[str] = mapped_column(Text)
    mano_de_obra_centavos: Mapped[int]
    decision: Mapped[str | None] = mapped_column(String(20))

    refacciones: Mapped[list[RefaccionCotizadaFila]] = relationship(
        cascade="all, delete-orphan", order_by="RefaccionCotizadaFila.posicion")


class RefaccionCotizadaFila(Base):
    __tablename__ = "refacciones_cotizadas"
    __table_args__ = (
        ForeignKeyConstraint(["id_cotizacion", "numero_linea"],
                             ["lineas_de_cotizacion.id_cotizacion", "lineas_de_cotizacion.numero"]),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    id_cotizacion: Mapped[str] = mapped_column(String(20))
    numero_linea: Mapped[int]
    posicion: Mapped[int]
    descripcion: Mapped[str] = mapped_column(String(200))
    cantidad: Mapped[int]
    precio_unitario_centavos: Mapped[int]


class SecuenciaFila(Base):
    """Folios consecutivos (OS-0001, COT-0001). Se revierten junto con la transacción."""

    __tablename__ = "secuencias"

    nombre: Mapped[str] = mapped_column(String(30), primary_key=True)
    ultimo_valor: Mapped[int] = mapped_column(default=0)
