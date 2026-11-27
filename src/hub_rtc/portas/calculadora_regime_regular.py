from typing import Protocol

from hub_rtc.dominio.operacao import Operacao
from hub_rtc.dominio.resultado import ResultadoCalculo


class CalculadoraRegimeRegular(Protocol):
    """Quem sabe calcular CBS, IBS e IS de uma operação no regime regular."""

    def calcular(self, operacao: Operacao) -> ResultadoCalculo: ...
