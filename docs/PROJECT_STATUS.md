# Estado Actual del Proyecto

## Estado general
El proyecto ya dejó de ser solo un prototipo con parsers sueltos. Hoy tiene:
- pipeline productivo funcionando en Streamlit,
- modo `production-test` para una salida controlada,
- motor declarativo versionado en `parser_specs/`,
- CLI para entrenar, validar, publicar y correr regresión,
- suite `pytest` estable,
- smoke real con navegador documentado,
- soporte multi-entidad para PDFs consolidados.

Sigue siendo, de todos modos, una base en consolidación y no un producto cerrado. El runtime productivo ya es declarativo, pero la cobertura real sigue dependiendo de publicar specs por banco y formato.

## Estado comprobado al 11 de abril de 2026
Validación local ejecutada con `venv\Scripts\python.exe`:
- `python -m pytest -q` -> `55 passed, 4 skipped`
- `python format_cli.py regress` -> `success: true` con `processed: 7`

Procesamiento manual comprobado con assets reales:
- `attached_assets/TestGalicia.pdf` -> `galicia_ar`, 52 transacciones, vía spec declarativa.
- `attached_assets/BancoRoela.Argentina.Test.pdf` -> `roela_ar`, 4913 transacciones, vía spec declarativa.
- `attached_assets/BANCO CH 2024 1.pdf` -> `chase`, 12 transacciones, vía spec declarativa.
- `attached_assets/BANCO CH 2024 2.pdf` -> `chase`, 10 transacciones, vía spec declarativa.
- `attached_assets/nuevo_formato/BBVA/01-2023 BBVA.pdf` -> `bbva`, documento consolidado con 5 scopes detectados y 192 transacciones.
- `attached_assets/nuevo_formato/BBVA/Resumen caja de ahorro BBVA 09-2023.pdf` -> `bbva`, resumen simple con 1 scope detectado y 12 transacciones.
- `attached_assets/nuevo_formato/Mercado Pago/Resumen de cuenta Mercado Pago 02-2023.pdf` -> `mercado_pago`, resumen wallet con 1 scope detectado y 232 transacciones.
- `Estado de cuenta Brubank [2026-01-01 al 2026-02-28]` -> `brubank`, 34 transacciones, vía spec declarativa publicada.
- `Estado de cuenta Brubank junio 2026 multi-cuenta (PDF externo no versionado)` -> `brubank`, documento multi-cuenta con 3 scopes detectados y 47 movimientos procesados al seleccionar todos los scopes; la cuenta en dólares queda detectada sin movimientos.

Nota operativa:
- En este workspace faltaba `attached_assets/nuevo_formato/BBVA/01-2023 BBVA.pdf`, por eso las integraciones que dependen de ese asset quedaron condicionadas y hoy aparecen como `skipped` cuando el archivo no está disponible.

## Lo que ya está resuelto

### Estabilización inicial
- Corregido el bug de Roela que reabría el PDF aunque ya hubiera texto preextraído.
- Corregido Galicia para no absorber footer legal en la última transacción.
- Endurecida la extracción de cuenta en formatos en inglés para no capturar direcciones.
- Reordenados tests y utilidades de diagnóstico.
- Corregida la generación de Excel multi-scope para labels con caracteres inválidos.
- Corregido el total agregado en UI/Excel para no mezclar monedas distintas ni caer en `EUR` por default.
- Garantizada la limpieza de PDFs temporales en análisis, procesamiento y backoffice.
- `process_pdf()` ya no reextrae texto ni rematchea la spec dentro de la misma ejecución.
- El fallback secundario de PDF pasó de `PyPDF2` a `pypdf`.
- El motor declarativo ya no deja `except/pass` silenciosos en la ruta específica de Roela.
- El runtime ahora escribe logs rotados en `logs/app.log`.
- La detección de banco ahora prioriza specs publicadas y señales del encabezado para evitar falsos positivos por menciones a otros bancos dentro de descripciones de transferencias.

### Infraestructura de tests
- `tests/` es la fuente de verdad.
- Hay tests unitarios, de integración y de regresión.
- Existen fixtures sanitizadas versionadas junto con las specs.
- Hay runbook y helper para smoke e2e con Streamlit + Playwright.

### Motor declarativo
- Existe `format_engine.py` con registro de specs TOML.
- `PDFProcessor` usa exclusivamente specs publicadas.
- `PDFProcessor` expone `analyze_pdf()` para descubrir scopes antes del parseo final.
- `PDFProcessor` también acepta override manual en `analyze_pdf()` y `process_pdf()` para forzar una spec publicada concreta.
- `PDFProcessor` expone `list_available_formats()` para listar dinámicamente los formatos publicados visibles en UI.
- `process_pdf()` ya devuelve `parse_status`, `format_id`, `format_version` y `diagnostics`.
- Hay detección cerrada de `format_changed` cuando un banco con specs publicadas deja de matchear.
- El core declarativo ya soporta preextracción específica desde PDF y reglas de signo basadas en códigos para formatos complejos como Roela.
- El core declarativo ya soporta también derivar `amount` desde columnas separadas de `debit`/`credit`, como en Brubank.
- El core declarativo ya soporta también reconstrucción tabular por bandas X para PDFs donde el texto sale partido alrededor de cada fila, como Mercado Pago.
- El core declarativo ya soporta documentos multi-entidad con descubrimiento de scopes y filtrado por selección explícita.
- Las actualizaciones parciales de scopes ya no pisan la moneda previamente detectada cuando una regla solo completa datos como el número de cuenta.
- El fallback Python legacy fue retirado del runtime.

### Selección manual de formato
- La UI muestra un selector por archivo con todos los formatos publicados.
- Cambiar el selector reanaliza el PDF con la spec elegida y actualiza dinámicamente los scopes disponibles.
- El flujo manual también cubre PDFs multi-entidad: si el formato forzado descubre múltiples scopes, la UI vuelve a exigir selección explícita antes de procesar.
- Los overrides inválidos o no publicados fallan como `unknown_format`; no se mezclan con `format_changed`.
- El override manual no siembra falsos positivos en el backoffice de entrenamiento cuando el usuario fuerza un formato incorrecto.

### Aprendizaje asistido
- Existe backoffice en Streamlit para aprender formatos.
- Existe CLI con `train`, `validate-draft`, `publish` y `regress`.
- Los borradores y formatos publicados quedan dentro del repo en `parser_specs/`.

### Migración declarativa ya hecha
- `galicia_ar/default` publicado y cubierto por regresión.
- `chase/default` publicado y cubierto por regresión.
- `roela_ar/default` publicado y cubierto por regresión.
- `bbva/default` publicado y cubierto por regresión/integración.
- `bbva/account_summary` publicado y cubierto por regresión/integración.
- `mercado_pago/default` publicado y cubierto por regresión/integración.
- `brubank/default` publicado y cubierto por regresión + validación manual con PDFs reales, incluyendo resumen multi-cuenta con caja de ahorro, cuenta remunerada y cuenta en dólares sin movimientos.

## Lo que todavía falta

### Prioridad alta
- Blindar mejor la detección de cambio de formato con más fixtures alteradas por banco.
- Ejecutar la primera prueba controlada en `production-test` con usuarios/datasets reales acotados.
- Mantener clara la diferencia entre banco detectado, banco soportado y documento consolidado.

### Prioridad media
- Seguir migrando bancos nuevos al sistema de specs.
- Mejorar la sanitización de fixtures para preservar estructura sin exponer datos sensibles.

### Prioridad estructural
- Sacar del repo restos históricos y artefactos que todavía no aportan al flujo actual.
- Mantener `docs/ROADMAP.md` sincronizado después de cada bloque grande de cambios.

## Riesgo técnico principal actual
El mayor riesgo principal sigue siendo la cobertura funcional: el runtime quedó más limpio y ya separa entidades dentro de PDFs consolidados, pero cualquier banco o formato nuevo exige publicar una spec antes de quedar soportado.

## Siguiente hito recomendado
El siguiente tramo lógico es:
1. correr la primera prueba controlada con `production-test`,
2. sumar más fixtures de `format_changed` por banco,
3. endurecer diagnósticos del backoffice para specs multi-entidad,
4. formalizar el criterio de “formato soportado” en UI y documentación.
