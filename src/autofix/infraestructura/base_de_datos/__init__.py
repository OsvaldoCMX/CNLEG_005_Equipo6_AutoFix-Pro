"""Adaptador de base de datos con SQLAlchemy (Unidad 5).

Implementa las mismas interfaces que la versión en memoria (Repositories, Unidad de
Trabajo y LectorDeOrdenes). En las pruebas se usa SQLite en memoria como motor de
prueba; el motor del Data Center se conectará después cambiando solo la URL (ADR-004).
"""
