"""Chamada HTTP a um motor da Receita, com os erros traduzidos para o vocabulário do Hub."""

from collections.abc import Callable

import httpx

from hub_rtc.dominio.erros import MotorIndisponivel, MotorRejeitouOperacao

PRIMEIRO_ERRO_DO_CLIENTE = 400
PRIMEIRO_ERRO_DO_SERVIDOR = 500


def _detalhe(erro: object) -> str | None:
    if not isinstance(erro, dict):
        return None
    detalhe = erro.get("detail") or erro.get("descricao") or erro.get("title")
    return str(detalhe) if detalhe else None


def mensagem_de_recusa(resposta: httpx.Response) -> str:
    """Prefere o detalhe de cada erro da lista `errors`; senão, o do corpo todo."""
    try:
        corpo = resposta.json()
    except ValueError:
        return resposta.text.strip() or f"HTTP {resposta.status_code}"
    lista = corpo.get("errors") if isinstance(corpo, dict) else None
    erros = lista or (corpo if isinstance(corpo, list) else [corpo])
    detalhes = [d for d in (_detalhe(erro) for erro in erros) if d]
    return "; ".join(detalhes) or f"HTTP {resposta.status_code}"


def requisitar(enviar: Callable[[], httpx.Response], motor: str) -> httpx.Response:
    try:
        resposta = enviar()
    except httpx.TransportError as erro:
        raise MotorIndisponivel(f"o motor {motor} não respondeu") from erro
    if resposta.status_code >= PRIMEIRO_ERRO_DO_SERVIDOR:
        raise MotorIndisponivel(f"o motor falhou (HTTP {resposta.status_code})")
    if resposta.status_code >= PRIMEIRO_ERRO_DO_CLIENTE:
        raise MotorRejeitouOperacao(mensagem_de_recusa(resposta))
    return resposta
