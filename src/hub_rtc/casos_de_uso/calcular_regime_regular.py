from hub_rtc.dominio.operacao import Operacao
from hub_rtc.dominio.resultado import ResultadoCalculo
from hub_rtc.portas.calculadora_regime_regular import CalculadoraRegimeRegular


class CalcularRegimeRegular:
    def __init__(self, calculadora: CalculadoraRegimeRegular) -> None:
        self._calculadora = calculadora

    def executar(self, operacao: Operacao) -> ResultadoCalculo:
        return self._calculadora.calcular(operacao)
