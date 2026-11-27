from datetime import date
from decimal import Decimal
from typing import Any

from fastapi.testclient import TestClient

from hub_rtc.dominio.catalogo import AtividadeSimples
from hub_rtc.dominio.erros import ErroDoHub, MotorIndisponivel
from hub_rtc.dominio.resultado import MemoriaDeCalculo
from hub_rtc.dominio.resultado_simples import ItemSimplesCalculado, ResultadoSimples
from hub_rtc.dominio.simples_nacional import OperacaoSimples
from hub_rtc.entrada.api import criar_app
from hub_rtc.entrada.api_simples import criar_roteador_simples

PEDIDO: dict[str, Any] = {
    "data": "2027-03-15",
    "tipo_documento": 55,
    "crt": 1,
    "aliquotas_efetivas": {
        "fator_r": False,
        "impedimento_sublimite": False,
        "anexos": {
            "I": {"cbs": "1.1612", "ibs": "0.0129"},
            "III": {
                "cbs": "2.3874",
                "ibs": "0.0263",
                "sem_redistribuicao_iss": {"cbs": "2.3591", "ibs": None},
            },
        },
    },
    "itens": [
        {
            "numero": 1,
            "atividade": "01",
            "classificacao_tributaria": "000001",
            "base_calculo": "1000.00",
            "valor_imposto_seletivo": "5.00",
            "nbs": "114051000",
        }
    ],
}


class CasoDeUsoFalso:
    def __init__(self, falha: ErroDoHub | None = None) -> None:
        self.falha = falha
        self.recebida: OperacaoSimples | None = None

    def executar(self, operacao: OperacaoSimples) -> ResultadoSimples:
        self.recebida = operacao
        if self.falha:
            raise self.falha
        calculado = ItemSimplesCalculado(
            numero=1,
            situacao="CALCULADO",
            receita_bruta=Decimal("1000.00"),
            base_calculo=Decimal("1000.00"),
            aliquota_cbs=Decimal("1.1612"),
            aliquota_ibs=Decimal("0.0129"),
            cbs=Decimal("11.61"),
            ibs=Decimal("0.13"),
            imposto_seletivo=Decimal("5.00"),
            anexo="I",
            memorias_de_calculo=(MemoriaDeCalculo("CBS", "explicação"),),
        )
        recusado = ItemSimplesCalculado(2, "NAO_CALCULADO", mensagens=("atividade desconhecida",))
        return ResultadoSimples(
            itens=(calculado, recusado), regime_apuracao="SN_PLENO", avisos=("um aviso",)
        )


class ConsultaFalsa:
    def __init__(self) -> None:
        self.data_pedida: date | None = None

    def executar(self, data: date) -> tuple[AtividadeSimples, ...]:
        self.data_pedida = data
        return (AtividadeSimples("01", "Revenda", "I", True, (55, 65)),)


def cliente(caso: CasoDeUsoFalso, consulta: ConsultaFalsa | None = None) -> TestClient:
    roteador = criar_roteador_simples(caso, consulta or ConsultaFalsa())
    return TestClient(criar_app([roteador]))


def test_calcula_e_devolve_itens_totais_e_regime() -> None:
    resposta = cliente(CasoDeUsoFalso()).post("/api/calculos/simples-nacional", json=PEDIDO)

    assert resposta.status_code == 200
    corpo = resposta.json()
    primeiro, segundo = corpo["itens"]
    assert (primeiro["situacao"], primeiro["cbs"], primeiro["ibs"]) == (
        "CALCULADO",
        "11.61",
        "0.13",
    )
    assert (primeiro["anexo"], primeiro["total"]) == ("I", "16.74")
    assert primeiro["memorias"] == [{"tributos": "CBS", "texto": "explicação"}]
    assert segundo["situacao"] == "NAO_CALCULADO"
    assert segundo["mensagens"] == ["atividade desconhecida"]
    assert corpo["totais"] == {
        "cbs": "11.61",
        "ibs": "0.13",
        "imposto_seletivo": "5.00",
        "tributos": "16.74",
    }
    assert (corpo["regime_apuracao"], corpo["avisos"]) == ("SN_PLENO", ["um aviso"])


def test_pedido_chega_ao_dominio_com_aliquotas_por_anexo() -> None:
    caso = CasoDeUsoFalso()

    cliente(caso).post("/api/calculos/simples-nacional", json=PEDIDO)

    operacao = caso.recebida
    assert operacao is not None
    assert (operacao.data, operacao.tipo_documento, operacao.crt) == (date(2027, 3, 15), 55, 1)
    anexos = operacao.aliquotas_efetivas.anexos
    assert anexos["I"].par.cbs == Decimal("1.1612")
    iii = anexos["III"].sem_redistribuicao_iss
    assert iii is not None
    assert (iii.cbs, iii.ibs) == (Decimal("2.3591"), None)
    assert operacao.aliquotas_efetivas.fator_r is False
    item = operacao.itens[0]
    assert (item.atividade, item.valor_imposto_seletivo, item.nbs) == (
        "01",
        Decimal("5.00"),
        "114051000",
    )


def test_dado_invalido_do_dominio_vira_422_com_mensagem() -> None:
    pedido = {**PEDIDO, "crt": 3}

    resposta = cliente(CasoDeUsoFalso()).post("/api/calculos/simples-nacional", json=pedido)

    assert resposta.status_code == 422
    assert "CRT" in resposta.json()["erro"]


def test_motor_fora_do_ar_vira_503() -> None:
    caso = CasoDeUsoFalso(MotorIndisponivel("o motor Simples Nacional não respondeu"))

    resposta = cliente(caso).post("/api/calculos/simples-nacional", json=PEDIDO)

    assert resposta.status_code == 503


def test_lista_as_atividades_na_data_pedida() -> None:
    consulta = ConsultaFalsa()

    resposta = cliente(CasoDeUsoFalso(), consulta).get("/api/atividades-simples?data=2027-03-15")

    assert resposta.status_code == 200
    assert consulta.data_pedida == date(2027, 3, 15)
    assert resposta.json() == [
        {
            "codigo": "01",
            "descricao": "Revenda",
            "anexo": "I",
            "disponivel": True,
            "tipos_de_documento": [55, 65],
        }
    ]
