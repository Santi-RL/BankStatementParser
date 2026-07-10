# Estado Actual del Proyecto

## Estado general
El proyecto ya dejó de ser solo un prototipo con parsers sueltos. Hoy tiene:
- pipeline productivo funcionando en Streamlit,
- modo `production-test` para una salida controlada,
- motor declarativo versionado en `parser_specs/`,
- CLI para entrenar, validar, publicar y correr regresión,
- suite `pytest` estable,
- CI remoto de GitHub Actions para tests y regresión declarativa,
- smoke real con navegador documentado,
- soporte multi-entidad para PDFs consolidados.

Sigue siendo, de todos modos, una base en consolidación y no un producto cerrado. El runtime productivo ya es declarativo, pero la cobertura real sigue dependiendo de publicar specs por banco y formato. La aplicación está lista para pruebas controladas con datasets acotados; todavía no debe tratarse como lista para público general.

## Estado comprobado al 10 de julio de 2026
Validación local ejecutada con `venv\Scripts\python.exe`:
- `python -m pytest -q` -> `113 passed`
- `python format_cli.py regress` -> `success: true` con `processed: 7`
- CI remoto configurado en `.github/workflows/ci.yml` para push/PR a `main`, incluyendo tests Python, regresión declarativa y smoke E2E
- `npm run test:e2e` -> `1 passed`; smoke Playwright en `production-test` con PDF sanitizado generado desde fixture Galicia

Procesamiento manual comprobado con muestras reales locales:
- `local_samples/galicia_ar/TestGalicia.pdf` -> `galicia_ar`, 52 transacciones, vía spec declarativa.
- `local_samples/roela_ar/BancoRoela.Argentina.Test.pdf` -> `roela_ar`, 4913 transacciones, vía spec declarativa.
- `local_samples/chase/BANCO CH 2024 1.pdf` -> `chase`, 12 transacciones, vía spec declarativa.
- `local_samples/chase/BANCO CH 2024 2.pdf` -> `chase`, 11 transacciones, vía spec declarativa, incluyendo la operación del 29/02/2024.
- `local_samples/bbva/01-2023 BBVA.pdf` -> validación histórica de `bbva` consolidado con 5 scopes detectados y 192 transacciones; la muestra no está disponible hoy y la cobertura automatizada usa fixture sanitizada.
- `local_samples/bbva/Resumen caja de ahorro BBVA 09-2023.pdf` -> `bbva`, resumen simple con 1 scope detectado y 12 transacciones.
- `local_samples/mercado_pago/Resumen de cuenta Mercado Pago 02-2023.pdf` -> `mercado_pago`, resumen wallet con 1 scope detectado y 232 transacciones.
- `Estado de cuenta Brubank [2026-01-01 al 2026-02-28]` -> `brubank`, 34 transacciones, vía spec declarativa publicada.
- `local_samples/brubank/<extracto junio 2026>.pdf` -> `brubank`, documento multi-cuenta validado desde la nueva ruta local con 3 scopes y 47 movimientos al seleccionar todos; la cuenta en dólares queda detectada sin movimientos.

Nota operativa:
- La cobertura multi-entidad automatizada ya no depende del PDF real BBVA consolidado faltante. `tests/integration/test_bank_parsing.py` usa fixtures sanitizadas parametrizadas para BBVA consolidado y Brubank multi-cuenta.

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
- Corregido el parseo declarativo de fechas sin año para no depender del año implícito 1900 de `strptime`; esto elimina el warning previsto para Python 3.15 y recupera fechas bisiestas como 29/02/2024.
- El motor declarativo ya no deja `except/pass` silenciosos en la ruta específica de Roela.
- El runtime ahora escribe logs rotados en `logs/app.log`.
- La detección de banco ahora prioriza specs publicadas y señales del encabezado para evitar falsos positivos por menciones a otros bancos dentro de descripciones de transferencias.
- Las exportaciones Excel y CSV escapan textos no confiables que podrían convertirse en fórmulas, incluyendo nombres de archivo, descripciones, scopes y errores en Excel, y campos transaccionales en CSV.
- Las salidas visibles para usuario quedan en español: nombres de hojas, títulos, columnas y valores de tipo en Excel, CSV y vista previa de Streamlit, manteniendo claves técnicas internas en inglés.
- Las hojas de análisis mensual en Excel separan las agregaciones por moneda cuando hay movimientos de distintas monedas.
- La generación de Excel ya no asume que la columna `balance` existe para aplicar formatos monetarios.
- El workflow de entrenamiento valida `bank_id` y `format_id` como slugs seguros y verifica que los borradores queden bajo `parser_specs/`.
- Los scripts de diagnóstico devuelven código de salida no cero ante errores operativos y evitan caracteres problemáticos para consolas Windows.
- La metadata del paquete en `pyproject.toml` ya usa la identidad `bank-statement-parser`.

### Infraestructura de tests
- `tests/` es la fuente de verdad.
- Hay tests unitarios, de integración y de regresión.
- Existen fixtures sanitizadas versionadas junto con las specs.
- Hay runbook, configuración Playwright y smoke e2e automatizado con Streamlit + navegador real.
- Hay workflow de GitHub Actions que ejecuta `python -m pytest -q`, `python format_cli.py regress` y `npm run test:e2e`.
- Los tests de endurecimiento cubren la política anti-fórmulas compartida para Excel y CSV.
- Los tests de integración multi-entidad cubren BBVA consolidado y Brubank multi-cuenta con fixtures sanitizadas, selección explícita de scopes, filtrado por grupo/scope individual y generación de Excel.
- La extracción PDF tiene cobertura obligatoria con PDFs sanitizados generados de forma determinista, incluyendo las estrategias de columnas de Roela y bandas X de Mercado Pago.

### Motor declarativo
- Existe `format_engine.py` con registro de specs TOML.
- `PDFProcessor` usa exclusivamente specs publicadas.
- `PDFProcessor` expone `analyze_pdf()` para descubrir scopes antes del parseo final.
- `PDFProcessor` también acepta override manual en `analyze_pdf()` y `process_pdf()` para forzar una spec publicada concreta.
- `PDFProcessor` expone `list_available_formats()` para listar dinámicamente los formatos publicados visibles en UI.
- `process_pdf()` ya devuelve `parse_status`, `format_id`, `format_version` y `diagnostics`.
- Hay detección cerrada de `format_changed` cuando un banco con specs publicadas deja de matchear.
- La regresión de `format_changed` ya cubre cambios parciales de tabla por banco con fixtures sanitizadas: Galicia, Chase, Roela, BBVA account summary, Mercado Pago y Brubank.
- Las specs pueden activar `extract.reject_description_amount_tail` para rechazar filas donde una columna monetaria nueva fue absorbida como descripción.
- Los rechazos de esa guardia se exponen en `diagnostics.rejected_matches` y fuerzan `format_changed`, incluso si el resto del extracto todavía alcanza `min_transactions`.
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
- `brubank/default` publicado y cubierto por regresión, fixture sanitizada multi-cuenta y validación manual con PDFs reales, incluyendo caja de ahorro, cuenta remunerada y cuenta en dólares sin movimientos.

## Lo que todavía falta

### Prioridad 0: correcciones funcionales y de salida
- Sin pendientes abiertos en esta prioridad después de corregir el parseo de fechas sin año.

### Prioridad 1: robustez del parser y detección de cambios
- Mejorar los diagnósticos de `format_changed` para mostrar umbrales fallidos, cobertura, candidatos y secciones afectadas.
- Seguir ampliando fixtures parciales de `format_changed` cuando se publique o modifique una spec.
- Mantener clara en UI y diagnósticos la diferencia entre banco detectado, banco soportado, formato publicado y documento consolidado.

### Prioridad 2: cobertura funcional real
- Seguir migrando bancos nuevos al sistema de specs declarativas.
- Elegir el próximo banco o formato según impacto real, disponibilidad de muestras y posibilidad de fixtures sanitizadas.
- Reutilizar el patrón multi-entidad en nuevos formatos consolidados sin hardcode por banco.
- Al sumar un formato consolidado, seguir la metodología documentada en `CONTRIBUTING.md`: scopes declarativos, fixture sanitizada multi-cuenta y caso en `MULTI_SCOPE_FIXTURE_CASES`.

### Prioridad 3: backoffice y mantenimiento operativo
- Endurecer diagnósticos del backoffice para specs multi-entidad.
- Mostrar con más claridad por qué una spec no alcanza `min_transactions` o `min_match_ratio`.
- Mejorar la vista previa de scopes en `validate-draft` y en el backoffice.
- Mantener `docs/ROADMAP.md` y `docs/PROJECT_STATUS.md` sincronizados después de cada bloque grande.

### Prioridad 4: consistencia documental y de experiencia local
- Mantener alineada la documentación E2E si cambia el flujo `Analizar Extractos` -> `Procesar Extractos`.
- Mantener alineada la lista pública de bancos soportados entre `README.md`, specs publicadas y estado del proyecto.
- Decidir si la interfaz queda solo en español por ahora o si se completa realmente `--lang en`; hoy hay mezcla de `tr()` con textos hardcodeados.
- Sostener la higiene del repo para no reintroducir legacy fuera del runtime declarativo.

### Prioridad 5: preparación para exposición pública
Esta prioridad queda al final. No debe frenar las mejoras funcionales anteriores.

- Purgar del historial Git los PDFs reales previamente versionados y coordinar la actualización segura del remoto.
- Revisar fixtures existentes para eliminar nombres, direcciones, teléfonos, cuentas, CVU/CBU/CUIT/DNI u otros identificadores reales que todavía puedan quedar.
- Definir política de privacidad, manejo de datos bancarios, retención de logs y responsabilidades operativas.
- Definir despliegue, autenticación, límites de uso y monitoreo si se habilitan usuarios externos.

## Riesgo técnico principal actual
El riesgo principal sigue siendo la cobertura funcional por formato. Antes de compartir el proyecto públicamente, todavía deben revisarse las fixtures versionadas y definirse la política operativa de privacidad.

## Siguiente hito recomendado
El siguiente tramo lógico es:
1. mejorar diagnósticos de `format_changed` para explicar umbrales fallidos y secciones afectadas,
2. mejorar diagnósticos del backoffice para specs multi-entidad,
3. elegir el siguiente banco o formato a publicar,
4. seguir ampliando fixtures parciales cuando se agreguen formatos nuevos.
