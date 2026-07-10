# Smoke E2E con Playwright

## Objetivo
Validar en un navegador real que la app Streamlit en modo `production-test` cubre el flujo productivo actual:

1. carga de un PDF sanitizado,
2. análisis previo con `Analizar Extractos`,
3. procesamiento final con `Procesar Extractos`,
4. resumen visible y descargas Excel/CSV disponibles,
5. backoffice `Aprender Formatos` oculto.

## Preparación local
Instalar dependencias Python si todavía no están instaladas:

```bash
venv\Scripts\python.exe -m pip install -r requirements.txt
```

Instalar dependencias Node del smoke:

```bash
npm install
```

Instalar Chromium para Playwright:

```bash
npx playwright install chromium
```

Si Node falla con `UNABLE_TO_VERIFY_LEAF_SIGNATURE` en Windows, reintentar usando la CA del sistema:

```powershell
$env:NODE_OPTIONS='--use-system-ca'; npx playwright install chromium
```

## Ejecución automatizada
Ejecutar el smoke oficial:

```bash
npm run test:e2e
```

`playwright.config.js` levanta automáticamente la app con:

```bash
venv\Scripts\python.exe scripts/run_app.py --mode production-test
```

En Linux/macOS o CI usa `python scripts/run_app.py --mode production-test` por defecto. También se puede sobrescribir con:

```bash
BANK_STATEMENT_E2E_SERVER_CMD="python scripts/run_app.py --mode production-test" npm run test:e2e
```

## Qué valida el smoke
El test `tests/e2e/production_smoke.spec.js` verifica que:

- `Aprender Formatos` no aparece en `production-test`,
- el PDF sanitizado se carga como archivo válido,
- `Analizar Extractos` detecta Banco Galicia,
- el documento simple queda listo sin selección de scopes,
- `Procesar Extractos` genera resultados,
- aparecen `Resumen del Proceso`, `Vista Previa de Transacciones`, `Descargar Archivo Excel` y `Descargar Archivo CSV`,
- el total de transacciones es `3`, según la fixture sanitizada.

## Alcance
Este smoke cubre integración UI + navegador + Streamlit + parsing + exportaciones visibles. No reemplaza:

- `venv\Scripts\python.exe -m pytest -q`,
- `venv\Scripts\python.exe format_cli.py regress`,
- pruebas manuales con PDFs reales cuando se valida un banco nuevo.

El CI remoto ejecuta este smoke como job separado en `.github/workflows/ci.yml` con instalación de Node, `npm ci`, `npx playwright install --with-deps chromium` y `npm run test:e2e`.
