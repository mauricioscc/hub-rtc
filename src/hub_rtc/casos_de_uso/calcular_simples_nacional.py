from hub_rtc.dominio.resultado_simples import ResultadoSimples
from hub_rtc.dominio.simples_nacional import OperacaoSimples
from hub_rtc.portas.calculadora_simples_nacional import CalculadoraSimplesNacional


class CalcularSimplesNacional:
    def __init__(self, calculadora: CalculadoraSimplesNacional) -> None:
        self._calculadora = calculadora

    def executar(self, operacao: OperacaoSimples) -> ResultadoSimples:
        return self._calculadora.calcular(operacao)
