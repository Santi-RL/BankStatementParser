# Analizador de Extractos Bancarios

Esta aplicación convierte extractos bancarios en PDF a archivos Excel mediante la interfaz de Streamlit.

## Documentación interna

Si vas a retomar el proyecto o a trabajar con agentes, empieza por estos archivos:

- `AGENTS.md`
- `docs/PROJECT_CONTEXT.md`
- `docs/PROJECT_STATUS.md`
- `docs/ROADMAP.md`
- `docs/FILE_MAP.md`

## Bancos compatibles

Actualmente hay formatos declarativos publicados para:
- Banco Galicia (Argentina)
- Banco Roela (Argentina)
- Chase / JPMorgan Chase
- BBVA (extracto consolidado con múltiples tarjetas y cuentas, y resumen simple)
- Mercado Pago
- Brubank

Si el banco es detectado pero no tiene una spec publicada, el resultado esperado es `unknown_format`.

## Muestras PDF locales

Los extractos bancarios reales usados para validación manual deben guardarse siempre en:

```text
local_samples/<bank_id>/
```

`local_samples/` está ignorado por Git porque esos archivos pueden contener datos bancarios y personales. No guardar PDFs reales en `attached_assets/`, `parser_specs/` ni ninguna otra ruta versionada. Para tests y regresión compartidos, usar únicamente fixtures sanitizadas bajo `parser_specs/<bank_id>/<format_id>/fixtures/`.

Esta exclusión evita nuevos commits, pero no borra PDFs presentes en el historial anterior. Antes de exponer públicamente el repositorio debe limpiarse también el historial Git y actualizarse el remoto.

## Instalación de Dependencias

Antes de ejecutar la aplicación instala las dependencias con pip:

```bash
pip install -r requirements.txt
```

## Ejecución de la Aplicación

El comando oficial del repo es:

```bash
venv\Scripts\python.exe scripts/run_app.py --mode local
```

Opciones útiles:

```bash
venv\Scripts\python.exe scripts/run_app.py --mode local --debug
venv\Scripts\python.exe scripts/run_app.py --mode production-test
```

- `local`: deja visible el backoffice `Aprender Formatos` y permite activar debug desde la barra lateral.
- `production-test`: oculta el backoffice, desactiva el debug interactivo y sanitiza los errores mostrados al usuario.
- Los logs rotan en `logs/app.log`.

Si prefieres arrancar Streamlit manualmente:

```bash
venv\Scripts\streamlit.exe run app.py -- --mode local
```

## Motor Declarativo de Formatos

El proyecto ahora incorpora un registro declarativo de parsers en `parser_specs/`.

- Los formatos publicados son la única vía de parsing en runtime.
- La app incluye un backoffice `Aprender Formatos` para crear borradores y publicarlos.
- Existe un modo endurecido `production-test` para primeras pruebas controladas.
- La UI productiva separa el flujo en `Analizar Extractos` y `Procesar Extractos`.
- Cuando un PDF contiene múltiples entidades extraíbles, la app exige una selección previa por cuenta o tarjeta antes de procesar.
- La salida mantiene un CSV consolidado y genera hojas/tabs separadas por entidad cuando corresponde.
- La CLI interna está disponible con:

```bash
venv\Scripts\python.exe format_cli.py train ...
venv\Scripts\python.exe format_cli.py validate-draft ...
venv\Scripts\python.exe format_cli.py publish ...
venv\Scripts\python.exe format_cli.py regress
```

## Tests

El runner oficial de tests local es:

```bash
venv\Scripts\python.exe -m pytest -q
```

La regresión declarativa se ejecuta con:

```bash
venv\Scripts\python.exe format_cli.py regress
```

Hay cuatro capas:
- tests unitarios,
- tests de integración con PDFs reales ya presentes en el repo y fixtures sanitizadas,
- tests de regresión para specs declarativas,
- smoke E2E con navegador sobre `production-test`.

El CI remoto está configurado en `.github/workflows/ci.yml` y corre en push/PR a `main`:
- `python -m pytest -q`
- `python format_cli.py regress`

Toda implementación nueva que cambie comportamiento, parsing, specs, exportaciones, UI o seguridad debe agregar o actualizar tests proporcionales al riesgo. Los cambios puramente documentales pueden omitir tests.

El smoke E2E con navegador se ejecuta con:

```bash
npm install
npx playwright install chromium
npm run test:e2e
```

La guía completa queda en `docs/E2E_PLAYWRIGHT.md`.

## Primera prueba en producción

- Formatos hoy soportados: Galicia Argentina, Roela Argentina, Chase, BBVA (consolidado y resumen simple), Mercado Pago y Brubank.
- El modo recomendado para la primera prueba controlada es `production-test`.
- El runbook operativo breve está en `docs/PRODUCTION_TEST_RUNBOOK.md`.

## Agregar nuevos formatos

Para soportar un banco adicional solo hace falta crear un nuevo formato declarativo en `parser_specs/`. No es necesario escribir código Python.

La guía completa para contribuir un banco nuevo está en [`CONTRIBUTING.md`](CONTRIBUTING.md), incluyendo:
- Paso a paso con la CLI (`train`, `validate-draft`, `publish`)
- Checklist para PRs
- Convenciones de naming
- Ejemplos de specs mínimas y por secciones
- Referencia de campos y formatos avanzados
