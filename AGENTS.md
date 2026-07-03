# AGENTS.md

## Instrucciones compartidas
- Este proyecto vive bajo `C:\Users\SANTI\Documents\Proyectos`.
- Para instrucciones generales compartidas, revisar también `C:\Users\SANTI\Documents\Proyectos\AGENTS.md`.
- En caso de conflicto, este `AGENTS.md` local prevalece para reglas específicas de BankStatementParser.

## Lectura recomendada
1. `docs/PROJECT_CONTEXT.md`
2. `docs/PROJECT_STATUS.md`
3. `docs/ROADMAP.md`
4. `docs/FILE_MAP.md`

## Objetivo del producto
Este repositorio busca convertir extractos bancarios en PDF a un formato tabular normalizado y descargable, hoy vía Streamlit y con salida Excel/CSV.

## Fuente de verdad
- El código productivo vive en la raíz del repo y en `parser_specs/`.
- Los scripts de diagnóstico vigentes viven en `scripts/diagnostics/`.
- `attached_assets/` contiene PDFs y capturas usados como muestras reales para validar formatos.

## Flujo principal
1. `app.py` recibe PDFs desde Streamlit.
2. `utils.validate_pdf_files` valida extensión y tamaño.
3. `pdf_processor.PDFProcessor` extrae texto, detecta banco, busca una spec publicada y normaliza transacciones.
4. `excel_generator.ExcelGenerator` genera el `.xlsx`.
5. La app permite descargar Excel o CSV.

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

## Entorno local
- El repo depende de `venv\Scripts\python.exe`; no asumir que `uv` o `pytest` están en el `PATH`.
- Ejecución UI: `venv\Scripts\streamlit.exe run app.py`
- Tests: `venv\Scripts\python.exe -m pytest -q`

## Flujo Git del proyecto
- La rama de trabajo normal es `main`.
- No crear ramas nuevas para tareas habituales; hacer commits directamente en `main` y luego `git push origin main`.
- Crear ramas de trabajo, PRs o ramas `codex/*` solo si el usuario lo pide explícitamente o si se acuerda antes por una razón técnica concreta.
- Antes de hacer push a `main`, verificar que el árbol esté limpio, que los tests relevantes pasen y que no queden ramas temporales locales o remotas que puedan confundir.

## Riesgos conocidos
- La detección de banco sigue siendo heurística.
- Los bancos sin spec publicada deben fallar como `unknown_format`.
- La calidad del producto depende de mantener fixtures sanitizadas y regresión por formato.

## Reglas prácticas para futuros cambios
- Mantener el runtime 100% declarativo; no reintroducir parsers Python como fallback.
- Preservar la forma normalizada de las transacciones; cambiar claves rompe app, validación y Excel.
- Si se toca una spec o el motor declarativo, validar al menos con un PDF real de `attached_assets/`.
- Después de cada bloque grande de cambios, actualizar `docs/ROADMAP.md` y, si cambió el estado general del proyecto, también `docs/PROJECT_STATUS.md`.

## Revisión de código y seguridad
- Usar `security-best-practices` si se cambian validaciones de PDFs, rutas de archivos, parsing de entradas externas, exportaciones, manejo de datos bancarios o Streamlit.
- Usar `autoreview` como cierre de cambios no triviales en parser, specs, app o exportadores: ejecutar `venv\Scripts\python.exe -m pytest -q` y validar con una muestra real cuando aplique; verificar manualmente cada finding.
- Usar la CLI global `clawpatch` (`C:\Users\SANTI\AppData\Roaming\npm\clawpatch.cmd`) solo para auditorías/backlog de mantenimiento del repo o por pedido explícito. Para la política compartida de comandos, revisar `C:\Users\SANTI\Documents\Proyectos\AGENTS.md`. Empezar por `clawpatch status`, `clawpatch map`, `clawpatch review --limit <n>` y `clawpatch report`; `clawpatch fix --finding <id>` requiere worktree limpio y confirmación explícita.
- No usar estas herramientas para simples pruebas manuales con PDFs o actualizaciones documentales menores.
