# AutoFix Pro — Unidad 5: Integración, pruebas y calidad

**Materia:** Componentes de Lógica de Negocio · FIME UANL
**Profesor:** Miguel Ángel Gómez Marroquín
**Equipo 6:**

| Integrante | Matrícula |
|---|---|
| Jesus Eduardo Moreno Osoria | 2136063 |
| Osvaldo Salvador Cárdenas Mejorado | 2141553 |
| Abraham Sandoval De León | 2136604 |

**Repositorio:** _(agregar enlace)_

Este repositorio tiene dos partes:

1. **Laboratorio guiado (pasos 1 a 8):** el proyecto base de pedidos del profesor (`src/domain.py`, `src/application.py`, `src/repository.py`, `src/security.py`) con las pruebas nuevas que pide cada paso.
2. **Aplicación al PIA (paso 9):** el código base de AutoFix Pro de la Unidad 3 (`src/autofix/`) con su matriz de 19 casos, pruebas de persistencia con base de datos y pruebas con servicios externos simulados.

## Resultados

| Verificación | Resultado |
|---|---|
| Pruebas | 172 aprobadas, 0 fallidas |
| Cobertura de `src/` | 99.51 % de líneas y 95.18 % de ramas (mínimo exigido: 80 %) |
| Cobertura del dominio de AutoFix Pro | 100 % de líneas y de ramas |
| Ruff | sin errores |
| Matriz del laboratorio (CP01–CP15) | 15 de 15 pasan → `reportes/matriz_laboratorio_resultados.csv` |
| Matriz del PIA (PIA-01 a PIA-19) | 19 de 19 pasan, en memoria y en base de datos → `reportes/matriz_pia_autofix_resultados.csv` |

## Qué necesitas instalar

- **Python 3.11 o superior** (marca “Add python.exe to PATH” al instalar en Windows).
- **Git** y una cuenta de **GitHub** (para el paso 8).
- **VS Code** (recomendado).
- **SQLite no se instala:** viene incluido dentro de Python. Las pruebas crean una base de datos *en memoria* que existe solo mientras corre la prueba y desaparece al terminar.
- *Opcional:* DB Browser for SQLite, solo si quieres abrir el archivo de ejemplo `pedidos_prueba.sqlite3` del profesor.

`pip install -r requirements.txt` instala lo demás: pytest, pytest-cov, SQLAlchemy y Ruff.

## Cómo ejecutarlo

Abre una terminal **dentro de la carpeta del proyecto** (donde está este README).

**Windows (PowerShell):**

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -v
```

Si PowerShell no deja activar el entorno, ejecuta una vez
`Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` o usa directamente
`.venv\Scripts\python.exe -m pytest -v`.

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -v
```

**Calidad y cobertura (paso 7):**

```bash
python -m ruff check src tests
python -m pytest -v --cov=src --cov-report=term-missing --cov-report=html --cov-fail-under=80
```

Después abre `htmlcov/index.html` en el navegador para ver el reporte de cobertura. Para medir también las ramas (`if`/`else`), agrega `--cov-branch`.

La carpeta `htmlcov/` no se sube al repositorio (está en `.gitignore`): se entrega aparte comprimida, y GitHub Actions también la guarda como artefacto en cada ejecución.

**Comandos útiles:**

| Quiero… | Comando |
|---|---|
| Correr solo un archivo | `python -m pytest tests/test_order.py -v` |
| Correr solo el PIA | `python -m pytest tests/autofix -v` |
| Cobertura solo del PIA | `python -m pytest --cov=src/autofix --cov-report=term-missing` |
| Correr una prueba por nombre | `python -m pytest -k cannot_confirm_twice -v` |

## Estructura

```
autofix-pro-u5/
├── .github/workflows/ci.yml        Pipeline: Ruff + pytest con cobertura ≥ 80 % + compilación
├── datos/
│   ├── casos_de_prueba.csv         Casos CP01–CP15 del profesor
│   ├── pedidos_prueba.csv          Pedidos de ejemplo del profesor
│   ├── clientes_prueba.csv         Clientes de ejemplo del profesor
│   └── matriz_pia_autofix.csv      Matriz del PIA: 19 casos (entrada y resultado esperado)
├── reportes/                       Matrices "esperado vs real" (se regeneran con cada pytest)
├── src/
│   ├── domain.py · application.py · repository.py · security.py    Laboratorio (pedidos)
│   └── autofix/                    AutoFix Pro (código base de la Unidad 3 + adaptador de base de datos)
│       ├── dominio/                Aggregates, Value Objects, reglas, eventos, interfaces de Repository
│       ├── aplicacion/             Application Services, Commands, Queries, Unidad de Trabajo, puertos
│       ├── infraestructura/
│       │   ├── memoria/            Repositorios en memoria (Unidad 3)
│       │   ├── base_de_datos/      NUEVO: Repositorios y Unidad de Trabajo con SQLAlchemy
│       │   └── adaptadores.py      Reloj, alertas internas y generador de PDF simulado
│       └── composicion.py          Arma la aplicación en memoria o con base de datos
└── tests/
    ├── test_order.py               Pasos 2 y 3 (pruebas unitarias y TDD)
    ├── test_repository.py          Paso 4 (commit y rollback)
    ├── test_service.py             Paso 5 (pasarela de pago con Mock)
    ├── test_security.py            Paso 6 (autorización con fechas fijas)
    ├── test_casos_csv.py           CP01–CP15 leídos con csv.DictReader
    └── autofix/
        ├── test_matriz_pia.py                  Paso 9: los 19 casos del CSV (memoria y base de datos)
        ├── test_persistencia_base_de_datos.py  Paso 9: commit, rollback, atomicidad y consultas
        ├── test_servicios_externos_mock.py     Paso 9: PDF y alertas simulados con Mock
        ├── test_tdd_diagnostico.py             Paso 9: ciclo TDD sobre una regla del PIA
        ├── test_reglas_complementarias.py      Invariantes del dominio (cobertura de ramas)
        ├── test_casos_de_uso.py                Escenarios de la Unidad 3 (regresión)
        └── test_arquitectura.py                Regla de dependencias entre capas (Unidad 3)
```

## Laboratorio: qué se hizo en cada paso

| Paso | Qué se agregó | Dónde |
|---|---|---|
| 2 | VIP $200 → cobro $170; regular $200 → cobro $200 | `tests/test_order.py` |
| 3 | TDD: `test_cannot_confirm_twice` en ROJO → regla mínima en `Order.confirm()` → VERDE → refactor a `_ensure_can_be_confirmed()` | `tests/test_order.py`, `src/domain.py` |
| 4 | Pedido id=2, total 250: commit y verificación en una sesión nueva; id duplicado rechazado (unicidad) | `tests/test_repository.py` |
| 5 | Pago rechazado VIP $200: se intentó cobrar $170 y se lanzó `RuntimeError`; timeout de la pasarela sin cobro duplicado | `tests/test_service.py` |
| 6 | Admin cancela pedido NEW de otro usuario; dueño a las 24 h exactas es rechazado; matriz de autorización | `tests/test_security.py` |
| 7 | Ruff limpio y cobertura ≥ 80 % con reporte HTML | — |
| 8 | Pipeline en GitHub Actions (verde → rojo → verde) | `.github/workflows/ci.yml` |

**CP08:** el CSV del profesor esperaba `CONFIRMED` porque el código original permitía confirmar dos veces. Después del ciclo TDD el resultado correcto es `ValueError: already confirmed`; la prueba usa la expectativa actualizada y la matriz de resultados conserva ambas columnas.

**Riesgo de consistencia (paso 5):** `OrderService.checkout()` confirma el pedido *antes* de cobrar, así que si la pasarela rechaza el pago el pedido queda `CONFIRMED` sin pago (la prueba lo deja visible). Propuesta: cobrar primero y confirmar solo si el cobro fue exitoso, o confirmar y cobrar dentro de una misma transacción que se revierta si el cobro falla.

## PIA AutoFix Pro: reglas probadas

Se eligieron cuatro reglas aprobadas en las User Stories, cada una con casos de éxito, error y límite:

| Regla | Criterios | Casos |
|---|---|---|
| R1 · Una cotización inicial **mayor** a $15,000 MXN requiere aprobación del Gerente; las adicionales no | CA-007, CA-016 | PIA-01 a PIA-06 |
| R2 · Sin diagnóstico no se cotiza y, ya cotizada, el diagnóstico no cambia | CA-005, CA-033 | PIA-07 a PIA-10 |
| R3 · En flotillas solo el Responsable de Flotilla autoriza (el conductor no) | CA-029 | PIA-11 a PIA-14 |
| R4 · El vehículo se entrega solo con pago completo o crédito, o tras rechazo total | CA-026, CA-039, CA-041 a CA-043 | PIA-15 a PIA-19 |

Casos límite clave: $15,000.00 exactos (no requiere Gerente) contra $15,000.01 (sí requiere); pago de $6,299.99 contra un total de $6,300.00; nombre del Responsable escrito con otras mayúsculas y espacios.

## Decisiones de diseño (Unidad 5)

- **Se reutilizó el diseño de la Unidad 3 sin cambiar las reglas.** Las pruebas llaman a los mismos Application Services, Aggregates y políticas de los diagramas de clases y secuencia.
- **Adaptador de base de datos nuevo, dominio intacto (ADR-004).** `infraestructura/base_de_datos/` implementa las mismas interfaces que la versión en memoria. Para cambiar de una a otra solo se usa `construir_aplicacion()` o `construir_aplicacion_con_base_de_datos()`.
- **SQLite en memoria es solo el motor de prueba.** El motor de la base de datos del Data Center todavía no se define; cuando se defina, se conecta pasando otra URL a `crear_motor()`.
- **Mismas pruebas para memoria y base de datos.** La matriz del PIA y las pruebas de contrato corren contra las dos implementaciones para demostrar que se comportan igual (principio de sustitución de Liskov).
- **Importes en centavos.** En la base se guardan como enteros para no perder precisión con decimales.
- **Llaves foráneas activas en SQLite** para que la base de prueba rechace datos inconsistentes, como lo haría el motor real.
- **Ruff con reglas fijas.** Desde Ruff 0.16 el conjunto de reglas por defecto creció mucho; el `pyproject.toml` fija la lista para que el resultado sea igual en cualquier computadora.

**Cambio al dominio hecho con TDD:** un diagnóstico vacío o con solo espacios ya no se acepta. Es una interpretación del equipo de CA-005 («diagnóstico registrado por el técnico»), no un criterio escrito por el cliente. La prueba se escribió primero, falló y después se agregó la validación en `OrdenDeServicio.registrar_diagnostico()`.

**Riesgos documentados (servicios externos):** el PDF y las alertas internas se generan *después* del commit. Si fallan, los datos ya quedaron bien guardados, pero el aviso al Gerente se puede perder. Propuesta para el proyecto final: guardar los eventos en una tabla de salida (patrón *outbox*) dentro de la misma transacción y enviarlos después con reintentos.

## Pipeline (GitHub Actions)

Cada `push` o `pull request` ejecuta: instalación de dependencias → `ruff check src tests` → `pytest` con cobertura mínima de 80 % → `python -m compileall -q src`. Al final guarda el reporte HTML y las matrices como artefacto descargable (`reporte-cobertura-y-matrices`).

Que el YAML exista **no bloquea** el *merge* por sí solo: para exigir el pipeline verde hay que activar una regla de protección de la rama `main` en *Settings → Branches* (o *Rulesets*) de GitHub.

**Fallo controlado (verde → rojo → verde):** se hace en una rama aparte (`evidencia-fallo-ci`) para que `main` nunca quede en rojo: se cambia a propósito una aserción, se sube la rama (ejecución roja), se revierte el cambio en la misma rama (ejecución verde) y la rama no se fusiona.

## Uso de IA

Se usó un asistente de IA para proponer casos de éxito, error y límite y para revisar ramas sin cobertura. Cada caso se comparó contra los criterios de aceptación aprobados antes de aceptarlo. El detalle (caso aceptado, corregido y rechazado) está en el reporte de la Unidad 5.
