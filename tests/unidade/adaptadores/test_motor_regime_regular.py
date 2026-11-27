import json
from decimal import Decimal

import httpx
import pytest

from hub_rtc.adaptadores.motor_regime_regular import MotorRegimeRegular
from hub_rtc.dominio.erros import MotorIndisponivel, MotorRejeitouOperacao
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
