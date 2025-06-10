"""Mantiene compatibilidad con la antigua ubicación de los parsers."""

from parsers import (
    BaseBankParser,
    SpanishBankParser,
    SantanderParser,
    BBVAParser,
    CaixaBankParser,
    GaliciaParser,
    GenericEnglishParser,
    BankParserFactory,
)

__all__ = [
    'BaseBankParser',
    'SpanishBankParser',
    'SantanderParser',
    'BBVAParser',
    'CaixaBankParser',
    'GaliciaParser',
    'GenericEnglishParser',
    'BankParserFactory',
]
