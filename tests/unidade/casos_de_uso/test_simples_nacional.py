from datetime import date

from hub_rtc.casos_de_uso.calcular_simples_nacional import CalcularSimplesNacional
from hub_rtc.casos_de_uso.consultar_atividades_simples import ConsultarAtividadesSimples
from hub_rtc.dominio.catalogo import AtividadeSimples
from hub_rtc.dominio.resultado_simples import ItemSimplesCalculado, ResultadoSimples
from hub_rtc.dominio.simples_nacional import OperacaoSimples
from tests.unidade.dominio.test_simples_nacional import uma_operacao


class CalculadoraFalsa:
    def __init__(self) -> None:
        self.recebida: OperacaoSimples | None = None

    def calcular(self, operacao: OperacaoSimples) -> ResultadoSimples:
        self.recebida = operacao
        return ResultadoSimples(itens=(ItemSimplesCalculado(numero=1, situacao="CALCULADO"),))


class CatalogoFalso:
    def __init__(self) -> None:
        self.data_pedida: date | None = None

    def atividades(self, data: date) -> tuple[AtividadeSimples, ...]:
        self.data_pedida = data
        return (AtividadeSimples("01", "Revenda", "I", True, (55,)),)


def test_entrega_a_operacao_ao_motor_e_devolve_o_resultado() -> None:
    calculadora = CalculadoraFalsa()
    operacao = uma_operacao()

    resultado = CalcularSimplesNacional(calculadora).executar(operacao)

    assert calculadora.recebida is operacao
    assert resultado.itens[0].numero == 1


def test_consulta_as_atividades_na_data_pedida() -> None:
    catalogo = CatalogoFalso()

    atividades = ConsultarAtividadesSimples(catalogo).executar(date(2027, 3, 15))

    assert catalogo.data_pedida == date(2027, 3, 15)
    assert atividades[0].codigo == "01"
