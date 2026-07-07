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
- Existe smoke E2E automatizado con Playwright Test: genera un PDF sanitizado desde fixture, levanta `production-test` y valida `Analizar Extractos` -> `Procesar Extractos` -> descargas.
- Existe CI remoto en `.github/workflows/ci.yml` para correr `python -m pytest -q`, `python format_cli.py regress` y `npm run test:e2e` en push/PR a `main`.

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
- La regresión de `format_changed` ya incluye fixtures sanitizadas de cambios parciales de tabla por banco: Galicia, Chase, Roela, BBVA account summary, Mercado Pago y Brubank.
- El core declarativo ya soporta:
  - regex por línea,
  - secciones múltiples,
  - fechas con año implícito,
  - fecha arrastrada por bloque,
  - montos derivados desde columnas separadas de débito/crédito,
  - thresholds de cobertura y cantidad mínima,
  - descubrimiento de scopes,
  - contexto dinámico por bloque,
  - filtrado por entidades seleccionadas,
  - actualización parcial de scopes sin perder moneda ya detectada.

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
- Excel ahora mantiene `Movimientos` como hoja consolidada y agrega hojas por entidad cuando se procesan múltiples scopes.
- La CLI `validate-draft` ya reporta scopes descubiertos.
- La cobertura multi-entidad ya no depende del PDF real BBVA faltante: `tests/integration/test_bank_parsing.py` usa fixtures sanitizadas parametrizadas para BBVA consolidado y Brubank multi-cuenta.
- `CONTRIBUTING.md` documenta el patrón común para agregar bancos con resumen multi-cuenta: scopes declarativos, fixture sanitizada y caso en `MULTI_SCOPE_FIXTURE_CASES`.

### Fase 6: endurecimiento para primeras pruebas en producción
- Existe un modo `production-test` para correr la app sin backoffice ni debug interactivo.
- Los errores inesperados quedan sanitizados en UI y registrados en `logs/app.log`.
- La exportación Excel quedó endurecida contra inyección de fórmulas en textos no confiables.
- La exportación CSV quedó endurecida contra inyección de fórmulas usando la misma política compartida que Excel.
- Hay tests unitarios que validan Excel y CSV con textos iniciados en `=`, `+`, `-`, `@`, tabulaciones y saltos de línea.
- Los resúmenes mensuales de Excel separan totales por moneda cuando hay movimientos multi-moneda.
- El formato monetario de Excel se aplica por encabezado y ya no depende de que `Saldo` exista físicamente como columna D.
- Las salidas visibles para usuario quedan en español: hojas, títulos, columnas, tipos de movimiento/producto, CSV, vista previa y nombres de descarga.
- El entrenamiento de specs valida slugs y contención bajo `parser_specs/` antes de escribir borradores.
- Los scripts diagnósticos devuelven estados de salida útiles para mantenimiento y CI.
- La metadata de paquete dejó de usar la identidad de template de Replit.
- Los temporales PDF quedan centralizados y se limpian incluso ante excepciones.
- `process_pdf()` ya no duplica extracción, matching y preparación de texto.
- El fallback PDF secundario ya usa `pypdf`.
- El parseo de fechas sin año ya no depende del año implícito 1900 de `strptime`; inyecta un año explícito, conserva la inferencia del resumen y permite fechas bisiestas como 29/02/2024.
- El repo dejó de depender de artefactos históricos de Replit y del lockfile legacy de `uv`.
- La detección de banco ahora prioriza el match de specs publicadas y señales estructurales antes que menciones sueltas dentro del detalle de movimientos.

### Fase 7: selección manual y dinámica de formato
- La UI muestra un selector por archivo con todos los formatos publicados disponibles en el runtime declarativo.
- Cambiar el selector reanaliza ese PDF con la spec elegida antes del procesamiento final.
- El flujo manual también actualiza dinámicamente los scopes disponibles, por lo que sigue siendo compatible con PDFs multi-entidad.
- `PDFProcessor.analyze_pdf()` y `PDFProcessor.process_pdf()` aceptan override manual, pero solo resuelven specs publicadas.
- Los overrides inválidos se reportan como `unknown_format`, evitando mezclar un error de selección manual con un `format_changed` real.
- Hay tests unitarios para listar formatos, analizar multi-scope con override, procesar con override y rechazar overrides inválidos.

### Formatos ya migrados
- `galicia_ar/default`
- `chase/default`
- `roela_ar/default`
- `bbva/default`
- `bbva/account_summary`
- `mercado_pago/default`
- `brubank/default` v2, con soporte para resumen multi-cuenta cubierto por fixture sanitizada: caja de ahorro, cuenta remunerada y cuenta en dólares sin movimientos

## Pendiente

### Prioridad 0: correcciones funcionales y de salida
Estas tareas van primero porque afectan la confiabilidad del resultado entregado al usuario, incluso en una prueba controlada.

- Sin pendientes funcionales abiertos en esta prioridad después de corregir el parseo de fechas sin año.

### Prioridad 1: robustez del parser y detección de cambios
Estas tareas fortalecen el motor existente antes de sumar más superficie.

- Hacer que los diagnósticos de `format_changed` expliquen mejor qué umbral falló: keywords, cantidad de candidatos, cobertura, transacciones encontradas y secciones afectadas.
- Seguir agregando fixtures parciales de `format_changed` cada vez que se publique o modifique una spec.
- Mantener clara en UI y diagnósticos la diferencia entre banco detectado, banco soportado, formato publicado y documento consolidado.
- Validar que el override manual de formato no oculte errores reales de cambio de formato cuando el usuario fuerza una spec incorrecta.

### Prioridad 2: ampliar cobertura funcional real
Estas tareas agregan valor de producto sin cambiar el principio de runtime declarativo.

- Elegir qué banco o formato nuevo aporta más valor para la siguiente spec publicada.
- Mantener el runtime exclusivamente declarativo al sumar soporte nuevo.
- Reutilizar el patrón multi-entidad en nuevos formatos consolidados sin hardcode por banco.
- Priorizar bancos nuevos según impacto, disponibilidad de muestras y posibilidad de crear fixtures sanitizadas confiables.

### Prioridad 3: backoffice y flujo de entrenamiento
Estas tareas hacen más práctico mantener y ampliar la aplicación.

- Endurecer diagnósticos del backoffice para specs multi-entidad.
- Mostrar en el backoffice el motivo concreto por el que una spec no alcanza `min_transactions` o `min_match_ratio`.
- Mejorar la vista previa de scopes descubiertos durante `validate-draft` y en el backoffice.
- Hacer más visible cuándo una fixture quedó sanitizada pero perdió estructura útil para regresión.
- Mantener `CONTRIBUTING.md` como guía oficial para specs nuevas. Convenciones de naming, criterio de banco soportado y flujo de PR ya están resueltos allí.

### Prioridad 4: consistencia de producto local
Estas tareas no bloquean el parser, pero reducen confusión durante uso interno o pruebas controladas.

- Mantener `README.md`, `docs/E2E_PLAYWRIGHT.md`, `docs/PRODUCTION_TEST_RUNBOOK.md` y la UI alineados con el flujo actual.
- Mantener alineada la lista pública de bancos soportados entre README, specs publicadas y estado del proyecto.
- Decidir si la app será solo español por ahora o si `--lang en` debe quedar realmente completo; hoy la UI mezcla `tr()` con textos hardcodeados en español.
- Mantener el roadmap y el estado del proyecto sincronizados después de cada bloque grande.
- Sostener la higiene del repo para no reintroducir legacy fuera del runtime declarativo.

### Prioridad 5: preparación para exposición pública
Esta prioridad queda deliberadamente después de las mejoras funcionales. No debe bloquear el trabajo de parser, cobertura y salida.

- Retirar PDFs reales versionados o reemplazarlos por muestras sintéticas/sanitizadas.
- Revisar fixtures existentes para eliminar nombres, direcciones, teléfonos, cuentas, CVU/CBU/CUIT/DNI u otros identificadores reales que todavía puedan quedar.
- Definir política de privacidad y manejo de datos bancarios.
- Definir despliegue, autenticación, límites de uso, monitoreo y retención de logs si se habilitan usuarios externos.
- Preparar documentación pública final cuando la cobertura funcional y los flujos principales estén cerrados.

## Hitos recomendados siguientes
1. Mejorar diagnósticos de `format_changed` para explicar umbrales fallidos y secciones afectadas.
2. Mejorar diagnósticos del backoffice para entrenamiento y publicación.
3. Elegir el siguiente banco o formato a publicar con criterio de impacto y calidad.
4. Seguir ampliando fixtures parciales cuando se agreguen formatos nuevos.
