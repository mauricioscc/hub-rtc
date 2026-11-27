"""Teste de fumaça da Fase 0: os três motores oficiais respondem.

Precisa dos contêineres no ar (`docker compose up -d`). Por padrão testa o
Docker local; com HUB_RTC_HOST testa o servidor da empresa.
Rodar com: pytest -m fumaca
"""

import os
from decimal import Decimal

import httpx
import pytest

from hub_rtc.configuracao import EnderecosMotores

pytestmark = pytest.mark.fumaca

TEMPO_LIMITE_SEGUNDOS = 10
ENDERECOS = EnderecosMotores.do_ambiente(os.environ)


@pytest.mark.parametrize(
    "url",
    [
        pytest.param(f"{ENDERECOS.regime_regular}/api/swagger-ui.html", id="regime-regular"),
        pytest.param(f"{ENDERECOS.simples_nacional}/api/versao", id="simples-nacional"),
        pytest.param(f"{ENDERECOS.gerador_danfse}/health/ready", id="gerador-danfse"),
    ],
)
def test_motor_responde(url: str) -> None:
    resposta = httpx.get(url, timeout=TEMPO_LIMITE_SEGUNDOS, follow_redirects=True)

    assert resposta.status_code == httpx.codes.OK


def test_regime_regular_consulta_o_banco_oficial() -> None:
    """Prova que o banco gerado pelo Flyway foi montado e é lido."""
    url = f"{ENDERECOS.regime_regular}/api/calculadora/dados-abertos/situacoes-tributarias/cbs-ibs"

    resposta = httpx.get(url, params={"data": "2027-01-01"}, timeout=TEMPO_LIMITE_SEGUNDOS)

    assert resposta.status_code == httpx.codes.OK
    assert resposta.json(), "a lista de CST veio vazia: o banco oficial não foi carregado"


def test_hub_calcula_com_o_motor_real() -> None:
    """Ponta a ponta: Hub -> motor oficial. Os totais do Hub fecham com a soma dos itens."""
    pedido = {
        "fato_gerador": "2026-10-20T10:00:00-03:00",
        "municipio": 3550308,
        "uf": "SP",
        "itens": [
            {
                "numero": 1,
                "cst": "000",
                "classificacao_tributaria": "000001",
                "base_calculo": "100.00",
                "ncm": "84713012",
            }
        ],
    }

    resposta = httpx.post(
        f"{ENDERECOS.hub}/api/calculos/regime-regular", json=pedido, timeout=TEMPO_LIMITE_SEGUNDOS
    )

    assert resposta.status_code == httpx.codes.OK, resposta.text
    corpo = resposta.json()
    assert Decimal(corpo["totais"]["cbs"]) > 0
    assert corpo["totais"]["cbs"] == corpo["itens"][0]["cbs"]


def test_hub_lista_situacoes_tributarias_com_classificacoes() -> None:
    resposta = httpx.get(
        f"{ENDERECOS.hub}/api/situacoes-tributarias",
        params={"data": "2026-10-20"},
        timeout=TEMPO_LIMITE_SEGUNDOS,
    )

    assert resposta.status_code == httpx.codes.OK
    integral = next(s for s in resposta.json() if s["codigo"] == "000")
    assert "000001" in [c["codigo"] for c in integral["classificacoes"]]


def test_hub_calcula_a_partir_de_2027_com_aliquotas_nominais() -> None:
    pedido = {
        "fato_gerador": "2027-01-05T12:00:00-03:00",
        "municipio": 3304557,
        "uf": "RJ",
        "aliquotas_nominais": {"cbs": "8.8", "ibs_estadual": "8.85", "ibs_municipal": "8.85"},
        "itens": [
            {
                "numero": 1,
                "cst": "000",
                "classificacao_tributaria": "000001",
                "base_calculo": "100.00",
            }
        ],
    }

    resposta = httpx.post(
        f"{ENDERECOS.hub}/api/calculos/regime-regular", json=pedido, timeout=TEMPO_LIMITE_SEGUNDOS
    )

    assert resposta.status_code == httpx.codes.OK, resposta.text
    corpo = resposta.json()
    assert corpo["simulado"] is True
    assert corpo["totais"] == {"cbs": "8.80", "ibs": "17.70", "imposto_seletivo": "0"}


def test_hub_calcula_o_imposto_seletivo_com_o_motor_real() -> None:
    """188 x 10% + 0,50 x 1 unidade = 19,30; a base de CBS/IBS vira 188 + 19,30."""
    pedido = {
        "fato_gerador": "2027-01-05T12:00:00-03:00",
        "municipio": 3304557,
        "uf": "RJ",
        "aliquotas_nominais": {
            "cbs": "8.8",
            "ibs_estadual": "8.85",
            "ibs_municipal": "8.85",
            "imposto_seletivo": {"ad_valorem": "10", "ad_rem": "0.5"},
        },
        "itens": [
            {
                "numero": 1,
                "cst": "000",
                "classificacao_tributaria": "000001",
                "ncm": "24021000",
                "imposto_seletivo": {
                    "cst": "000",
                    "classificacao_tributaria": "000001",
                    "base_calculo": "188.00",
                    "quantidade": "1",
                    "unidade": "UN",
                },
            }
        ],
    }

    resposta = httpx.post(
        f"{ENDERECOS.hub}/api/calculos/regime-regular", json=pedido, timeout=TEMPO_LIMITE_SEGUNDOS
    )

    assert resposta.status_code == httpx.codes.OK, resposta.text
    corpo = resposta.json()
    assert corpo["totais"]["imposto_seletivo"] == "19.30"
    assert corpo["itens"][0]["base_calculo"] == "207.30"
    assert "Imposto Seletivo" in [m["tributos"] for m in corpo["itens"][0]["memorias"]]


def test_hub_envia_nbs_e_tipo_de_documento_e_repassa_as_regras_do_motor() -> None:
    item = {
        "numero": 1,
        "cst": "000",
        "classificacao_tributaria": "000001",
        "base_calculo": "100.00",
    }
    pedido = {
        "fato_gerador": "2026-10-20T10:00:00-03:00",
        "municipio": 3304557,
        "uf": "RJ",
        "itens": [item],
    }
    url = f"{ENDERECOS.hub}/api/calculos/regime-regular"

    def calcular(**alteracoes: object) -> httpx.Response:
        corpo = {**pedido, **alteracoes}
        return httpx.post(url, json=corpo, timeout=TEMPO_LIMITE_SEGUNDOS)

    com_nbs = [{**item, "nbs": "109052100"}]
    com_ncm = [{**item, "ncm": "84713012"}]

    assert calcular(itens=com_nbs).status_code == httpx.codes.OK
    nfe_com_ncm = calcular(tipo_documento=55, itens=com_ncm)
    assert nfe_com_ncm.status_code == httpx.codes.OK, nfe_com_ncm.text
    assert nfe_com_ncm.json()["totais"]["cbs"] == "0.90"
    nfe_com_nbs = calcular(tipo_documento=55, itens=com_nbs)
    assert nfe_com_nbs.status_code == httpx.codes.UNPROCESSABLE_ENTITY
    assert "NBS não permitida" in nfe_com_nbs.json()["erro"]
    desconhecido = calcular(tipo_documento=99)
    assert desconhecido.status_code == httpx.codes.UNPROCESSABLE_ENTITY
    assert "tpDoc" in desconhecido.json()["erro"]


ALIQUOTAS_SIMPLES = {
    "fator_r": False,
    "anexos": {
        "I": {"cbs": "1.1612", "ibs": "0.0129"},
        "II": {"cbs": "1.2", "ibs": "0.02"},
        "III": {
            "cbs": "2.3874",
            "ibs": "0.0263",
            "sem_redistribuicao_iss": {"cbs": "2.3591", "ibs": "0.0260"},
        },
    },
}


def _simples(itens: list[dict[str, object]], **alteracoes: object) -> httpx.Response:
    pedido = {
        "data": "2027-03-15",
        "tipo_documento": 55,
        "crt": 1,
        "aliquotas_efetivas": ALIQUOTAS_SIMPLES,
        "itens": itens,
        **alteracoes,
    }
    return httpx.post(
        f"{ENDERECOS.hub}/api/calculos/simples-nacional", json=pedido, timeout=TEMPO_LIMITE_SEGUNDOS
    )


def _item_simples(**alteracoes: object) -> dict[str, object]:
    item = {
        "numero": 1,
        "atividade": "01",
        "classificacao_tributaria": "000001",
        "base_calculo": "1000.00",
        "ncm": "22030000",
    }
    return {**item, **alteracoes}


def test_hub_calcula_o_simples_nacional_com_o_motor_real() -> None:
    """Anexo I: R$ 1.000 x 1,1612% de CBS = 11,61 e x 0,0129% de IBS = 0,13."""
    resposta = _simples([_item_simples()])

    assert resposta.status_code == httpx.codes.OK, resposta.text
    corpo = resposta.json()
    assert corpo["regime_apuracao"] == "SN_PLENO"
    assert corpo["itens"][0]["situacao"] == "CALCULADO"
    assert corpo["itens"][0]["anexo"] == "I"
    assert corpo["totais"] == {
        "cbs": "11.61",
        "ibs": "0.13",
        "imposto_seletivo": "0.00",
        "tributos": "11.74",
    }


def test_simples_com_crt_2_nao_calcula_ibs() -> None:
    corpo = _simples([_item_simples()], crt=2).json()

    assert corpo["totais"]["ibs"] == "0"
    assert corpo["totais"]["cbs"] == "11.61"


def test_simples_item_recusado_pelo_motor_traz_a_mensagem_e_nao_derruba_o_resto() -> None:
    itens = [_item_simples(), _item_simples(numero=2, atividade="99")]

    corpo = _simples(itens).json()

    assert [i["situacao"] for i in corpo["itens"]] == ["CALCULADO", "NAO_CALCULADO"]
    assert "99" in corpo["itens"][1]["mensagens"][0]
    assert corpo["totais"]["cbs"] == "11.61"


def test_simples_sem_a_aliquota_do_anexo_marca_o_item_como_inconsistente() -> None:
    corpo = _simples([_item_simples()], aliquotas_efetivas={"anexos": {}}).json()

    item = corpo["itens"][0]
    assert item["situacao"] == "INCONSISTENCIA_ENTRADA"
    assert "pCBSSN do anexo I" in item["mensagens"][0]
    assert corpo["totais"]["tributos"] == "0"


def test_simples_antes_da_vigencia_devolve_422_com_o_motivo_do_motor() -> None:
    resposta = _simples([_item_simples()], data="2026-03-15")

    assert resposta.status_code == httpx.codes.UNPROCESSABLE_ENTITY
    assert "não suportado" in resposta.json()["erro"]


def test_hub_lista_as_atividades_do_simples_nacional() -> None:
    resposta = httpx.get(
        f"{ENDERECOS.hub}/api/atividades-simples",
        params={"data": "2027-03-15"},
        timeout=TEMPO_LIMITE_SEGUNDOS,
    )

    assert resposta.status_code == httpx.codes.OK
    primeira = resposta.json()[0]
    assert primeira["codigo"] == "01"
    assert primeira["anexo"] == "I"
    assert 55 in primeira["tipos_de_documento"]
