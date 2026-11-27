"""Adaptador HTTP da Calculadora Regime Regular (motor oficial da Receita Federal)."""

from collections.abc import Mapping
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import uuid4

import httpx

from hub_rtc.adaptadores.http_motor import requisitar
from hub_rtc.dominio.catalogo import ClassificacaoTributaria, SituacaoTributaria
from hub_rtc.dominio.operacao import (
    AliquotasNominais,
    ImpostoSeletivoItem,
    ItemOperacao,
    Operacao,
)
from hub_rtc.dominio.resultado import MemoriaDeCalculo, ResultadoCalculo, TributosDoItem

CAMINHO_CALCULO = "/api/calculadora/regime-geral"
CAMINHO_SITUACOES = "/api/calculadora/dados-abertos/situacoes-tributarias/cbs-ibs"
VERSAO_DO_FORMATO = "0.0.1"
NOME_DO_MOTOR = "Regime Regular"

Json = Mapping[str, Any]

# (nome mostrado, grupo na resposta, chave na memória agrupada do motor)
TRIBUTOS_COM_MEMORIA = (
    ("CBS", "gCBS", "cbs"),
    ("IBS (UF)", "gIBSUF", "ibsUF"),
    ("IBS (município)", "gIBSMun", "ibsMun"),
)


def _aliquotas_para_json(aliquotas: AliquotasNominais) -> dict[str, Any]:
    json_aliquotas: dict[str, Any] = {
        "cbs": float(aliquotas.cbs),
        "ibsEstadual": float(aliquotas.ibs_estadual),
        "ibsMunicipal": float(aliquotas.ibs_municipal),
    }
    if aliquotas.imposto_seletivo is not None:
        json_aliquotas["impostoSeletivo"] = {
            "adValorem": float(aliquotas.imposto_seletivo.ad_valorem),
            "adRem": float(aliquotas.imposto_seletivo.ad_rem),
        }
    return json_aliquotas


def _seletivo_para_json(seletivo: ImpostoSeletivoItem) -> dict[str, Any]:
    json_seletivo: dict[str, Any] = {
        "cst": seletivo.cst,
        "cClassTrib": seletivo.classificacao_tributaria,
        "baseCalculo": float(seletivo.base_calculo),
    }
    if seletivo.quantidade is not None:
        json_seletivo["quantidade"] = float(seletivo.quantidade)
    if seletivo.unidade:
        json_seletivo["unidade"] = seletivo.unidade
    return json_seletivo


def _item_para_json(item: ItemOperacao) -> dict[str, Any]:
    json_item: dict[str, Any] = {
        "numero": item.numero,
        "cst": item.cst,
        "cClassTrib": item.classificacao_tributaria,
    }
    if item.base_calculo is not None:
        json_item["baseCalculo"] = float(item.base_calculo)
    if item.ncm:
        json_item["ncm"] = item.ncm
    if item.nbs:
        json_item["nbs"] = item.nbs
    if item.imposto_seletivo is not None:
        json_item["impostoSeletivo"] = _seletivo_para_json(item.imposto_seletivo)
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
    if operacao.aliquotas_nominais is not None:
        aliquotas = _aliquotas_para_json(operacao.aliquotas_nominais)
        for json_item in json_operacao["itens"]:
            json_item["aliquotasNominais"] = aliquotas
    if operacao.tipo_documento is not None:
        json_operacao["tpDoc"] = operacao.tipo_documento
    return json_operacao


def _valor(no: Json | None, *caminho: str) -> Decimal:
    """Lê um valor numérico aninhado; ausente significa que o motor não calculou (zero)."""
    for chave in caminho:
        if no is None:
            return Decimal(0)
        no = no.get(chave)
    return Decimal(0) if no is None else Decimal(str(no))


def _aliquota_efetiva(tributo: Json | None, chave_aliquota: str) -> Decimal:
    """Alíquota em %: a efetiva, quando há redução; senão a cheia."""
    reducao = (tributo or {}).get("gRed") or {}
    if "pAliqEfet" in reducao:
        return _valor(reducao, "pAliqEfet")
    return _valor(tributo, chave_aliquota)


def _memorias(calculo: Json, grupo: Json) -> tuple[MemoriaDeCalculo, ...]:
    """Reúne os textos de memória de cálculo, juntando os tributos que têm o mesmo texto.

    O motor ora traz o texto dentro de cada tributo, ora agrupado em IBSCBS.memoriaCalculo.
    """
    agrupadas = (calculo.get("IBSCBS") or {}).get("memoriaCalculo") or {}
    nomes_por_texto: dict[str, list[str]] = {}
    for nome, chave_grupo, chave_agrupada in TRIBUTOS_COM_MEMORIA:
        texto = (grupo.get(chave_grupo) or {}).get("memoriaCalculo") or agrupadas.get(
            chave_agrupada
        )
        if texto:
            nomes_por_texto.setdefault(texto, []).append(nome)
    seletivo = (calculo.get("IS") or {}).get("memoriaCalculo")
    if seletivo:
        nomes_por_texto.setdefault(seletivo, []).append("Imposto Seletivo")
    return tuple(
        MemoriaDeCalculo(", ".join(nomes), texto) for texto, nomes in nomes_por_texto.items()
    )


def _objeto_para_tributos(objeto: Json) -> TributosDoItem:
    calculo = objeto.get("tribCalc") or {}
    grupo = (calculo.get("IBSCBS") or {}).get("gIBSCBS") or {}
    return TributosDoItem(
        numero=int(objeto["nObj"]),
        base_calculo_ibs_cbs=_valor(grupo, "vBC"),
        cbs=_valor(grupo, "gCBS", "vCBS"),
        ibs_uf=_valor(grupo, "gIBSUF", "vIBSUF"),
        ibs_municipal=_valor(grupo, "gIBSMun", "vIBSMun"),
        imposto_seletivo=_valor(calculo, "IS", "vIS"),
        aliquota_cbs=_aliquota_efetiva(grupo.get("gCBS"), "pCBS"),
        aliquota_ibs_uf=_aliquota_efetiva(grupo.get("gIBSUF"), "pIBSUF"),
        aliquota_ibs_municipal=_aliquota_efetiva(grupo.get("gIBSMun"), "pIBSMun"),
        memorias_de_calculo=_memorias(calculo, grupo),
    )


def _situacao_do_motor(situacao: Json) -> SituacaoTributaria:
    return SituacaoTributaria(
        codigo=situacao["codigo"],
        descricao=situacao["descricao"],
        classificacoes=tuple(
            ClassificacaoTributaria(c["codigo"], c["descricao"])
            for c in situacao.get("classificacoesTributarias", [])
        ),
    )


class MotorRegimeRegular:
    """Cumpre as portas de cálculo e de catálogo conversando com o mesmo motor."""

    def __init__(self, cliente: httpx.Client) -> None:
        self._cliente = cliente

    def calcular(self, operacao: Operacao) -> ResultadoCalculo:
        resposta = requisitar(
            lambda: self._cliente.post(CAMINHO_CALCULO, json=_operacao_para_json(operacao)),
            NOME_DO_MOTOR,
        )
        objetos = resposta.json().get("objetos", [])
        return ResultadoCalculo(
            itens=tuple(_objeto_para_tributos(o) for o in objetos),
            simulado=any(o.get("calculoSimulado") for o in objetos),
        )

    def situacoes_tributarias(self, data: date) -> tuple[SituacaoTributaria, ...]:
        resposta = requisitar(
            lambda: self._cliente.get(CAMINHO_SITUACOES, params={"data": data.isoformat()}),
            NOME_DO_MOTOR,
        )
        return tuple(_situacao_do_motor(s) for s in resposta.json())
