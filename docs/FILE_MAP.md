# Mapa de Archivos

## Criterio
Este mapa cubre los archivos y directorios relevantes del proyecto en su estado actual. No enumera `venv/`, `.git/` ni cachés generados.

## Raíz del repo

| Archivo | Rol | Estado / observación |
| --- | --- | --- |
| `.gitignore` | Exclusiones locales | Cubre cachés, `.env*`, logs y artefactos locales de pruebas |
| `.github/workflows/ci.yml` | CI remoto | Ejecuta `pytest`, regresión declarativa y smoke E2E en push/PR a `main` |
| `AGENTS.md` | Guía breve para futuros agentes | Contexto operativo rápido |
| `CONTRIBUTING.md` | Guía de contribución para colaboradores externos | Procedimiento para agregar bancos nuevos vía PR |
| `app.py` | Entrada principal Streamlit | Código productivo; soporta `local` y `production-test` |
| `excel_generator.py` | Generación de Excel | Código productivo |
| `format_cli.py` | CLI para train/validate/publish/regress | Código productivo |
| `format_engine.py` | Motor declarativo de specs | Código productivo |
| `format_training.py` | Helpers de entrenamiento, sanitización y publicación | Código productivo |
| `pdf_processor.py` | Orquestador de extracción, detección y validación | Código productivo |
| `pyproject.toml` | Metadatos y configuración de `pytest` | Vigente; identidad de paquete `bank-statement-parser` |
| `package.json` | Dependencias y scripts Node para Playwright | Vigente; expone `npm run test:e2e` |
| `package-lock.json` | Lockfile Node para Playwright | Vigente |
| `playwright.config.js` | Configuración del smoke E2E | Vigente; levanta Streamlit en `production-test` |
| `README.md` | Documentación pública base | Vigente |
| `requirements.txt` | Dependencias para instalación con `pip` | Vigente |
| `utils.py` | Helpers compartidos | Código productivo |

## Configuración de Streamlit

| Archivo | Rol | Estado / observación |
| --- | --- | --- |
| `.streamlit/config.toml` | Configuración de servidor Streamlit | Vigente |

## Registro declarativo `parser_specs/`

| Ruta | Rol | Estado / observación |
| --- | --- | --- |
| `parser_specs/galicia_ar/default/spec.toml` | Formato publicado de Galicia | Vigente |
| `parser_specs/chase/default/spec.toml` | Formato publicado de Chase | Vigente |
| `parser_specs/roela_ar/default/spec.toml` | Formato publicado de Roela | Vigente |
| `parser_specs/bbva/default/spec.toml` | Formato publicado de BBVA consolidado | Vigente |
| `parser_specs/bbva/account_summary/spec.toml` | Formato publicado de BBVA para resumen simple de cuenta | Vigente |
| `parser_specs/mercado_pago/default/spec.toml` | Formato publicado de Mercado Pago para resumen de cuenta wallet | Vigente |
| `parser_specs/brubank/default/spec.toml` | Formato publicado de Brubank para resumen de cuenta | Vigente |
| `parser_specs/bbva/default/fixtures/sample_text.txt` | Fixture sanitizada de BBVA consolidado | Vigente; cubre cuentas, tarjeta de crédito y tarjeta de débito sin depender del PDF real faltante |
| `parser_specs/brubank/default/fixtures/multi_account_sample_text.txt` | Fixture sanitizada de Brubank multi-cuenta | Vigente; cubre caja de ahorro ARS, cuenta remunerada ARS y cuenta USD sin movimientos |
| `parser_specs/*/*/fixtures/sample_text.txt` | Fixture sanitizada principal de texto | Vigente; base para regresión declarativa por formato |
| `parser_specs/*/*/fixtures/expected_transactions.json` | Salida esperada sanitizada | Vigente |

## Tests y diagnóstico

| Ruta | Rol | Estado / observación |
| --- | --- | --- |
| `tests/` | Fuente de verdad de la suite | Vigente |
| `tests/unit/` | Tests unitarios | Vigente; incluye endurecimiento de runtime, Excel, workflow de formatos y scripts diagnósticos |
| `tests/integration/` | Tests con PDFs reales disponibles y fixtures sanitizadas para flujos multi-entidad | Vigente |
| `tests/e2e/` | Smoke E2E con Playwright | Vigente; genera PDF sanitizado temporal y valida `production-test` |
| `tests/regression/` | Regresión de specs publicadas | Vigente |
| `scripts/run_app.py` | Helper para levantar la app en puerto fijo | Vigente; acepta `--mode` y `--debug` |
| `scripts/diagnostics/` | Scripts manuales de depuración | Vigente |

## Assets reales de validación

| Archivo | Rol | Estado / observación |
| --- | --- | --- |
| `attached_assets/BANCO CH 2024 1.pdf` | Muestra real de Chase | Se procesa con 12 transacciones |
| `attached_assets/BANCO CH 2024 2.pdf` | Segunda muestra real de Chase | Se procesa con 11 transacciones, incluyendo 29/02/2024 |
| `attached_assets/BancoRoela.Argentina.Test.pdf` | Muestra grande de Roela | Se procesa con 4913 transacciones |
| `attached_assets/BancoRoela.Argentina.Test.png` | Captura visual de Roela | Soporte visual |
| `attached_assets/TestBancoRoelaArg.txt` | Texto de muestra de Roela | Soporte manual útil |
| `attached_assets/TestGalicia.pdf` | Muestra real de Galicia | Se procesa con 52 transacciones |
| `attached_assets/TestGalicia.png` | Captura visual de Galicia | Soporte visual |
| `attached_assets/nuevo_formato/BBVA/01-2023 BBVA.pdf` | Muestra real histórica de BBVA consolidado | No disponible en este workspace; la cobertura CI actual usa `parser_specs/bbva/default/fixtures/sample_text.txt` |
| `attached_assets/nuevo_formato/BBVA/Resumen caja de ahorro BBVA 09-2023.pdf` | Muestra real de BBVA resumen simple | Se procesa con 1 scope y 12 transacciones |
| `attached_assets/nuevo_formato/Mercado Pago/Resumen de cuenta Mercado Pago 02-2023.pdf` | Muestra real de Mercado Pago | Se procesa con 1 scope y 232 transacciones |

## Artefactos locales no versionados

| Ruta | Rol | Estado / observación |
| --- | --- | --- |
| `logs/app.log` | Log rotado de runtime | Generado localmente, no versionado |
| `.coverage*`, `htmlcov/` | Cobertura local | Generado localmente, no versionado |
| `node_modules/` | Dependencias Node locales | Generado por `npm install`, no versionado |
| `playwright-report/`, `test-results/` | Reportes y artefactos Playwright | Generados por `npm run test:e2e`, no versionados |
