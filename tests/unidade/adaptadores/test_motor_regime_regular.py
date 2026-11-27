import json
from dataclasses import replace
from datetime import date
from decimal import Decimal

import httpx
import pytest

from hub_rtc.adaptadores.motor_regime_regular import MotorRegimeRegular
from hub_rtc.dominio.erros import MotorIndisponivel, MotorRejeitouOperacao
from hub_rtc.dominio.operacao import AliquotasNominais
from tests.unidade.dominio.test_operacao import um_item, uma_operacao

RESPOSTA_DO_MOTOR = {
    "objetos": [
        {
            "nObj": 1,
            "tribCalc": {
                "IS": {"vIS": "47.30"},
                "IBSCBS": {
                    "gIBSCBS": {
                        "vBC": "247.30",
                        "gIBSUF": {"vIBSUF": "0.12"},
                        "gIBSMun": {"vIBSMun": "0.13"},
                        "gCBS": {"vCBS": "20.77"},
                    }
                },
            },
        },
        {"nObj": 2, "tribCalc": {"IBSCBS": {"CST": "410"}}},
    ]
}


def motor_respondendo(
    status: int, corpo: object, capturadas: list[httpx.Request] | None = None
) -> MotorRegimeRegular:
    def responder(requisicao: httpx.Request) -> httpx.Response:
        if capturadas is not None:
            capturadas.append(requisicao)
        return httpx.Response(status, json=corpo)

    cliente = httpx.Client(base_url="http://motor", transport=httpx.MockTransport(responder))
    return MotorRegimeRegular(cliente)


def test_envia_a_operacao_no_formato_do_motor() -> None:
    capturadas: list[httpx.Request] = []
    motor = motor_respondendo(200, RESPOSTA_DO_MOTOR, capturadas)

    motor.calcular(uma_operacao((um_item(ncm="84713012"),)))

    requisicao = capturadas[0]
    corpo = json.loads(requisicao.content)
    assert requisicao.url.path == "/api/calculadora/regime-geral"
    assert corpo["id"]
    assert corpo["versao"]
    assert corpo["dhFatoGerador"] == "2026-10-20T10:00:00+00:00"
    assert corpo["municipio"] == 3550308
    assert corpo["uf"] == "SP"
    assert "tpDoc" not in corpo
    assert corpo["itens"] == [
        {
            "numero": 1,
            "cst": "000",
            "cClassTrib": "000001",
            "baseCalculo": 25.0,
            "ncm": "84713012",
        }
    ]


def test_traduz_a_resposta_para_o_resultado_do_hub() -> None:
    motor = motor_respondendo(200, RESPOSTA_DO_MOTOR)

    resultado = motor.calcular(uma_operacao((um_item(numero=1), um_item(numero=2))))

    primeiro, segundo = resultado.itens
    assert primeiro.base_calculo_ibs_cbs == Decimal("247.30")
    assert primeiro.cbs == Decimal("20.77")
    assert primeiro.ibs_uf == Decimal("0.12")
    assert primeiro.ibs_municipal == Decimal("0.13")
    assert primeiro.imposto_seletivo == Decimal("47.30")
    assert segundo.cbs == Decimal(0)  # item sem grupo de cálculo (ex.: isento)


def test_recusa_do_motor_vira_erro_com_a_mensagem_dele() -> None:
    motor = motor_respondendo(422, {"title": "Erro", "detail": "NCM inválido para o CST"})

    with pytest.raises(MotorRejeitouOperacao, match="NCM inválido para o CST"):
        motor.calcular(uma_operacao((um_item(),)))


def test_recusa_com_lista_de_erros_junta_os_detalhes() -> None:
    corpo = [{"detail": "primeiro problema"}, {"detail": "segundo problema"}]
    motor = motor_respondendo(400, corpo)

    with pytest.raises(MotorRejeitouOperacao, match="primeiro problema; segundo problema"):
        motor.calcular(uma_operacao((um_item(),)))


def test_erro_interno_do_motor_vira_indisponivel() -> None:
    motor = motor_respondendo(500, {"detail": "boom"})

    with pytest.raises(MotorIndisponivel):
        motor.calcular(uma_operacao((um_item(),)))


def test_motor_fora_do_ar_vira_indisponivel() -> None:
    def derrubar(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("recusou")

    cliente = httpx.Client(base_url="http://motor", transport=httpx.MockTransport(derrubar))

    with pytest.raises(MotorIndisponivel):
        MotorRegimeRegular(cliente).calcular(uma_operacao((um_item(),)))


RESPOSTA_COM_REDUCAO_E_MEMORIA = {
    "objetos": [
        {
            "nObj": 1,
            "tribCalc": {
                "IBSCBS": {
                    "gIBSCBS": {
                        "vBC": "100.00",
                        "gIBSUF": {"pIBSUF": "0.10", "vIBSUF": "0.04"},
                        "gIBSMun": {"pIBSMun": "0.00", "vIBSMun": "0.00"},
                        "gCBS": {
                            "pCBS": "0.90",
                            "gRed": {"pRedAliq": "60.00", "pAliqEfet": "0.36"},
                            "vCBS": "0.36",
                        },
                    },
                    "memoriaCalculo": {
                        "cbs": "texto igual",
                        "ibsUF": "texto igual",
                        "ibsMun": "outro",
                    },
                },
                "IS": {"vIS": "5.00", "pIS": "13.00", "memoriaCalculo": "texto do seletivo"},
            },
        }
    ]
}


def test_traduz_aliquotas_usando_a_efetiva_quando_ha_reducao() -> None:
    motor = motor_respondendo(200, RESPOSTA_COM_REDUCAO_E_MEMORIA)

    item = motor.calcular(uma_operacao((um_item(),))).itens[0]

    assert item.aliquota_cbs == Decimal("0.36")  # efetiva, não a cheia de 0.90
    assert item.aliquota_ibs_uf == Decimal("0.10")
    assert item.aliquota_ibs_municipal == Decimal("0.00")


def test_junta_memorias_de_calculo_iguais_e_inclui_a_do_seletivo() -> None:
    motor = motor_respondendo(200, RESPOSTA_COM_REDUCAO_E_MEMORIA)

    memorias = motor.calcular(uma_operacao((um_item(),))).itens[0].memorias_de_calculo

    assert [(m.tributos, m.texto) for m in memorias] == [
        ("CBS, IBS (UF)", "texto igual"),
        ("IBS (município)", "outro"),
        ("Imposto Seletivo", "texto do seletivo"),
    ]


def test_le_a_memoria_de_dentro_do_proprio_tributo() -> None:
    corpo = {
        "objetos": [
            {
                "nObj": 1,
                "tribCalc": {
                    "IBSCBS": {"gIBSCBS": {"gCBS": {"vCBS": "1.00", "memoriaCalculo": "da CBS"}}}
                },
            }
        ]
    }

    memorias = motor_respondendo(200, corpo).calcular(uma_operacao((um_item(),))).itens[0]

    assert [(m.tributos, m.texto) for m in memorias.memorias_de_calculo] == [("CBS", "da CBS")]


CATALOGO_DO_MOTOR = [
    {
        "id": 1,
        "codigo": "000",
        "descricao": "Tributação integral",
        "classificacoesTributarias": [
            {"codigo": "000001", "descricao": "Situações tributadas integralmente"}
        ],
    },
    {"id": 2, "codigo": "400", "descricao": "Isenção", "classificacoesTributarias": []},
]


def test_consulta_situacoes_tributarias_na_data_informada() -> None:
    capturadas: list[httpx.Request] = []
    motor = motor_respondendo(200, CATALOGO_DO_MOTOR, capturadas)

    situacoes = motor.situacoes_tributarias(date(2026, 10, 20))

    requisicao = capturadas[0]
    assert requisicao.url.path == "/api/calculadora/dados-abertos/situacoes-tributarias/cbs-ibs"
    assert requisicao.url.params["data"] == "2026-10-20"
    assert [s.codigo for s in situacoes] == ["000", "400"]
    assert situacoes[0].descricao == "Tributação integral"
    assert situacoes[0].classificacoes[0].codigo == "000001"
    assert situacoes[1].classificacoes == ()


def test_consulta_de_situacoes_tambem_traduz_motor_fora_do_ar() -> None:
    with pytest.raises(MotorIndisponivel):
        motor_respondendo(503, {}).situacoes_tributarias(date(2026, 10, 20))


def test_envia_as_aliquotas_nominais_em_cada_item() -> None:
    capturadas: list[httpx.Request] = []
    motor = motor_respondendo(200, RESPOSTA_DO_MOTOR, capturadas)
    operacao = replace(
        uma_operacao((um_item(numero=1), um_item(numero=2))),
        aliquotas_nominais=AliquotasNominais(Decimal("8.8"), Decimal("8.85"), Decimal("8.85")),
    )

    motor.calcular(operacao)

    itens = json.loads(capturadas[0].content)["itens"]
    esperado = {"cbs": 8.8, "ibsEstadual": 8.85, "ibsMunicipal": 8.85}
    assert [item["aliquotasNominais"] for item in itens] == [esperado, esperado]


def test_sem_aliquotas_nominais_o_campo_nao_vai_no_pedido() -> None:
    capturadas: list[httpx.Request] = []
    motor = motor_respondendo(200, RESPOSTA_DO_MOTOR, capturadas)

    motor.calcular(uma_operacao((um_item(),)))

    assert "aliquotasNominais" not in json.loads(capturadas[0].content)["itens"][0]


def test_resultado_indica_quando_o_calculo_foi_simulado() -> None:
    simulado = {"objetos": [{"nObj": 1, "calculoSimulado": True, "tribCalc": {}}]}
    normal = {"objetos": [{"nObj": 1, "calculoSimulado": False, "tribCalc": {}}]}

    assert motor_respondendo(200, simulado).calcular(uma_operacao((um_item(),))).simulado
    assert not motor_respondendo(200, normal).calcular(uma_operacao((um_item(),))).simulado
