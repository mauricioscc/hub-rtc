from datetime import date
from typing import Protocol

from hub_rtc.dominio.catalogo import AtividadeSimples
from hub_rtc.dominio.resultado_simples import ResultadoSimples
from hub_rtc.dominio.simples_nacional import OperacaoSimples


class CalculadoraSimplesNacional(Protocol):
    """Quem sabe calcular CBS e IBS de uma operação do Simples Nacional."""

    def calcular(self, operacao: OperacaoSimples) -> ResultadoSimples: ...


class CatalogoAtividades(Protocol):
    """Quem conhece as atividades do Simples Nacional vigentes numa data."""

    def atividades(self, data: date) -> tuple[AtividadeSimples, ...]: ...
