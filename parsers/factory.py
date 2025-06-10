from typing import Optional, Dict, Type

from . import PARSER_REGISTRY
from .base import BaseBankParser

class BankParserFactory:
    """Fábrica que instancia parsers usando :data:`PARSER_REGISTRY`."""

    def __init__(self) -> None:
        self._instances: Dict[Type[BaseBankParser], BaseBankParser] = {}

    def get_parser(self, bank_identifier: str) -> Optional[BaseBankParser]:
        cls = PARSER_REGISTRY.get(bank_identifier)
        if not cls and bank_identifier != "unknown":
            if any(k in bank_identifier.lower() for k in ["spanish", "spain", "españa"]):
                cls = PARSER_REGISTRY.get("generic_spanish")
            else:
                cls = PARSER_REGISTRY.get("generic_english")

        if cls is None:
            return None

        if cls not in self._instances:
            self._instances[cls] = cls()

        return self._instances[cls]
