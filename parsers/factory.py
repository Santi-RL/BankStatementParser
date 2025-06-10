import pkgutil
import importlib
import inspect
from typing import Optional

from .base import BaseBankParser

class BankParserFactory:
    """Fábrica que registra dinámicamente todos los parsers."""

    def __init__(self) -> None:
        self.parsers: dict[str, BaseBankParser] = {}
        self._discover_parsers()

    def _discover_parsers(self) -> None:
        package = importlib.import_module(__name__.split('.')[0])
        for _, module_name, _ in pkgutil.walk_packages(package.__path__, package.__name__ + '.'):
            module = importlib.import_module(module_name)
            for _, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, BaseBankParser) and obj is not BaseBankParser:
                    parser_instance = obj()
                    keys = [obj.bank_id] + list(getattr(obj, 'aliases', []))
                    for key in filter(None, keys):
                        if key not in self.parsers:
                            self.parsers[key] = parser_instance

    def get_parser(self, bank_identifier: str) -> Optional[BaseBankParser]:
        parser = self.parsers.get(bank_identifier)
        if not parser and bank_identifier != 'unknown':
            if any(k in bank_identifier.lower() for k in ['spanish', 'spain', 'españa']):
                parser = self.parsers.get('generic_spanish')
            else:
                parser = self.parsers.get('generic_english')
        return parser
