import json
from datetime import date
from decimal import Decimal

import httpx
import pytest

from hub_rtc.adaptadores.motor_simples_nacional import MotorSimplesNacional
from hub_rtc.dominio.erros import MotorIndisponivel, MotorRejeitouOperacao
from hub_rtc.dominio.simples_nacional import AliquotasEfetivas, AnexoAliquotas, ParAliquotas
from tests.unidade.dominio.test_simples_nacional import um_item, uma_operacao

CALCULADO = {
    "oper": {"data": "2027-03-15", "regimeApuracao": "SN_PLENO"},
    "resolucaoAliquotas": {
        "avisos": ["aviso da operação"],
        "itens": [{"numero": 1, "anexoAplicado": "I"}],
    },
    "objetos": [
        {
            "nObj": 1,
            "estadoItem": "CALCULADO",
            "tribCalc": {
                "vRBSNitem": "1000.00",
                "vBC": "1000.00",
                "pIBSSN": "0.0129",
                "vIBSSN": "0.13",
                "pCBSSN": "1.1612",
                "vCBSSN": "11.61",
                "IS": {"valor": "5.00"},
                "memoriaCalculo": {"cbs": "texto igual", "ibs": "texto igual"},
            },
        }
    ],
}
NAO_CALCULADO = {
    "oper": {"regimeApuracao": "SN_PLENO"},
    "objetos": [
        {
            "nObj": 1,
            "estadoItem": "NAO_CALCULADO",
            "motivoEstado": {"codigo": "X", "descricao": "atividade '99' não existe"},
            "tribCalc": {"vRBSNitem": "1000.00"},
        },
        {
            "nObj": 2,
            "estadoItem": "INCONSISTENCIA_ENTRADA",
            "erros": [{"detail": "cClassTrib incompatível"}, {"detail": "outro problema"}],
        },
    ],
}


def motor_respondendo(
    status: int, corpo: object, capturadas: list[httpx.Request] | None = None
) -> MotorSimplesNacional:
    def responder(requisicao: httpx.Request) -> httpx.Response:
        if capturadas is not None:
            capturadas.append(requisicao)
        return httpx.Response(status, json=corpo)

    cliente = httpx.Client(base_url="http://motor", transport=httpx.MockTransport(responder))
    return MotorSimplesNacional(cliente)


def test_envia_a_operacao_no_formato_do_motor() -> None:
    capturadas: list[httpx.Request] = []
    aliquotas = AliquotasEfetivas(
        anexos={
            "I": AnexoAliquotas(ParAliquotas(Decimal("1.1612"), Decimal("0.0129"))),
            "III": AnexoAliquotas(
                ParAliquotas(Decimal("2.3874"), Decimal("0.0263")),
                sem_redistribuicao_iss=ParAliquotas(Decimal("2.3591"), None),
            ),
        },
        fator_r=False,
    )
    item = um_item(ncm="22030000", valor_imposto_seletivo=Decimal("5.00"))

    motor_respondendo(200, CALCULADO, capturadas).calcular(
        uma_operacao(aliquotas_efetivas=aliquotas, itens=(item,))
    )

    requisicao = capturadas[0]
    corpo = json.loads(requisicao.content)
    assert requisicao.url.path == "/api/calculadora/observabilidade/simples-nacional/nao-assistido"
    assert corpo["id"]
    assert (corpo["versao"], corpo["data"], corpo["tpDoc"], corpo["CRT"]) == (
        "3.0.0",
        "2027-03-15",
        "55",
        "1",
    )
    assert corpo["aliquotasEfetivas"] == {
        "fatorR": False,
        "impedimentoSublimite": False,
        "anexoI": {"pCBSSN": "1.1612", "pIBSSN": "0.0129"},
        "anexoIII": {
            "pCBSSN": "2.3874",
            "pIBSSN": "0.0263",
            "semRedistribuicaoISS": {"pCBSSN": "2.3591", "pIBSSN": None},
        },
    }
    assert corpo["itens"] == [
        {
            "numero": 1,
            "cAtivSN": "01",
            "cClassTrib": "000001",
            "baseCalculo": "1000.00",
            "valorImpostoSeletivo": "5.00",
            "ncm": "22030000",
        }
    ]


def test_sem_fator_r_o_campo_nao_vai_no_pedido() -> None:
    capturadas: list[httpx.Request] = []

    motor_respondendo(200, CALCULADO, capturadas).calcular(uma_operacao())

    assert "fatorR" not in json.loads(capturadas[0].content)["aliquotasEfetivas"]


def test_traduz_o_item_calculado() -> None:
    resultado = motor_respondendo(200, CALCULADO).calcular(uma_operacao())

    item = resultado.itens[0]
    assert item.situacao == "CALCULADO"
    assert (item.receita_bruta, item.base_calculo) == (Decimal("1000.00"), Decimal("1000.00"))
    assert (item.aliquota_cbs, item.aliquota_ibs) == (Decimal("1.1612"), Decimal("0.0129"))
    assert (item.cbs, item.ibs, item.imposto_seletivo) == (
        Decimal("11.61"),
        Decimal("0.13"),
        Decimal("5.00"),
    )
    assert item.anexo == "I"
    assert [(m.tributos, m.texto) for m in item.memorias_de_calculo] == [
        ("CBS, IBS", "texto igual")
    ]
    assert resultado.regime_apuracao == "SN_PLENO"
    assert resultado.avisos == ("aviso da operação",)
    assert resultado.total_tributos == Decimal("16.74")


def test_item_nao_calculado_traz_a_mensagem_do_motor() -> None:
    primeiro, segundo = motor_respondendo(200, NAO_CALCULADO).calcular(uma_operacao()).itens

    assert primeiro.situacao == "NAO_CALCULADO"
    assert primeiro.mensagens == ("atividade '99' não existe",)
    assert primeiro.cbs == Decimal(0)
    assert segundo.situacao == "INCONSISTENCIA_ENTRADA"
    assert segundo.mensagens == ("cClassTrib incompatível", "outro problema")


def test_crt_2_sem_ibs_no_calculo_vale_zero() -> None:
    tributos = {"pCBSSN": "1.16", "vCBSSN": "11.61"}
    corpo = {"objetos": [{"nObj": 1, "estadoItem": "CALCULADO", "tribCalc": tributos}]}

    item = motor_respondendo(200, corpo).calcular(uma_operacao(crt=2)).itens[0]

    assert (item.cbs, item.ibs) == (Decimal("11.61"), Decimal(0))


def test_recusa_da_operacao_mostra_os_detalhes_dos_erros() -> None:
    corpo = {"title": "Erros", "errors": [{"detail": "tpDoc não suportado"}]}

    with pytest.raises(MotorRejeitouOperacao, match="tpDoc não suportado"):
        motor_respondendo(422, corpo).calcular(uma_operacao())


def test_motor_com_falha_ou_fora_do_ar_vira_indisponivel() -> None:
    with pytest.raises(MotorIndisponivel, match="HTTP 503"):
        motor_respondendo(503, {}).calcular(uma_operacao())

    def derrubar(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("recusou")

    cliente = httpx.Client(base_url="http://motor", transport=httpx.MockTransport(derrubar))
    with pytest.raises(MotorIndisponivel, match="Simples Nacional"):
        MotorSimplesNacional(cliente).calcular(uma_operacao())


def test_lista_as_atividades_da_data() -> None:
    capturadas: list[httpx.Request] = []
    corpo = [
        {
            "codigo": "01",
            "descricao": "Revenda de mercadorias",
            "rotuloAnexo": "I",
            "disponivel": True,
            "tpDocsAdmissiveis": ["55", "65"],
        },
        {
            "codigo": "09",
            "descricao": "Serviços",
            "rotuloAnexo": "III ou V",
            "disponivel": False,
            "tpDocsAdmissiveis": [],
        },
    ]

    atividades = motor_respondendo(200, corpo, capturadas).atividades(date(2027, 3, 15))

    assert capturadas[0].url.path == "/api/calculadora/simples-nacional/atividades"
    assert capturadas[0].url.params["data"] == "2027-03-15"
    assert [(a.codigo, a.anexo, a.disponivel) for a in atividades] == [
        ("01", "I", True),
        ("09", "III ou V", False),
    ]
    assert atividades[0].tipos_de_documento == (55, 65)
