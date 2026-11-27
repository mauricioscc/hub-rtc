"""Adaptador HTTP da Calculadora Regime Regular (motor oficial da Receita Federal)."""

from collections.abc import Mapping
from decimal import Decimal
from typing import Any
from uuid import uuid4

import httpx

from hub_rtc.dominio.erros import MotorIndisponivel, MotorRejeitouOperacao
from hub_rtc.dominio.operacao import ItemOperacao, Operacao
from hub_rtc.dominio.resultado import ResultadoCalculo, TributosDoItem

CAMINHO_CALCULO = "/api/calculadora/regime-geral"
VERSAO_DO_FORMATO = "0.0.1"
PRIMEIRO_ERRO_DO_CLIENTE = 400
PRIMEIRO_ERRO_DO_SERVIDOR = 500


def _item_para_json(item: ItemOperacao) -> dict[str, Any]:
    json_item: dict[str, Any] = {
        "numero": item.numero,
        "cst": item.cst,
        "cClassTrib": item.classificacao_tributaria,
        "baseCalculo": float(item.base_calculo),
    }
    if item.ncm:
        json_item["ncm"] = item.ncm
    return json_item


def _operacao_para_json(operacao: Operacao) -> dict[str, Any]:
    json_operacao: dict[str, Any] = {
        "id": uuid4().hex,
        "versao": VERSAO_DO_FORMATO,
        "dhFatoGerador": operacao.fato_gerador.isoformat(),
        "municipio": operacao.municipio,
        "uf": operacao.uf,
        "itens": [_item_para_json(item) for item in operacao.itens],
    }
    if operacao.tipo_documento is not None:
        json_operacao["tpDoc"] = operacao.tipo_documento
    return json_operacao


def _valor(no: Mapping[str, Any] | None, *caminho: str) -> Decimal:
    """Lê um valor monetário aninhado; ausente significa que o motor não calculou (zero)."""
    for chave in caminho:
        if no is None:
            return Decimal(0)
        no = no.get(chave)
    return Decimal(0) if no is None else Decimal(str(no))


def _objeto_para_tributos(objeto: Mapping[str, Any]) -> TributosDoItem:
    calculo = objeto.get("tribCalc") or {}
    grupo = (calculo.get("IBSCBS") or {}).get("gIBSCBS") or {}
    return TributosDoItem(
        numero=int(objeto["nObj"]),
        base_calculo_ibs_cbs=_valor(grupo, "vBC"),
        cbs=_valor(grupo, "gCBS", "vCBS"),
        ibs_uf=_valor(grupo, "gIBSUF", "vIBSUF"),
        ibs_municipal=_valor(grupo, "gIBSMun", "vIBSMun"),
        imposto_seletivo=_valor(calculo, "IS", "vIS"),
    )


def _mensagem_de_recusa(resposta: httpx.Response) -> str:
    try:
        corpo = resposta.json()
    except ValueError:
        return resposta.text.strip() or f"HTTP {resposta.status_code}"
    erros = corpo if isinstance(corpo, list) else [corpo]
    detalhes = [
        str(erro.get("detail") or erro.get("descricao") or erro.get("title"))
        for erro in erros
        if isinstance(erro, dict)
    ]
    return "; ".join(detalhes) or f"HTTP {resposta.status_code}"


class MotorRegimeRegular:
    def __init__(self, cliente: httpx.Client) -> None:
        self._cliente = cliente

    def calcular(self, operacao: Operacao) -> ResultadoCalculo:
        resposta = self._enviar(_operacao_para_json(operacao))
        objetos = resposta.json().get("objetos", [])
        return ResultadoCalculo(itens=tuple(_objeto_para_tributos(o) for o in objetos))

    def _enviar(self, corpo: dict[str, Any]) -> httpx.Response:
        try:
            resposta = self._cliente.post(CAMINHO_CALCULO, json=corpo)
        except httpx.TransportError as erro:
            raise MotorIndisponivel("o motor Regime Regular não respondeu") from erro
        if resposta.status_code >= PRIMEIRO_ERRO_DO_SERVIDOR:
            raise MotorIndisponivel(f"o motor falhou (HTTP {resposta.status_code})")
        if resposta.status_code >= PRIMEIRO_ERRO_DO_CLIENTE:
            raise MotorRejeitouOperacao(_mensagem_de_recusa(resposta))
        return resposta
