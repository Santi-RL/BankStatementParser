from .base import SpanishBankParser

class CaixaBankParser(SpanishBankParser):
    """Parser de extractos para CaixaBank."""

    bank_id = 'caixabank'
    aliases = ['caixabank']

    def _get_bank_name(self) -> str:
        return "CaixaBank"
