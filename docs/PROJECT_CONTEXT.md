# Contexto del Proyecto

## Resumen
`BankStatementParser` es una aplicación de escritorio/web ligera, hecha con Streamlit, para subir extractos bancarios en PDF, detectar automáticamente el banco y convertir los movimientos a un Excel o CSV normalizado.

La idea central no es solo “leer PDFs”, sino crear una capa de normalización reusable para distintos bancos y formatos de extracto.

## Qué hace hoy
- Acepta múltiples PDFs por carga.
- Rechaza archivos no PDF y archivos grandes.
- Extrae texto con `pdfplumber`, usa `pypdf` como fallback y tiene un tercer fallback muy básico sobre el binario bruto.
- Detecta banco por heurísticas de texto.
- Usa únicamente formatos declarativos publicados en `parser_specs/`.
- Ejecuta un preanálisis cuando detecta documentos con múltiples cuentas o tarjetas extraíbles.
- Genera un `.xlsx` con hojas de resumen, movimientos y análisis.
- Permite descargar también un CSV.
- Incluye un backoffice dentro de Streamlit para entrenar y publicar nuevos formatos declarativos.
- Incluye un modo `production-test` que oculta el backoffice y sanea la salida operativa para pruebas controladas.
- Expone una CLI para `train`, `validate-draft`, `publish` y `regress`.

## Flujo técnico
```text
Streamlit UI
  -> validate_pdf_files
  -> PDFProcessor._extract_text_from_pdf
  -> PDFProcessor._detect_bank
  -> FormatRegistry.match_published
  -> PDFProcessor.analyze_pdf
  -> selección explícita de scopes si el documento es consolidado
  -> spec.parse_transactions
  -> PDFProcessor._validate_transactions
  -> conciliación opcional y no bloqueante cuando la spec la soporta
  -> ExcelGenerator.create_excel_file
  -> descarga Excel / CSV
```

## Componentes principales

### `app.py`
Es la interfaz Streamlit. Gestiona sesión, subida de archivos, preanálisis, selección de scopes, progreso, errores, preview y descargas. También implementa una capa mínima de internacionalización `en/es`.

### `pdf_processor.py`
Es el orquestador real del dominio. Se encarga de:
- extraer texto del PDF,
- detectar el banco,
- resolver la spec publicada correcta,
- exponer `analyze_pdf(...)` para descubrir entidades extraíbles antes del parseo final,
- validar y completar transacciones.

### `parser_specs/`
Contiene el registro declarativo versionado por banco/formato. Cada formato tiene su `spec.toml` y sus fixtures sanitizadas. Hoy Galicia, Chase, Roela, BBVA, Mercado Pago y Brubank ya están migrados a este modelo, incluyendo dos variantes publicadas de BBVA.

### `excel_generator.py`
Arma el Excel final. Hoy crea cinco hojas base:
- `Resumen`
- `Conciliación`
- `Movimientos`
- `Análisis`
- `Resumen Mensual`

La hoja `Conciliación` informa por extracto, scope, moneda y período si el saldo inicial más el neto de movimientos coincide con el saldo final. Es un control auxiliar: una diferencia o la ausencia de saldos no bloquea el procesamiento ni la exportación.

Cuando se seleccionan múltiples entidades, agrega también una hoja por cuenta o tarjeta extraída. Las hojas, títulos, columnas y valores visibles de exportación se muestran en español; las claves internas del modelo siguen en inglés.

### `utils.py`
Centraliza helpers reutilizados por varios módulos: limpieza de texto, parseo de montos, parseo de fechas, validación de PDFs, logging y listado de bancos soportados.

## Bancos con soporte real actual
- `galicia_ar/default`
- `chase/default`
- `roela_ar/default`
- `bbva/default`
- `bbva/account_summary`
- `mercado_pago/default`
- `brubank/default`

## Esquema de transacción que consume todo el sistema
La UI, la validación y el generador de Excel asumen que cada movimiento sale como diccionario con estas claves base:

```python
{
    "date": "YYYY-MM-DD",
    "description": "texto normalizado",
    "amount": float,
    "balance": float | "",
    "account": str,
    "bank": str,
    "currency": str,
    "transaction_type": "Credit" | "Debit" | "Neutral",
}
```

En documentos multi-entidad puede agregar metadatos opcionales sin romper compatibilidad:
- `scope_id`
- `scope_label`
- `product_type`
- `linked_account`
- `source_file`

## Validación manual realizada sobre muestras reales locales
Los PDFs reales viven exclusivamente en `local_samples/<bank_id>/`, ignorado por Git.

Se procesaron localmente estos archivos con `venv\Scripts\python.exe`:

| Archivo | Banco detectado | Resultado observado |
| --- | --- | --- |
| `local_samples/galicia_ar/TestGalicia.pdf` | `galicia_ar` | 52 transacciones |
| `local_samples/roela_ar/BancoRoela.Argentina.Test.pdf` | `roela_ar` | 4913 transacciones |
| `local_samples/chase/BANCO CH 2024 1.pdf` | `chase` | 12 transacciones |
| `local_samples/chase/BANCO CH 2024 2.pdf` | `chase` | 11 transacciones, incluyendo 29/02/2024 |
| `local_samples/bbva/01-2023 BBVA.pdf` | `bbva` | Validación histórica de documento consolidado con 5 scopes y 192 transacciones; la muestra no está disponible hoy y la cobertura CI usa `parser_specs/bbva/default/fixtures/sample_text.txt` |
| `local_samples/bbva/Resumen caja de ahorro BBVA 09-2023.pdf` | `bbva` | Resumen simple de cuenta, 1 scope detectado y 12 transacciones |
| `local_samples/mercado_pago/Resumen de cuenta Mercado Pago 02-2023.pdf` | `mercado_pago` | Resumen de cuenta wallet, 1 scope detectado y 232 transacciones |
| `Brubank ene-feb 2026 (PDF externo no versionado)` | `brubank` | Resumen de cuenta con 34 transacciones, vía spec declarativa |
| `local_samples/brubank/<extracto junio 2026>.pdf` | `brubank` | Muestra multi-cuenta local validada con 3 scopes y 47 movimientos al seleccionar todos |

Eso confirma que el pipeline base funciona hoy y no es solo un prototipo estático.

## Tests y regresión
- `pytest` ya corre sobre `tests/` como fuente de verdad.
- Hay regresión offline para los formatos declarativos publicados.
- Existe un helper `scripts/run_app.py`, configuración Playwright, runbook en `docs/E2E_PLAYWRIGHT.md` y job de CI para smoke real automatizado con navegador.
- Existe un runbook específico de primera salida en `docs/PRODUCTION_TEST_RUNBOOK.md`.
- La suite actual valida formatos declarativos publicados para Galicia, Chase, Roela, BBVA, Mercado Pago y Brubank.
- La cobertura multi-entidad de integración usa fixtures sanitizadas parametrizadas para BBVA consolidado y Brubank multi-cuenta, incluyendo entidades sin movimientos.

## Límites explícitos del producto actual
- Solo soporta PDFs basados en texto. No hay OCR.
- La detección de bancos es heurística y frágil.
- Un banco detectado pero sin spec publicada debe fallar como `unknown_format`.
- Los PDFs consolidados requieren selección explícita de scopes antes del parseo final.
- No hay persistencia ni almacenamiento histórico.
- No hay API, CLI oficial ni empaquetado del producto; la entrada principal es Streamlit.
- La cobertura real actual se limita a los formatos publicados.

## Contexto de estructura del repo
- El entorno virtual operativo sigue siendo `venv/`.
- Los scripts de diagnóstico útiles quedaron centralizados en `scripts/diagnostics/`.
- El árbol activo ya no depende de artefactos históricos de Replit ni del lockfile legacy de `uv`.
