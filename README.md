# Analizador de Extractos Bancarios

Esta aplicación convierte extractos bancarios en PDF a archivos Excel mediante la interfaz de Streamlit.

## Instalación

En plataformas como **Streamlit Community Cloud** las dependencias se instalan usando un archivo `requirements.txt`.
Para generarlo localmente se ejecutó:

```bash
uv pip compile pyproject.toml -o requirements.txt
```

El resultado se incluye en el repositorio para que la plataforma lo utilice automáticamente al desplegar la aplicación.

## Ejecución de la Aplicación

Usa `streamlit run app.py` para iniciar la aplicación. Un flag opcional `--debug` controla el nivel de registro por defecto.

```bash
streamlit run app.py -- --debug
```

- Cuando se proporciona `--debug`, la casilla 🐞 **Modo Depuración** de la barra lateral aparece marcada y el registro comienza en nivel `DEBUG`.
- Sin `--debug`, la casilla inicia desmarcada y el registro se establece en `INFO`.
- Cambiar la casilla mientras la aplicación está en ejecución ajustará el nivel de registro inmediatamente y la configuración se mantiene entre recargas.

El flag de la CLI solo controla el estado inicial; la casilla de la barra lateral es la fuente de verdad después del arranque.
