"""Clases base para bancos argentinos."""

from typing import Dict

from ..spain.base import SpanishBankParser


class ArgentinianBankParser(SpanishBankParser):
    """Parser genérico para extractos de bancos argentinos."""

    bank_id = "generic_argentinian"
    aliases = ["argentina", "generic_argentinian"]

    def _extract_account_info(self, text_content: str) -> Dict[str, str]:
        """Extiende la detección de cuenta poniendo ARS como moneda por defecto."""

        info = super()._extract_account_info(text_content)
        if info.get("currency") == "EUR":
            info["currency"] = "ARS"
        return info

    def _get_bank_name(self) -> str:
        return "Argentinian Bank"

