from decimal import Decimal

from hub_rtc.casos_de_uso.calcular_regime_regular import CalcularRegimeRegular
from hub_rtc.dominio.operacao import Operacao
from hub_rtc.dominio.resultado import ResultadoCalculo, TributosDoItem
from tests.unidade.dominio.test_operacao import um_item, uma_operacao


class CalculadoraFalsa:
    def __init__(self) -> None:
        self.recebida: Operacao | None = None

    def calcular(self, operacao: Operacao) -> ResultadoCalculo:
        self.recebida = operacao
        zero = Decimal(0)
        return ResultadoCalculo(itens=(TributosDoItem(1, zero, Decimal("2.10"), zero, zero, zero),))


def test_entrega_a_operacao_ao_motor_e_devolve_o_resultado() -> None:
    calculadora = CalculadoraFalsa()
    operacao = uma_operacao((um_item(),))

    resultado = CalcularRegimeRegular(calculadora).executar(operacao)

    assert calculadora.recebida is operacao
    assert resultado.total_cbs == Decimal("2.10")
