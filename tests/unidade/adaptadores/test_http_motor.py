import httpx
import pytest

from hub_rtc.adaptadores.http_motor import requisitar
from hub_rtc.dominio.erros import MotorIndisponivel, MotorRejeitouOperacao


def resposta(status: int, corpo: object) -> httpx.Response:
    return httpx.Response(status, json=corpo)


def test_resposta_boa_e_devolvida() -> None:
    assert requisitar(lambda: resposta(200, {"ok": True}), "X").json() == {"ok": True}


def test_recusa_usa_o_detalhe_de_cada_erro_da_lista_errors() -> None:
    corpo = {
        "title": "Erros no processamento",
        "detail": "O cálculo contém 2 erro(s).",
        "errors": [{"detail": "primeiro"}, {"detail": "segundo"}],
    }

    with pytest.raises(MotorRejeitouOperacao, match="primeiro; segundo"):
        requisitar(lambda: resposta(422, corpo), "X")


def test_recusa_sem_lista_usa_o_detalhe_geral() -> None:
    with pytest.raises(MotorRejeitouOperacao, match="só o geral"):
        requisitar(lambda: resposta(422, {"detail": "só o geral"}), "X")


def test_erro_do_servidor_vira_indisponivel() -> None:
    with pytest.raises(MotorIndisponivel, match="HTTP 502"):
        requisitar(lambda: resposta(502, {}), "X")


def test_falha_de_rede_vira_indisponivel_com_o_nome_do_motor() -> None:
    def derrubar() -> httpx.Response:
        raise httpx.ConnectError("recusou")

    with pytest.raises(MotorIndisponivel, match="Simples Nacional"):
        requisitar(derrubar, "Simples Nacional")
