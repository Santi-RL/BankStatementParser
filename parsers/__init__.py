"""Inicialización del paquete de parsers.

Este módulo descubre automáticamente todos los parsers disponibles y los
registra en :data:`PARSER_REGISTRY`. Cualquier subclase de
``BaseBankParser`` dentro del paquete ``parsers`` queda disponible al
importar ``parsers``.
"""

from __future__ import annotations

from typing import Dict, Type

import importlib
import inspect
import pkgutil

from .base import BaseBankParser

PARSER_REGISTRY: Dict[str, Type[BaseBankParser]] = {}

__all__ = ["BaseBankParser"]


def _discover_parsers() -> None:
    """Importa submódulos y registra subclases de ``BaseBankParser``."""

    package = importlib.import_module(__name__)
    for _, module_name, _ in pkgutil.walk_packages(
        package.__path__, package.__name__ + "."
    ):
        module = importlib.import_module(module_name)
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, BaseBankParser) and obj is not BaseBankParser:
                globals()[name] = obj
                if name not in __all__:
                    __all__.append(name)
                keys = [obj.bank_id] + list(getattr(obj, "aliases", []))
                for key in filter(None, keys):
                    PARSER_REGISTRY.setdefault(key, obj)


_discover_parsers()

from .factory import BankParserFactory

__all__.append("BankParserFactory")

