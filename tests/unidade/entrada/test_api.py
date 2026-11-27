from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient

from hub_rtc.dominio.erros import ErroDoHub, MotorIndisponivel, MotorRejeitouOperacao
from hub_rtc.dominio.operacao import Operacao
from hub_rtc.dominio.resultado import ResultadoCalculo, TributosDoItem
from hub_rtc.entrada.api import criar_app

PEDIDO: dict[str, Any] = {
    "fato_gerador": "2026-10-20T10:00:00-03:00",
    "municipio": 3550308,
    "uf": "SP",
    "itens": [
        {"numero": 1, "cst": "000", "classificacao_tributaria": "000001", "base_calculo": "100.00"}
    ],
}


class CasoDeUsoFalso:
    def __init__(self, falha: ErroDoHub | None = None) -> None:
        self.falha = falha
        self.recebida: Operacao | None = None

    def executar(self, operacao: Operacao) -> ResultadoCalculo:
        self.recebida = operacao
        if self.falha:
            raise self.falha
        item = TributosDoItem(
            numero=1,
            base_calculo_ibs_cbs=Decimal("100.00"),
            cbs=Decimal("8.80"),
            ibs_uf=Decimal("0.05"),
            ibs_municipal=Decimal("0.05"),
            imposto_seletivo=Decimal("0"),
        )
        return ResultadoCalculo(itens=(item,))


def cliente(caso_de_uso: CasoDeUsoFalso) -> TestClient:
    return TestClient(criar_app(caso_de_uso))


def test_calcula_e_devolve_itens_e_totais_como_texto() -> None:
    caso_de_uso = CasoDeUsoFalso()

    resposta = cliente(caso_de_uso).post("/api/calculos/regime-regular", json=PEDIDO)

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["itens"][0]["cbs"] == "8.80"
    assert corpo["itens"][0]["ibs"] == "0.10"
    assert corpo["totais"] == {"cbs": "8.80", "ibs": "0.10", "imposto_seletivo": "0"}
    assert caso_de_uso.recebida is not None
    assert caso_de_uso.recebida.itens[0].base_calculo == Decimal("100.00")


def test_dados_fora_do_formato_do_dominio_viram_422_com_mensagem() -> None:
    pedido = {**PEDIDO, "uf": "SAO"}

    resposta = cliente(CasoDeUsoFalso()).post("/api/calculos/regime-regular", json=pedido)

    assert resposta.status_code == 422
    assert "UF" in resposta.json()["erro"]


def test_pedido_sem_campos_obrigatorios_vira_422() -> None:
    resposta = cliente(CasoDeUsoFalso()).post("/api/calculos/regime-regular", json={})

    assert resposta.status_code == 422


@pytest.mark.parametrize(
    ("falha", "status"),
    [
        (MotorRejeitouOperacao("NCM inválido"), 422),
        (MotorIndisponivel("fora do ar"), 503),
    ],
)
def test_erros_do_motor_viram_status_http_com_a_mensagem(falha: ErroDoHub, status: int) -> None:
    resposta = cliente(CasoDeUsoFalso(falha)).post("/api/calculos/regime-regular", json=PEDIDO)

    assert resposta.status_code == status
    assert resposta.json() == {"erro": str(falha)}


def test_rota_de_saude() -> None:
    assert cliente(CasoDeUsoFalso()).get("/api/saude").json() == {"status": "ok"}


def test_serve_a_tela_web_na_raiz() -> None:
    resposta = cliente(CasoDeUsoFalso()).get("/")

    assert resposta.status_code == 200
    assert "Hub RTC" in resposta.text
