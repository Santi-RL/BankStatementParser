# Bank Statement Parser

This application converts PDF bank statements into Excel files using a Streamlit interface.

## Running the App

Use `streamlit run app.py` to start the application. An optional `--debug` flag controls the default logging level.

```bash
streamlit run app.py -- --debug
```

- When `--debug` is provided, the 🐞 **Debug Mode** checkbox in the sidebar is pre‑checked and logging starts at the `DEBUG` level.
- Without `--debug`, the checkbox starts unchecked and logging defaults to `INFO`.
- Toggling the checkbox while the app is running will immediately change the logger level and the setting persists across page reruns.

The CLI flag only controls the initial state; the sidebar checkbox is the source of truth for logging after startup.
