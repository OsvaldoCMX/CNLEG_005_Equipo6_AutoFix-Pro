"""Verifica la regla de dependencias entre capas (principio D, ADR-003/ADR-004).

dominio  -> no importa aplicacion ni infraestructura
aplicacion -> no importa infraestructura
"""
from __future__ import annotations

import ast
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src" / "autofix"


def importaciones(carpeta: str) -> dict[str, set[str]]:
    resultado = {}
    for archivo in (SRC / carpeta).rglob("*.py"):
        modulos = set()
        for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8"))):
            if isinstance(nodo, ast.ImportFrom) and nodo.module:
                modulos.add(nodo.module)
            elif isinstance(nodo, ast.Import):
                modulos.update(a.name for a in nodo.names)
        resultado[str(archivo.relative_to(SRC))] = modulos
    return resultado


class ReglaDeDependencias(unittest.TestCase):
    def test_el_dominio_no_depende_de_aplicacion_ni_infraestructura(self):
        for archivo, modulos in importaciones("dominio").items():
            prohibidos = {m for m in modulos if m.startswith(("autofix.aplicacion", "autofix.infraestructura"))}
            self.assertFalse(prohibidos, f"{archivo} importa {prohibidos}")

    def test_la_aplicacion_no_depende_de_infraestructura(self):
        for archivo, modulos in importaciones("aplicacion").items():
            prohibidos = {m for m in modulos if m.startswith("autofix.infraestructura")}
            self.assertFalse(prohibidos, f"{archivo} importa {prohibidos}")

    def test_el_dominio_no_usa_bases_de_datos_ni_frameworks(self):
        for archivo, modulos in importaciones("dominio").items():
            prohibidos = {m for m in modulos if m.split(".")[0] in {"sqlite3", "sqlalchemy", "django", "flask"}}
            self.assertFalse(prohibidos, f"{archivo} importa {prohibidos}")


if __name__ == "__main__":
    unittest.main()
