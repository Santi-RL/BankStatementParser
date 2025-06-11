"""Clases base para bancos argentinos."""

from typing import Dict

from ..spain.base import SpanishBankParser


class ArgentinianBankParser(SpanishBankParser):
    """Parser genérico para extractos de bancos argentinos."""

    bank_id = "generic_argentinian"
    aliases = ["argentina", "generic_argentinian"]

    def _extract_account_info(self, text_content: str) -> Dict[str, str]:
        """Extiende la detección de cuenta poniendo ARS como moneda por defecto.

        La clase base ``BaseBankParser`` asume Dólares (USD) cuando detecta el
        símbolo ``$`` en el texto. Sin embargo, en Argentina el signo ``$`` se
        utiliza para indicar Pesos, por lo que dicha heurística genera una
        detección incorrecta. Aquí normalizamos la moneda de la siguiente
        manera:

        - Si se encuentran indicadores explícitos de dólares (``USD``, ``U$`` o
          ``U$S``) se establece ``USD``.
        - En cualquier otro caso se utiliza ``ARS`` como valor por defecto.
        """

        info = super()._extract_account_info(text_content)

        text_upper = text_content.upper()
        usd_indicators = ["USD", "U$S", "U$"]

        if any(indicator in text_upper for indicator in usd_indicators):
            info["currency"] = "USD"
        else:
            # Predeterminar a pesos argentinos
            info["currency"] = "ARS"

        return info

    def _get_bank_name(self) -> str:
        return "Argentinian Bank"

