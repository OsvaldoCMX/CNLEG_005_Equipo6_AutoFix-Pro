"""Configuracion comun de pytest.

Las pruebas que leen una matriz CSV registran aqui su resultado real. Al terminar
la ejecucion se escribe la matriz "esperado vs real" en la carpeta reportes/.
"""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
CARPETA_REPORTES = RAIZ / "reportes"
_RESULTADOS: dict[str, list[dict[str, str]]] = defaultdict(list)


class Matriz:
    """Anota una fila de la matriz de resultados (se usa dentro de las pruebas)."""

    def __init__(self, prueba: str) -> None:
        self._prueba = prueba

    def anotar(self, archivo: str, fila: dict[str, str], real: str, coincide: bool) -> None:
        registro = dict(fila)
        registro["resultado_real"] = real
        registro["estado"] = "PASA" if coincide else "FALLA"
        registro["prueba_pytest"] = self._prueba      # nombre exacto para buscarlo en la salida
        _RESULTADOS[archivo].append(registro)


@pytest.fixture
def matriz(request) -> Matriz:
    return Matriz(request.node.nodeid)


def pytest_sessionfinish(session, exitstatus):
    if not _RESULTADOS:
        return
    CARPETA_REPORTES.mkdir(exist_ok=True)
    for archivo, filas in _RESULTADOS.items():
        filas = sorted(filas, key=lambda f: (f.get("id") or f.get("caso_id") or "",
                                             f.get("implementacion") != "memoria"))
        columnas = list(filas[0].keys())
        with (CARPETA_REPORTES / archivo).open("w", encoding="utf-8-sig", newline="") as f:
            escritor = csv.DictWriter(f, fieldnames=columnas)
            escritor.writeheader()
            escritor.writerows(filas)
