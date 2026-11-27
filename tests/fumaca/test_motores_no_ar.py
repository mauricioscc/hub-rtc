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
