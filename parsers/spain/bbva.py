from .base import SpanishBankParser

class BBVAParser(SpanishBankParser):
    """Parser de extractos para BBVA."""

    bank_id = 'bbva'
    aliases = ['bbva']

    def _get_bank_name(self) -> str:
        return "BBVA"
