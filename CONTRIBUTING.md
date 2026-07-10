# Guía de Contribución

## Objetivo del proyecto

BankStatementParser convierte extractos bancarios en PDF a tablas normalizadas (Excel/CSV). El runtime es **100% declarativo**: cada banco se define mediante un archivo TOML (`spec.toml`) ubicado en `parser_specs/`, sin necesidad de escribir código Python.

## Formas de contribuir

| Contribución | Complejidad | Toca código Python? |
| --- | --- | --- |
| Agregar un banco nuevo | Media | No (*) |
| Agregar un formato alternativo de un banco existente | Media | No |
| Mejorar fixtures o regexes de una spec existente | Baja | No |
| Reportar un bug o un formato roto | Baja | No |
| Proponer mejoras al motor declarativo | Alta | Sí |

(*) Ver la sección "Detección de banco" más abajo para un caso excepcional menor.

## Política de tests para cambios nuevos

Toda implementación que cambie comportamiento debe traer tests nuevos o actualizar tests existentes. La cobertura debe ser proporcional al riesgo:

- Cambios en specs: fixture sanitizada, `expected_transactions.json` actualizado y `python format_cli.py regress` verde.
- Cambios en `format_engine.py`, `pdf_processor.py`, exportadores o helpers compartidos: test unitario o de integración que falle sin el cambio.
- Cambios en UI o flujo Streamlit: al menos test de la lógica extraída cuando exista y actualización del smoke/manual QA correspondiente.
- Cambios de seguridad, validación de PDFs, temporales, sanitización o exportaciones: tests de casos adversos.
- Cambios puramente documentales o de wording pueden omitir tests, indicando esa razón en el cierre del cambio.

El CI remoto ejecuta `python -m pytest -q` y `python format_cli.py regress` en push/PR a `main`.

---

## Agregar un banco nuevo: paso a paso

### Requisitos previos

```bash
# Clonar y activar entorno
git clone <repo-url>
cd BankStatementParser
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/macOS
pip install -r requirements.txt
```

Verificar que todo funciona:

```bash
python -m pytest -q
python format_cli.py regress
```

### Paso 1: Crear una rama

```bash
git checkout -b feat/add-<bank_id>
# Ejemplo: git checkout -b feat/add-santander_ar
```

### Paso 2: Generar el borrador con la CLI

Necesitás un PDF real del extracto bancario. La CLI extrae el texto, genera un borrador de spec y crea fixtures sanitizadas automáticamente.

Guardá previamente el PDF real en `local_samples/<bank_id>/`. Esa carpeta es exclusivamente local y está ignorada por Git; no copies extractos reales a `attached_assets/`, `parser_specs/` ni a otra ruta versionada.

```bash
python format_cli.py train path/al/extracto.pdf \
  --bank-id "santander_ar" \
  --format-id "default" \
  --display-name "Banco Santander (Arg.)" \
  --country "AR" \
  --currency "ARS" \
  --required-keyword "SANTANDER" \
  --required-keyword "MOVIMIENTOS" \
  --line-pattern '^(?P<date>\d{2}/\d{2}/\d{4})\s+(?P<description>.+?)\s+(?P<amount>[+-]?[\d.,]+)$'
```

Esto crea:

```
parser_specs/santander_ar/default/
├── spec.toml                        # Borrador (status = "draft")
├── fixtures/
│   ├── sample_text.txt              # Texto sanitizado del PDF
│   └── expected_transactions.json   # Transacciones esperadas
```

### Paso 3: Refinar la spec

Editá `spec.toml` directamente hasta que el parseo sea correcto. Los campos clave a ajustar:

| Campo | Qué hace | Cuándo ajustarlo |
| --- | --- | --- |
| `detect.required_keywords` | Palabras que deben aparecer en el texto del PDF | Si el banco no se detecta correctamente |
| `detect.min_score` | Proporción mínima de keywords que deben matchear (0.0–1.0) | Si hay falsos positivos o negativos |
| `extract.line_pattern` | Regex que captura una transacción | Si las transacciones no se parsean bien |
| `extract.candidate_pattern` | Regex para identificar líneas candidatas | Si la cobertura es baja |
| `extract.ignore_patterns` | Patrones de líneas a ignorar (headers, footers) | Si se incluyen líneas basura |
| `extract.stop_patterns` | Patrones que marcan el fin de las transacciones | Si se captura texto después de la tabla |
| `extract.section_start_patterns` | Patrones que marcan el inicio de secciones | Si las transacciones tienen secciones separadas |
| `extract.reject_description_amount_tail` | Rechaza filas cuya descripción termina en un monto | Si una columna monetaria nueva podría quedar absorbida como descripción |
| `fields.date` / `description` / `amount` | Nombres de los grupos capturados en `line_pattern` | Si los campos no mapean bien |
| `normalize.date_formats` | Formatos de fecha Python (`strptime`) | Si las fechas no se parsean |
| `change_detection.min_transactions` | Mínimo de transacciones esperadas | Si el extracto de ejemplo es pequeño |
| `change_detection.min_match_ratio` | Cobertura mínima (candidatos vs matcheados) | Ajustar según complejidad del formato |

### Paso 4: Validar iterativamente

```bash
python format_cli.py validate-draft parser_specs/santander_ar/default/spec.toml \
  --pdf path/al/extracto.pdf
```

La salida muestra:

```json
{
  "ok": true,
  "diagnostics": {
    "matched_starts": 45,
    "candidate_lines": 50,
    "coverage": 0.90,
    "transactions_found": 45
  },
  "transactions": 45
}
```

Iterá hasta que:
- `ok` sea `true`
- `coverage` >= el `min_match_ratio` de tu spec
- `transactions_found` >= `min_transactions` de tu spec
- Las transacciones tengan sentido (revisá fechas, montos, descripciones)

Si la tabla termina con columnas monetarias (`amount`, `balance`, `debit`, `credit`) y las descripciones reales no deberían terminar con importes, activá `extract.reject_description_amount_tail = true`. Esta protección evita que un layout nuevo con una columna monetaria extra sea parseado como si el primer monto fuera parte de la descripción. No la actives en formatos donde las descripciones válidas pueden terminar en importes; Roela es un ejemplo cubierto por regresión.

Para cada spec publicada o modificada, agregá al menos una prueba de `format_changed` cuando sea razonable. Las fixtures sanitizadas de cambios parciales viven en `tests/fixtures/format_changed_partial/` y deben conservar señales reales del banco, encabezados reconocibles y una alteración concreta de tabla.

### Paso 5: Publicar la spec

```bash
python format_cli.py publish parser_specs/santander_ar/default/spec.toml
```

Esto cambia `status = "draft"` a `status = "published"` en el TOML.

### Paso 6: Verificar la regresión

```bash
python -m pytest tests/regression/test_format_regression.py -v
python format_cli.py regress
```

Tu spec nueva debería aparecer en la lista y pasar. El test de regresión descubre automáticamente todas las specs publicadas — no hace falta tocar código de test.

### Paso 7: Correr la suite completa

```bash
python -m pytest -q
```

Todos los tests existentes deben seguir pasando.

---

## Detección de banco

El archivo `pdf_processor.py` tiene una función `_detect_bank()` con un diccionario de keywords → bank_id. Este diccionario se usa como **hint de ruteo rápido**, no como autoridad exclusiva.

**Si tu keyword ya está en el diccionario** (ej: `'santander'` → `'santander'`), la spec se matcheará automáticamente.

**Si tu keyword no está**, el banco se detecta como `"unknown"` y el motor prueba **todas** las specs publicadas. Gracias a los `required_keywords` de tu spec, igual debería matchear.

Para un ruteo óptimo, podés agregar tu keyword al diccionario de `_detect_bank()`. Es un cambio de una línea:

```python
# En pdf_processor.py, dentro de _detect_bank():
keywords = {
    # ... existentes ...
    'tu_keyword': 'tu_bank_id',   # <- agregar aquí
}
```

> **Nota**: este es el único cambio Python que podría hacer falta. Si las `required_keywords` de tu spec son suficientemente distintivas, no es estrictamente necesario.

---

## Estructura de un PR válido

Un PR para agregar un banco nuevo debe incluir **como mínimo**:

```
parser_specs/<bank_id>/default/
├── spec.toml                          # Con status = "published"
├── fixtures/
│   ├── sample_text.txt                # Texto sanitizado (sin datos reales)
│   └── expected_transactions.json     # Salida esperada
```

### Checklist del PR

- [ ] La spec tiene `status = "published"`
- [ ] Las fixtures están **sanitizadas** (sin nombres reales, sin CBU/CUIT reales, sin montos reales)
- [ ] `python format_cli.py regress` pasa incluyendo la spec nueva
- [ ] `python -m pytest -q` sigue verde (todos los tests previos pasan)
- [ ] El cambio incluye tests nuevos o actualizados cuando modifica comportamiento
- [ ] El `bank_id` es descriptivo y sigue la convención: minúsculas, snake_case, con sufijo de país si aplica (ej: `santander_ar`, `bbva_es`)
- [ ] El `display_name` es legible para el usuario final
- [ ] Los `required_keywords` son distintivos del banco (no genéricos como "cuenta" o "fecha")
- [ ] `min_transactions` y `min_match_ratio` en `change_detection` son razonables para el formato
- [ ] No se incluyeron archivos PDF en el PR (son binarios pesados)

### Archivos que NO debe tocar un PR de banco nuevo

| Archivo | Motivo |
| --- | --- |
| `format_engine.py` | Motor compartido; cambios aquí afectan a todos los bancos |
| `app.py` | UI principal; no debería cambiar por un banco nuevo |
| `excel_generator.py` | Generador de Excel; no debería cambiar |
| `utils.py` | Utilidades compartidas |
| Tests existentes | Los tests de regresión descubren specs automáticamente |

La **única excepción** es agregar opcionalmente una línea al diccionario de `_detect_bank()` en `pdf_processor.py`.

---

## Convenciones de naming

| Campo | Convención | Ejemplo |
| --- | --- | --- |
| `bank_id` | snake_case, minúsculas, sufijo de país si aplica | `santander_ar`, `chase`, `bbva` |
| `format_id` | snake_case, `default` para el formato principal | `default`, `account_summary` |
| Directorio de spec | `parser_specs/<bank_id>/<format_id>/` | `parser_specs/santander_ar/default/` |
| `display_name` | Nombre amigable para el usuario | `"Banco Santander (Arg.)"` |
| `country` | ISO 3166-1 alpha-2 | `"AR"`, `"US"`, `"ES"` |
| `currency_default` | ISO 4217 | `"ARS"`, `"USD"`, `"EUR"` |

---

## Ejemplo completo: spec mínima

Este es un ejemplo de una spec funcional para un banco ficticio con extractos simples:

```toml
[meta]
bank_id = "ejemplo_ar"
format_id = "default"
version = 1
status = "published"
country = "AR"
currency_default = "ARS"
display_name = "Banco Ejemplo (Arg.)"

[detect]
required_keywords = ["BANCO EJEMPLO S.A.", "RESUMEN DE CUENTA", "MOVIMIENTOS"]
excluded_keywords = []
min_score = 0.66

[extract]
strategy = "line_regex"
line_pattern = '^(?P<date>\d{2}/\d{2}/\d{4})\s+(?P<description>.+?)\s{2,}(?P<amount>[+-]?[\d.,]+)\s+(?P<balance>[\d.,]+)$'
candidate_pattern = '^\d{2}/\d{2}/\d{4}\s+'
section_start_patterns = ['^MOVIMIENTOS']
stop_patterns = ['^TOTAL\b', '^SALDO FINAL']
ignore_patterns = ['^Fecha\s+Descripción', '^-{3,}']
multiline = false

[fields]
date = "date"
description = "description"
amount = "amount"
balance = "balance"
account_pattern = 'Cuenta\s*[Nn]°?\s*:?\s*(\d[\d\-/]+)'

[normalize]
date_formats = ['%d/%m/%Y']

[change_detection]
min_transactions = 5
min_match_ratio = 0.5
```

---

## Ejemplo completo: spec por secciones (depósitos/retiros)

Si el extracto separa transacciones por tipo (como Chase):

```toml
[meta]
bank_id = "ejemplo_us"
format_id = "default"
version = 1
status = "published"
country = "US"
currency_default = "USD"
display_name = "Example Bank (US)"

[detect]
required_keywords = ["EXAMPLE BANK N.A.", "DEPOSITS", "WITHDRAWALS"]
excluded_keywords = []
min_score = 0.66

[extract]
strategy = "line_regex"

[[extract.sections]]
name = "deposits"
start_patterns = ['^DEPOSITS$']
stop_patterns = ['^Total Deposits']
line_pattern = '^(?P<date>\d{2}/\d{2})\s+(?P<description>.+?)\s+(?P<amount>\$?[\d,]+\.\d{2})$'
candidate_pattern = '^\d{2}/\d{2}\s+'
multiline = false
amount_sign = "positive"

[[extract.sections]]
name = "withdrawals"
start_patterns = ['^WITHDRAWALS$']
stop_patterns = ['^Total Withdrawals']
line_pattern = '^(?P<date>\d{2}/\d{2})\s+(?P<description>.+?)\s+(?P<amount>\$?[\d,]+\.\d{2})$'
candidate_pattern = '^\d{2}/\d{2}\s+'
multiline = false
amount_sign = "negative"

[fields]
date = "date"
description = "description"
amount = "amount"
balance = ""
account_pattern = '(?m)^Account\s+Number:\s*(\d+)$'

[normalize]
date_formats = ['%m/%d']
statement_year_pattern = 'through.*?(?P<year>20\d{2})'

[change_detection]
min_transactions = 3
min_match_ratio = 0.8
```

---

## Formatos avanzados

Para formatos más complejos, el motor soporta:

- **`multiline = true`**: descripciones que abarcan múltiples líneas
- **`extract.sign_rules`**: determinación de débito/crédito basada en códigos de transacción
- **`fields.debit` + `fields.credit`**: derivación declarativa de `amount` cuando el PDF separa columnas de débito y crédito
- **`pdf_text_strategy`**: estrategias especiales de extracción de texto (`"roela_columns"`, `"x_band_table"`)
- **`scopes`**: documentos consolidados con múltiples cuentas/tarjetas
- **`current_date_pattern` + `strip_current_date`**: fechas que aplican a bloques de transacciones

Para ejemplos de estos patrones, consultá las specs existentes:
- Roela (`parser_specs/roela_ar/default/`) — multiline, sign_rules, columns
- BBVA (`parser_specs/bbva/default/`) — scopes multi-entidad
- Mercado Pago (`parser_specs/mercado_pago/default/`) — x_band_table
- Brubank (`parser_specs/brubank/default/`) — columnas débito/crédito y resumen multi-cuenta

---

## Formatos multi-entidad o multi-cuenta

Cuando un extracto consolidado incluye varias cuentas, tarjetas, wallets o subcuentas, debe implementarse siempre con la misma metodología. El objetivo es que BBVA, Brubank y cualquier banco futuro usen el mismo contrato de scopes, selección explícita y regresión automatizada.

### Patrón de spec

1. Mantener el runtime declarativo. No agregar lógica Python específica del banco para elegir entidades, mezclar cuentas o filtrar movimientos.
2. Declarar scopes en la spec con `[[scopes]]` cuando las entidades aparecen como catálogo del documento, o con `[[extract.sections.context_rules]]` y `action = "activate_scope"` cuando cada bloque activa una entidad.
3. Definir siempre `scope_id_template`, `label_template`, `product_type`, `account_template` y moneda (`currency` o `currency_template`). Si una sección solo completa datos de un scope ya descubierto, usar `action = "update_scope"` con `create_if_missing = false`.
4. Preservar entidades sin movimientos como `available_scopes` cuando el resumen las informa. La UI debe poder mostrarlas aunque no generen transacciones.
5. Usar `selected_scope_ids` como único mecanismo de filtrado. No crear flags, heurísticas o reglas paralelas por banco para decidir qué cuenta se procesa.

### Convenciones prácticas

- `scope_id_template` debe generar IDs estables con prefijo de producto, por ejemplo `bank_account:<id>`, `credit_card:<id>`, `debit_card:<id>` o `wallet:<id>`.
- `label_template` debe ser legible para el usuario final y suficientemente corto para hojas de Excel.
- `product_type` debe usar categorías consistentes: `bank_account`, `credit_card`, `debit_card`, `wallet` u otra categoría explícita si el producto no encaja.
- `account_template` debe conservar el identificador normalizado que luego aparece en las transacciones.
- La moneda debe resolverse por scope cuando el documento mezcla monedas. No asumir la moneda default del banco si el scope informa otra.
- Los scopes descubiertos sin movimientos deben quedar disponibles en `analysis["available_scopes"]`, pero no deben crear transacciones vacías.

### Fixtures y cobertura obligatoria

1. Guardar una fixture sanitizada representativa en `parser_specs/<bank_id>/<format_id>/fixtures/`.
2. Si el formato tiene una variante simple y otra multi-cuenta, usar una fixture explícita como `multi_account_sample_text.txt` para el caso consolidado.
3. Agregar el banco/formato a `MULTI_SCOPE_FIXTURE_CASES` en `tests/integration/test_bank_parsing.py`.
4. Ese caso debe declarar scopes esperados, monedas esperadas, selección de todos los scopes, selección de un grupo y selección de un scope individual.
5. Validar que `analyze_pdf()` marque `multi_scope = true`, que `process_pdf()` falle sin selección explícita, que el filtrado por scopes devuelva solo lo pedido y que `ExcelGenerator` cree hojas por entidad sin nombres inválidos.
6. Ejecutar `venv\Scripts\python.exe -m pytest -q` y `venv\Scripts\python.exe format_cli.py regress` antes de publicar o commitear.

Referencias actuales:
- BBVA consolidado: `parser_specs/bbva/default/` y `parser_specs/bbva/default/fixtures/sample_text.txt`.
- Brubank multi-cuenta: `parser_specs/brubank/default/` y `parser_specs/brubank/default/fixtures/multi_account_sample_text.txt`.

---

## Conciliación opcional

La conciliación es un control auxiliar de salida y nunca una condición para aceptar o exportar movimientos. Sólo debe habilitarse en una spec cuando el extracto informa valores de resumen confiables.

- Declarar `[reconciliation]` y una `[[reconciliation.sections]]` por scope/moneda que pueda conciliarse.
- Mantener estables los `scope_id` y alinearlos con los scopes usados por las transacciones.
- Extraer por regex `opening_balance` y `closing_balance`; `credits` y `debits` informados pueden conservarse como evidencia auxiliar.
- Calcular el control con los movimientos normalizados: `saldo inicial + neto de movimientos` contra saldo final.
- Declarar `tolerance`, `precision`, período y formatos de fecha en la spec; no incorporar lógica Python específica del banco.
- Si faltan los saldos o el formato todavía no soporta el control, devolver `not_available`. Una diferencia devuelve `failed`, pero ambos estados deben preservar `success = true`, `parse_status = "ok"` y la exportación.
- Cubrir con fixtures sanitizadas los estados conciliado, con diferencia, no disponible y la selección individual de scope.

Brubank `default` es la referencia inicial de este contrato.

---
## Sanitización de fixtures

Las fixtures que acompañan la spec **no deben contener datos personales reales**. La CLI `train` sanitiza automáticamente, pero revisá manualmente que:

- No queden nombres de personas reales
- No queden CBU, CUIT, DNI u otros identificadores reales
- No queden montos que permitan identificar a alguien
- Los **keywords estructurales** del banco sí se preserven (nombres de secciones, encabezados, etc.)

---

## Flujo del PR

```
1. Fork / branch
2. format_cli.py train ...          → genera borrador + fixtures
3. Editar spec.toml                 → refinar regex y configuración
4. format_cli.py validate-draft ... → verificar cobertura
5. format_cli.py publish ...        → marcar como publicada
6. Agregar/actualizar tests          → cubrir el comportamiento nuevo o corregido
7. pytest -q                        → toda la suite verde
8. format_cli.py regress            → regresión verde incluyendo la nueva
9. Commit y push
10. Abrir PR con el checklist completado
```

---

## Preguntas frecuentes

**¿Puedo agregar un banco sin escribir Python?**
Sí. La spec TOML + fixtures es todo lo que se necesita. Opcionalmente podés agregar una línea de detección en `pdf_processor.py`.

**¿Cómo sé si mi regex está bien?**
Usá `format_cli.py validate-draft` iterativamente. Mostrará cobertura, cantidad de matches y diagnósticos.

**¿Puedo tener múltiples formatos para un mismo banco?**
Sí. Usá un `format_id` diferente (ej: `account_summary`, `credit_card`). Cada uno vive en su propio directorio.

**¿Qué pasa si el banco cambia su formato de PDF?**
El sistema tiene detección de cambios (`change_detection`). Si la cobertura baja del umbral, devuelve `format_changed` en vez de datos incorrectos. Para soportar el nuevo formato, se publica una nueva versión de la spec.

**¿Necesito incluir el PDF real en el PR?**
No. Guardalo únicamente en `local_samples/<bank_id>/`, que está ignorado por Git. El PR debe incluir sólo las fixtures sanitizadas.

**¿Cómo nombro mi banco si opera en varios países?**
Usá el sufijo de país: `santander_ar`, `santander_es`, `santander_mx`. Cada país tiene formatos de extracto diferentes.
