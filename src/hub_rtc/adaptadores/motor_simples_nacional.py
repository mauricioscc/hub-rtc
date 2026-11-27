"""Adaptador HTTP da Calculadora Simples Nacional (motor oficial da Receita Federal)."""

from collections.abc import Mapping
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import uuid4

import httpx

from hub_rtc.adaptadores.http_motor import requisitar
from hub_rtc.dominio.catalogo import AtividadeSimples
from hub_rtc.dominio.resultado import MemoriaDeCalculo
from hub_rtc.dominio.resultado_simples import ItemSimplesCalculado, ResultadoSimples
from hub_rtc.dominio.simples_nacional import (
    AliquotasEfetivas,
    ItemSimples,
    OperacaoSimples,
    ParAliquotas,
)

CAMINHO_CALCULO = "/api/calculadora/observabilidade/simples-nacional/nao-assistido"
CAMINHO_ATIVIDADES = "/api/calculadora/simples-nacional/atividades"
VERSAO_DO_FORMATO = "3.0.0"
NOME_DO_MOTOR = "Simples Nacional"

Json = Mapping[str, Any]


def _texto(valor: Decimal | None) -> str | None:
    return None if valor is None else str(valor)


def _par_para_json(par: ParAliquotas) -> dict[str, Any]:
    return {"pCBSSN": _texto(par.cbs), "pIBSSN": _texto(par.ibs)}


def _aliquotas_para_json(aliquotas: AliquotasEfetivas) -> dict[str, Any]:
    json_aliquotas: dict[str, Any] = {"impedimentoSublimite": aliquotas.impedimento_sublimite}
    if aliquotas.fator_r is not None:
        json_aliquotas["fatorR"] = aliquotas.fator_r
    for nome, anexo in aliquotas.anexos.items():
        json_anexo = _par_para_json(anexo.par)
        if anexo.sem_redistribuicao_iss is not None:
            json_anexo["semRedistribuicaoISS"] = _par_para_json(anexo.sem_redistribuicao_iss)
        json_aliquotas[f"anexo{nome}"] = json_anexo
    return json_aliquotas


def _item_para_json(item: ItemSimples) -> dict[str, Any]:
    json_item: dict[str, Any] = {
        "numero": item.numero,
        "cAtivSN": item.atividade,
        "cClassTrib": item.classificacao_tributaria,
        "baseCalculo": str(item.base_calculo),
        "valorImpostoSeletivo": str(item.valor_imposto_seletivo),
    }
    if item.ncm:
        json_item["ncm"] = item.ncm
    if item.nbs:
        json_item["nbs"] = item.nbs
    return json_item


def _operacao_para_json(operacao: OperacaoSimples) -> dict[str, Any]:
    return {
        "id": uuid4().hex,
        "versao": VERSAO_DO_FORMATO,
        "data": operacao.data.isoformat(),
        "tpDoc": str(operacao.tipo_documento),
        "CRT": str(operacao.crt),
        "aliquotasEfetivas": _aliquotas_para_json(operacao.aliquotas_efetivas),
        "itens": [_item_para_json(item) for item in operacao.itens],
    }


def _valor(no: Json | None, *caminho: str) -> Decimal:
    """Lê um valor aninhado; ausente significa que o motor não calculou (zero)."""
    for chave in caminho:
        if no is None:
            return Decimal(0)
        no = no.get(chave)
    return Decimal(0) if no is None else Decimal(str(no))


def _memorias(calculo: Json) -> tuple[MemoriaDeCalculo, ...]:
    memoria = calculo.get("memoriaCalculo") or {}
    nomes_por_texto: dict[str, list[str]] = {}
    for nome, chave in (("CBS", "cbs"), ("IBS", "ibs")):
        if texto := memoria.get(chave):
            nomes_por_texto.setdefault(texto, []).append(nome)
    return tuple(
        MemoriaDeCalculo(", ".join(nomes), texto) for texto, nomes in nomes_por_texto.items()
    )


def _mensagens(objeto: Json) -> tuple[str, ...]:
    motivo = (objeto.get("motivoEstado") or {}).get("descricao")
    erros = [e.get("detail") or e.get("title") for e in objeto.get("erros") or []]
    return tuple(str(m) for m in [motivo, *erros] if m)


def _item_calculado(objeto: Json, anexos: Mapping[int, str]) -> ItemSimplesCalculado:
    calculo = objeto.get("tribCalc") or {}
    numero = int(objeto["nObj"])
    return ItemSimplesCalculado(
        numero=numero,
        situacao=objeto["estadoItem"],
        receita_bruta=_valor(calculo, "vRBSNitem"),
        base_calculo=_valor(calculo, "vBC"),
        aliquota_cbs=_valor(calculo, "pCBSSN"),
        aliquota_ibs=_valor(calculo, "pIBSSN"),
        cbs=_valor(calculo, "vCBSSN"),
        ibs=_valor(calculo, "vIBSSN"),
        imposto_seletivo=_valor(calculo, "IS", "valor"),
        anexo=anexos.get(numero),
        mensagens=_mensagens(objeto),
        memorias_de_calculo=_memorias(calculo),
    )


def _atividade_do_motor(atividade: Json) -> AtividadeSimples:
    return AtividadeSimples(
        codigo=atividade["codigo"],
        descricao=atividade["descricao"],
        anexo=atividade.get("rotuloAnexo") or "",
        disponivel=bool(atividade.get("disponivel")),
        tipos_de_documento=tuple(int(t) for t in atividade.get("tpDocsAdmissiveis") or []),
    )


class MotorSimplesNacional:
    """Cumpre as portas de cálculo e de catálogo de atividades do Simples Nacional."""

    def __init__(self, cliente: httpx.Client) -> None:
        self._cliente = cliente

    def calcular(self, operacao: OperacaoSimples) -> ResultadoSimples:
        resposta = requisitar(
            lambda: self._cliente.post(CAMINHO_CALCULO, json=_operacao_para_json(operacao)),
            NOME_DO_MOTOR,
        ).json()
        resolucao = resposta.get("resolucaoAliquotas") or {}
        anexos = {int(i["numero"]): i.get("anexoAplicado") for i in resolucao.get("itens") or []}
        return ResultadoSimples(
            itens=tuple(_item_calculado(o, anexos) for o in resposta.get("objetos", [])),
            regime_apuracao=(resposta.get("oper") or {}).get("regimeApuracao"),
            avisos=tuple(resolucao.get("avisos") or []),
        )

    def atividades(self, data: date) -> tuple[AtividadeSimples, ...]:
        resposta = requisitar(
            lambda: self._cliente.get(CAMINHO_ATIVIDADES, params={"data": data.isoformat()}),
            NOME_DO_MOTOR,
        )
        return tuple(_atividade_do_motor(a) for a in resposta.json())
