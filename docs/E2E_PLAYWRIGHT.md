# Smoke E2E con Playwright MCP

## Objetivo
Validar el flujo real de la app Streamlit en un navegador con dos escenarios mínimos:

1. procesamiento exitoso de un PDF conocido en `production-test`,
2. acceso al backoffice de formatos y visibilidad del registro declarativo en `local`.

## Preparación
1. Levantar la app endurecida para la prueba controlada con:

```bash
venv\Scripts\python.exe scripts/run_app.py --mode production-test
```

2. Esperar a que la app quede escuchando en `http://127.0.0.1:8501`.

## Escenario 1: PDF conocido
1. Abrir `http://127.0.0.1:8501`.
2. Ir a la pestaña `Procesar Extractos`.
3. Subir `attached_assets/TestGalicia.pdf`.
4. Ejecutar `Procesar Extractos`.
5. Verificar:
   - mensaje de procesamiento completado,
   - preview de transacciones,
   - botón de descarga Excel,
   - resumen con 52 transacciones,
   - ausencia de la pestaña `Aprender Formatos`.

## Escenario 2: backoffice
1. Reiniciar la app en modo local:

```bash
venv\Scripts\python.exe scripts/run_app.py --mode local
```

2. Ir a la pestaña `Aprender Formatos`.
2. Verificar:
   - contador de publicados mayor o igual a 1,
   - aparición de `galicia_ar/default`,
   - formulario de entrenamiento visible,
   - posibilidad de cargar un PDF y ver texto extraído sin guardar el borrador.

## Nota
Los tests de regresión y cambio de formato quedan automatizados en `pytest`; este smoke con MCP cubre la integración real UI + navegador.
