# Runbook de Primera Prueba en Producción

## Objetivo
Levantar la app en un modo controlado para una prueba inicial con usuarios o datasets reales acotados, sin exponer el backoffice ni detalles internos de errores.

## Arranque

```bash
venv\Scripts\python.exe scripts/run_app.py --mode production-test
```

La app queda escuchando en `http://127.0.0.1:8501`.

## Logs
- Archivo principal: `logs/app.log`
- El modo `production-test` deja el logging en `INFO`.
- Los errores inesperados se muestran sanitizados en UI y el detalle queda en el log.

## Smoke mínimo antes de habilitar usuarios
1. Cargar `local_samples/galicia_ar/TestGalicia.pdf`.
2. Ejecutar `Analizar Extractos`.
3. Ejecutar `Procesar Extractos`.
4. Verificar resumen con 52 transacciones.
5. Verificar descarga Excel y CSV.
6. Confirmar que no aparece la pestaña `Aprender Formatos`.

## Formatos soportados para la prueba
- `galicia_ar/default`
- `roela_ar/default`
- `chase/default`
- `bbva/default`
- `bbva/account_summary`
- `mercado_pago/default`
- `brubank/default`

## Criterio de rollback
Volver a `local` o detener la prueba si aparece cualquiera de estos casos:
- errores inesperados repetidos en `logs/app.log`,
- diferencias de moneda o montos reportadas por usuarios,
- fallos al descargar Excel o CSV,
- documentos conocidos que dejen de matchear como `ok`.

## Comando de rollback

```bash
venv\Scripts\python.exe scripts/run_app.py --mode local
```
