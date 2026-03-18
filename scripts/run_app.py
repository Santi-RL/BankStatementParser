from __future__ import annotations

import argparse
import sys

from streamlit.web.cli import main as streamlit_main


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Streamlit app with a stable local configuration")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--lang", choices=["en", "es"], default="es")
    parser.add_argument("--mode", choices=["local", "production-test"], default="local")
    args, _ = parser.parse_known_args()

    sys.argv = [
        "streamlit",
        "run",
        "app.py",
        "--server.port",
        "8501",
        "--server.headless",
        "true",
        "--",
        "--lang",
        args.lang,
        "--mode",
        args.mode,
    ]
    if args.debug:
        sys.argv.append("--debug")
    raise SystemExit(streamlit_main())
