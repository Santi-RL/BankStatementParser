# AGENTS.md

## Instrucciones compartidas
- La raíz de este repo es `C:\Users\SANTI\Documents\Proyectos\BankStatementParser`.
- Este proyecto vive bajo `C:\Users\SANTI\Documents\Proyectos`.
- Para instrucciones generales compartidas, revisar también `C:\Users\SANTI\Documents\Proyectos\AGENTS.md`.
- En caso de conflicto, este `AGENTS.md` local prevalece para reglas específicas de BankStatementParser.

## Lectura recomendada
1. `docs/PROJECT_CONTEXT.md`
2. `docs/PROJECT_STATUS.md`
3. `docs/ROADMAP.md`
4. `docs/FILE_MAP.md`
5. `README.md`
6. `CONTRIBUTING.md` si se trabaja sobre specs o bancos nuevos.

## Objetivo del producto
Este repositorio convierte extractos bancarios en PDF a un formato tabular normalizado y descargable, hoy vía Streamlit y con salida Excel/CSV.

La arquitectura buscada es un runtime declarativo y extensible: cada banco/formato soportado debe vivir como spec TOML publicada en `parser_specs/`, no como parser Python ad hoc. La app está lista para pruebas controladas con datasets acotados, pero no debe tratarse como lista para público general sin resolver los pendientes del roadmap.

## Fuente de verdad
- El código productivo vive en la raíz del repo: `app.py`, `pdf_processor.py`, `format_engine.py`, `excel_generator.py`, `format_training.py`, `format_cli.py` y `utils.py`.
- Las specs productivas viven en `parser_specs/<bank_id>/<format_id>/spec.toml` con fixtures en `fixtures/`.
- Los tests vigentes viven en `tests/` y se dividen en unitarios, integración y regresión.
- Los scripts de diagnóstico vigentes viven en `scripts/diagnostics/`.
- `scripts/run_app.py` es el runner local oficial para Streamlit.
- `attached_assets/` contiene PDFs y capturas usados como muestras reales para validar formatos; tratarlos como datos sensibles.

## Flujo principal actual
1. `app.py` recibe PDFs desde Streamlit.
2. `utils.validate_pdf_files` valida extensión, cantidad y tamaño.
3. La app guarda cada PDF en un temporal con `utils.temporary_pdf_copy`.
4. `PDFProcessor.analyze_pdf()` extrae texto, detecta banco, resuelve una spec publicada y descubre scopes cuando el documento tiene múltiples cuentas o tarjetas.
5. La UI permite selección explícita de scopes y override manual hacia formatos publicados.
6. `PDFProcessor.process_pdf()` parsea y normaliza transacciones con la spec declarativa seleccionada.
7. `excel_generator.ExcelGenerator` genera el `.xlsx`.
8. La app permite descargar Excel o CSV.

## Modelo de datos esperado
Cada transacción debería salir, como mínimo, con:
- `date`
- `description`
- `amount`

Campos esperables cuando el formato puede resolverlos:
- `balance`
- `bank`
- `account`
- `currency`
- `transaction_type`

Metadatos opcionales usados en documentos multi-entidad o salida consolidada:
- `scope_id`
- `scope_label`
- `product_type`
- `linked_account`
- `source_file`

Estados y diagnósticos importantes del parser:
- `parse_status = "ok"` indica parseo exitoso.
- `parse_status = "unknown_format"` indica banco/formato no soportado por spec publicada.
- `parse_status = "format_changed"` indica banco conocido con estructura que no cumple la spec publicada.
- `diagnostics`, `format_id` y `format_version` son parte del contrato operativo y no deben eliminarse sin actualizar UI, tests y docs.

## Entorno local
- El repo depende de `venv\Scripts\python.exe`; no asumir que `uv`, `python`, `streamlit` o `pytest` están en el `PATH`.
- Ejecución UI local: `venv\Scripts\python.exe scripts/run_app.py --mode local`.
- Primera prueba controlada: `venv\Scripts\python.exe scripts/run_app.py --mode production-test`.
- Ejecución directa alternativa: `venv\Scripts\streamlit.exe run app.py -- --mode local`.
- Tests: `venv\Scripts\python.exe -m pytest -q`.
- Regresión de specs publicadas: `venv\Scripts\python.exe format_cli.py regress`.

## Tests y CI
- El CI remoto vive en `.github/workflows/ci.yml` y corre en push/PR contra `main`.
- El CI instala `requirements.txt`, ejecuta `python -m pytest -q` y luego `python format_cli.py regress`.
- Toda implementación nueva que cambie comportamiento, contratos, parsing, specs, UI, exportaciones o seguridad debe agregar o actualizar tests proporcionales al riesgo.
- Para cambios de specs, cubrir la regresión con fixtures sanitizadas y validar `format_cli.py regress`.
- Para cambios de motor, `PDFProcessor`, exportadores o utilidades compartidas, agregar tests unitarios o de integración que fallen sin el cambio.
- Para correcciones puramente documentales puede omitirse agregar tests, pero conviene dejarlo explícito en el cierre.

## Flujo Git del proyecto
- La rama de trabajo normal es `main`.
- No crear ramas nuevas para tareas habituales; crear ramas de trabajo, PRs o ramas `codex/*` solo si el usuario lo pide explícitamente o si se acuerda antes por una razón técnica concreta.
- Hacer commits directamente en `main` y luego `git push origin main` solo cuando el usuario lo pida o confirme explícitamente.
- Antes de hacer commit o push, verificar que el árbol esté limpio salvo los cambios esperados, que los tests relevantes pasen y que no queden ramas temporales locales o remotas que puedan confundir.

## Riesgos conocidos
- La detección de banco sigue siendo heurística.
- Los bancos sin spec publicada deben fallar como `unknown_format`.
- Un banco conocido cuya estructura cambió debe fallar como `format_changed`, no producir datos silenciosamente incorrectos.
- La calidad del producto depende de mantener fixtures sanitizadas y regresión por formato.
- La descarga Excel ya tiene defensa contra inyección de fórmulas; revisar `docs/ROADMAP.md` para el estado de la misma protección en CSV.
- Hay PDFs reales y fixtures históricas que requieren cuidado de privacidad antes de exponer el repo o la app al público.

## Reglas prácticas para futuros cambios
- Mantener el runtime 100% declarativo; no reintroducir parsers Python como fallback.
- Preservar la forma normalizada de las transacciones; cambiar claves rompe app, validación, Excel y CSV.
- Si se toca una spec o el motor declarativo, validar con fixtures y, cuando aplique, con una muestra real de `attached_assets/`.
- No agregar PDFs reales nuevos al repo salvo pedido explícito. Preferir fixtures sanitizadas y revisar datos personales antes de versionar.
- Si se toca UI, parsing, exportaciones o seguridad de archivos, revisar si corresponde actualizar `docs/ROADMAP.md`, `docs/PROJECT_STATUS.md`, `docs/FILE_MAP.md`, `README.md` o `CONTRIBUTING.md`.
- Después de cada bloque grande de cambios, actualizar `docs/ROADMAP.md` y, si cambió el estado general del proyecto, también `docs/PROJECT_STATUS.md`.
- Priorizar funcionalidad y confiabilidad del parser antes que preparación para exposición pública, según el orden vigente en `docs/ROADMAP.md`.

## Revisión de código y seguridad
- Usar `security-best-practices` si se cambian validaciones de PDFs, rutas de archivos, parsing de entradas externas, exportaciones, manejo de datos bancarios, Streamlit o cualquier flujo que pueda exponer datos sensibles.
- No ejecutar `autoreview` automáticamente. El usuario puede pedirlo en cualquier momento, pero si no lo pidió hay que sugerirlo cuando el cambio sea importante y pedir confirmación explícita antes de correrlo, porque puede consumir tiempo, tokens y enviar el diff local al motor de revisión.
- Recomendar `autoreview` especialmente cuando el cambio toque `PDFProcessor`, `format_engine.py`, specs publicadas, selección de scopes, detección de banco, `format_changed`, validaciones de PDFs, temporales, exportación Excel/CSV, sanitización, Streamlit, manejo de datos bancarios o cualquier flujo donde un error pueda producir datos incorrectos, exponer información sensible o romper descargas.
- No insistir con `autoreview` para cambios chicos, aislados y de bajo riesgo, como correcciones de texto, documentación simple, ajustes menores de wording o pruebas manuales con PDFs que no cambian código. En esos casos alcanzan las validaciones normales del área tocada, salvo que el usuario lo pida.
- Elegir el momento de la sugerencia según costo y precisión:
  - Para cambios pequeños pero sensibles, proponer `autoreview` inmediatamente después de implementar y antes de seguir acumulando trabajo, para que la revisión sea rápida, concreta y accionable.
  - Para varios cambios relacionados dentro de una misma unidad lógica, terminar el lote coherente, ejecutar pruebas/formato relevantes y luego proponer un único `autoreview` sobre todo el diff.
  - Si el diff empieza a mezclar temas independientes, sugerir cortar en commits o revisiones separadas para optimizar tiempo, tokens y calidad de hallazgos.
  - Antes de commit, push o PR de cambios no triviales, recordar la opción de `autoreview` si todavía no se ejecutó en ese ciclo.
- Antes de correr `autoreview`, ejecutar las pruebas relevantes siempre que sea razonable. Para este repo, el cierre normal es `venv\Scripts\python.exe -m pytest -q`; si se tocaron specs o el motor declarativo, agregar `venv\Scripts\python.exe format_cli.py regress`; si aplica a un formato concreto, validar con fixture y/o muestra real controlada.
- Después de `autoreview`, revisar el diff real y verificar manualmente cada finding. Clasificar cada hallazgo como aceptado, rechazado o diferido. Corregir solo findings que representen un riesgo real, regresión, contrato roto, caso no cubierto o mejora necesaria dentro del alcance.
- Rechazar hallazgos especulativos, cambios sobredimensionados o refactors que no reduzcan un riesgo concreto. Si se aceptan fixes que cambian código, repetir las pruebas enfocadas y volver a correr `autoreview` hasta que no queden hallazgos aceptados/accionables o hasta que el usuario decida detener el ciclo.
- Autorización del usuario para este proyecto: cuando el usuario pida o confirme ejecutar `autoreview`, queda permitido usar el motor Codex/OpenAI, enviarle el diff local necesario para la revisión y mantener habilitada la búsqueda web del helper. Esta autorización no habilita ejecutar `autoreview` sin pedido o confirmación explícita.
- En Windows, si `autoreview` falla con `PermissionError: [WinError 5] Acceso denegado` al invocar `codex`, no usar el shim `codex` del PATH ni el binario de `WindowsApps`. Ejecutar el helper apuntando al binario local de la app:
  `python C:\Users\SANTI\.codex\skills\autoreview\scripts\autoreview --mode local --codex-bin "C:\Users\SANTI\AppData\Local\OpenAI\Codex\bin\codex.exe"`.
- Usar la CLI global `clawpatch` (`C:\Users\SANTI\AppData\Roaming\npm\clawpatch.cmd`) solo para auditorías/backlog de mantenimiento del repo o por pedido explícito.
- Para `clawpatch`, respetar la política compartida en `C:\Users\SANTI\Documents\Proyectos\AGENTS.md`: empezar por `clawpatch doctor`, inicializar estado con `clawpatch init` si hace falta, luego `clawpatch map`, `clawpatch review --limit <n>` y `clawpatch report`.
- No ejecutar `clawpatch fix`, commits, pushes, merges ni acciones destructivas salvo pedido explícito y worktree limpio.
- No usar estas herramientas para simples pruebas manuales con PDFs o actualizaciones documentales menores.
