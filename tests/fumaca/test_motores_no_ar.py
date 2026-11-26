"""Teste de fumaça da Fase 0: os três motores oficiais respondem.

Precisa dos contêineres no ar (`docker compose up -d`). Por padrão testa o
Docker local; com HUB_RTC_HOST testa o servidor da empresa.
Rodar com: pytest -m fumaca
"""

import os

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
