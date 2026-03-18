# Roadmap

## Estado del roadmap
Este documento es la foto operativa del plan. Debe actualizarse después de cada bloque grande de cambios.

## Objetivo de llegada
Convertir el proyecto en una herramienta confiable y extensible para transformar extractos bancarios PDF en movimientos normalizados, con:
- parsers versionados por formato,
- aprendizaje asistido para nuevos extractos,
- detección de cambios de estructura,
- validación automatizada local y e2e,
- persistencia de formatos dentro del repositorio.

## Hecho

### Fase 1: reparar y ordenar lo existente
- Roela ya no reabre `filename` cuando ya tiene texto y el archivo no existe.
- Galicia ya corta correctamente antes del footer legal.
- La extracción de `account` en inglés ya no toma direcciones como cuenta.
- `tests/` quedó como fuente de verdad.
- Los scripts de diagnóstico se movieron a `scripts/diagnostics/`.
- El runner oficial quedó alineado con `venv\Scripts\python.exe -m pytest -q`.
- Ya se retiraron del repo los residuos históricos más obvios: `test/` viejo, cachés fuera de `venv/` y el legacy Python de Argentina absorbido por specs.

### Fase 2: infraestructura de tests
- Hay suite `pytest` con unitarias, integración y regresión.
- Existen fixtures sanitizadas versionadas para specs publicadas.
- Existe runbook para smoke real con navegador en `docs/E2E_PLAYWRIGHT.md`.
- Existe helper para levantar Streamlit en puerto fijo: `scripts/run_app.py`.
- Se validó la app con Playwright MCP sobre el flujo real de carga y procesamiento.

### Fase 3: motor declarativo de formatos
- Existe `format_engine.py`.
- Las specs viven en `parser_specs/<bank_id>/<format_id>/spec.toml`.
- `PDFProcessor` ya quedó 100% declarativo: sin `parsers/` ni fallback Python en runtime.
- `process_pdf()` devuelve:
  - `parse_status`
  - `format_id`
  - `format_version`
  - `diagnostics`
- Ya existe fallo cerrado como `format_changed` para bancos con spec publicada que dejan de matchear.
- El core declarativo ya soporta:
  - regex por línea,
  - secciones múltiples,
  - fechas con año implícito,
  - fecha arrastrada por bloque,
  - thresholds de cobertura y cantidad mínima,
  - descubrimiento de scopes,
  - contexto dinámico por bloque,
  - filtrado por entidades seleccionadas.

### Fase 4: aprendizaje asistido y publicación
- Existe backoffice en Streamlit para aprender formatos.
- Existe CLI con:
  - `train`
  - `validate-draft`
  - `publish`
  - `regress`
- Los borradores y publicados quedan guardados dentro del repo en `parser_specs/`.
- No hay commits ni pushes automáticos.

### Fase 5: PDFs consolidados multi-entidad
- Existe una etapa de `Analizar Extractos` previa al parseo final cuando el documento tiene múltiples cuentas o tarjetas.
- La UI exige selección explícita por entidad concreta antes de procesar documentos consolidados.
- La salida conserva compatibilidad con el modelo actual y agrega metadatos opcionales por scope.
- Excel ahora mantiene `All Transactions` y agrega hojas por entidad cuando se procesan múltiples scopes.
- La CLI `validate-draft` ya reporta scopes descubiertos.

### Fase 6: endurecimiento para primeras pruebas en producción
- Existe un modo `production-test` para correr la app sin backoffice ni debug interactivo.
- Los errores inesperados quedan sanitizados en UI y registrados en `logs/app.log`.
- Los temporales PDF quedan centralizados y se limpian incluso ante excepciones.
- `process_pdf()` ya no duplica extracción, matching y preparación de texto.
- El fallback PDF secundario ya usa `pypdf`.
- El repo dejó de depender de artefactos históricos de Replit y del lockfile legacy de `uv`.

### Formatos ya migrados
- `galicia_ar/default`
- `chase/default`
- `roela_ar/default`
- `bbva/default`
- `bbva/account_summary`

## Pendiente

### Prioridad 1: completar la migración declarativa
- Elegir qué banco nuevo aporta más valor para la siguiente spec publicada.
- Mantener el runtime exclusivamente declarativo al sumar soporte nuevo.
- Reutilizar el patrón multi-entidad en nuevos formatos consolidados sin hardcode por banco.

### Prioridad 2: detección más fuerte de cambios de formato
- Agregar más fixtures alteradas por banco.
- Hacer que los diagnósticos de `format_changed` sean más explicativos para el backoffice.
- Añadir más casos donde el banco sea conocido pero la tabla cambie sin desaparecer por completo.

### Prioridad 3: ampliar cobertura real
- Priorizar bancos nuevos según impacto y disponibilidad de muestras.
- Añadir convenciones de naming y validación para specs nuevas.
- Definir criterio explícito de “banco soportado”.

### Prioridad 4: producto y mantenimiento
- Mantener el roadmap y el estado del proyecto sincronizados con cada bloque grande.
- Sostener la higiene del repo para no reintroducir legacy fuera del runtime declarativo.

## Hitos recomendados siguientes
1. Ejecutar la primera prueba controlada con `production-test`.
2. Agregar más fixtures alteradas por banco para endurecer `format_changed`.
3. Mejorar diagnósticos del backoffice para entrenamiento y publicación.
4. Elegir el siguiente banco a publicar con criterio de impacto y calidad.
