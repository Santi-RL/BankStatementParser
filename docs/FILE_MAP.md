# Mapa de Archivos

## Criterio
Este mapa cubre los archivos y directorios relevantes del proyecto en su estado actual. No enumera `venv/`, `.git/` ni cachés generados.

## Raíz del repo

| Archivo | Rol | Estado / observación |
| --- | --- | --- |
| `.gitignore` | Exclusiones locales | Cubre cachés, `.env*`, logs y artefactos locales de pruebas |
| `AGENTS.md` | Guía breve para futuros agentes | Contexto operativo rápido |
| `app.py` | Entrada principal Streamlit | Código productivo; soporta `local` y `production-test` |
| `excel_generator.py` | Generación de Excel | Código productivo |
| `format_cli.py` | CLI para train/validate/publish/regress | Código productivo |
| `format_engine.py` | Motor declarativo de specs | Código productivo |
| `format_training.py` | Helpers de entrenamiento, sanitización y publicación | Código productivo |
| `pdf_processor.py` | Orquestador de extracción, detección y validación | Código productivo |
| `pyproject.toml` | Metadatos y configuración de `pytest` | Vigente |
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
| `parser_specs/*/*/fixtures/sample_text.txt` | Fixture sanitizada de texto | Vigente |
| `parser_specs/*/*/fixtures/expected_transactions.json` | Salida esperada sanitizada | Vigente |

## Tests y diagnóstico

| Ruta | Rol | Estado / observación |
| --- | --- | --- |
| `tests/` | Fuente de verdad de la suite | Vigente |
| `tests/unit/` | Tests unitarios | Vigente |
| `tests/integration/` | Tests con PDFs y flujos reales | Vigente |
| `tests/regression/` | Regresión de specs publicadas | Vigente |
| `scripts/run_app.py` | Helper para levantar la app en puerto fijo | Vigente; acepta `--mode` y `--debug` |
| `scripts/diagnostics/` | Scripts manuales de depuración | Vigente |

## Assets reales de validación

| Archivo | Rol | Estado / observación |
| --- | --- | --- |
| `attached_assets/BANCO CH 2024 1.pdf` | Muestra real de Chase | Se procesa con 12 transacciones |
| `attached_assets/BANCO CH 2024 2.pdf` | Segunda muestra real de Chase | Se procesa con 10 transacciones |
| `attached_assets/BancoRoela.Argentina.Test.pdf` | Muestra grande de Roela | Se procesa con 4913 transacciones |
| `attached_assets/BancoRoela.Argentina.Test.png` | Captura visual de Roela | Soporte visual |
| `attached_assets/TestBancoRoelaArg.txt` | Texto de muestra de Roela | Soporte manual útil |
| `attached_assets/TestGalicia.pdf` | Muestra real de Galicia | Se procesa con 52 transacciones |
| `attached_assets/TestGalicia.png` | Captura visual de Galicia | Soporte visual |
| `attached_assets/nuevo_formato/BBVA/01-2023 BBVA.pdf` | Muestra real de BBVA consolidado | Se procesa con 5 scopes y 192 transacciones |

## Artefactos locales no versionados

| Ruta | Rol | Estado / observación |
| --- | --- | --- |
| `logs/app.log` | Log rotado de runtime | Generado localmente, no versionado |
| `.coverage*`, `htmlcov/` | Cobertura local | Generado localmente, no versionado |
