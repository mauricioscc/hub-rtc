"""Rotas do Simples Nacional. Traduzem JSON para o domínio e o resultado para JSON."""

from datetime import date
from decimal import Decimal
from typing import Protocol

from fastapi import APIRouter
from pydantic import BaseModel

from hub_rtc.dominio.catalogo import AtividadeSimples
from hub_rtc.dominio.resultado_simples import ResultadoSimples
from hub_rtc.dominio.simples_nacional import (
    AliquotasEfetivas,
    AnexoAliquotas,
    ItemSimples,
    OperacaoSimples,
    ParAliquotas,
)
from hub_rtc.entrada.api import MemoriaResposta


class CasoDeUsoCalcularSimples(Protocol):
    def executar(self, operacao: OperacaoSimples) -> ResultadoSimples: ...


class ConsultaAtividades(Protocol):
    def executar(self, data: date) -> tuple[AtividadeSimples, ...]: ...


class ParPedido(BaseModel):
    cbs: Decimal | None = None
    ibs: Decimal | None = None

    def para_dominio(self) -> ParAliquotas:
        return ParAliquotas(cbs=self.cbs, ibs=self.ibs)


class AnexoPedido(ParPedido):
    sem_redistribuicao_iss: ParPedido | None = None

    def para_anexo(self) -> AnexoAliquotas:
        sem_redistribuicao = self.sem_redistribuicao_iss
        return AnexoAliquotas(
            par=self.para_dominio(),
            sem_redistribuicao_iss=sem_redistribuicao.para_dominio()
            if sem_redistribuicao
            else None,
        )


class AliquotasEfetivasPedido(BaseModel):
    anexos: dict[str, AnexoPedido]
    fator_r: bool | None = None
    impedimento_sublimite: bool = False

    def para_dominio(self) -> AliquotasEfetivas:
        return AliquotasEfetivas(
            anexos={nome: anexo.para_anexo() for nome, anexo in self.anexos.items()},
            fator_r=self.fator_r,
            impedimento_sublimite=self.impedimento_sublimite,
        )


class ItemSimplesPedido(BaseModel):
    numero: int
    atividade: str
    classificacao_tributaria: str
    base_calculo: Decimal
    valor_imposto_seletivo: Decimal = Decimal(0)
    ncm: str | None = None
    nbs: str | None = None


class PedidoSimples(BaseModel):
    data: date
    tipo_documento: int = 55
    crt: int = 1
    aliquotas_efetivas: AliquotasEfetivasPedido
    itens: list[ItemSimplesPedido]

    def para_dominio(self) -> OperacaoSimples:
        return OperacaoSimples(
            data=self.data,
            tipo_documento=self.tipo_documento,
            crt=self.crt,
            aliquotas_efetivas=self.aliquotas_efetivas.para_dominio(),
            itens=tuple(ItemSimples(**item.model_dump()) for item in self.itens),
        )


class ItemSimplesResposta(BaseModel):
    numero: int
    situacao: str
    receita_bruta: Decimal
    base_calculo: Decimal
    aliquota_cbs: Decimal
    aliquota_ibs: Decimal
    cbs: Decimal
    ibs: Decimal
    imposto_seletivo: Decimal
    total: Decimal
    anexo: str | None
    mensagens: list[str]
    memorias: list[MemoriaResposta]


class TotaisSimplesResposta(BaseModel):
    cbs: Decimal
    ibs: Decimal
    imposto_seletivo: Decimal
    tributos: Decimal


class RespostaSimples(BaseModel):
    itens: list[ItemSimplesResposta]
    totais: TotaisSimplesResposta
    regime_apuracao: str | None
    avisos: list[str]

    @classmethod
    def do_dominio(cls, resultado: ResultadoSimples) -> "RespostaSimples":
        return cls(
            itens=[
                ItemSimplesResposta(
                    numero=item.numero,
                    situacao=item.situacao,
                    receita_bruta=item.receita_bruta,
                    base_calculo=item.base_calculo,
                    aliquota_cbs=item.aliquota_cbs,
                    aliquota_ibs=item.aliquota_ibs,
                    cbs=item.cbs,
                    ibs=item.ibs,
                    imposto_seletivo=item.imposto_seletivo,
                    total=item.total,
                    anexo=item.anexo,
                    mensagens=list(item.mensagens),
                    memorias=[
                        MemoriaResposta(tributos=m.tributos, texto=m.texto)
                        for m in item.memorias_de_calculo
                    ],
                )
                for item in resultado.itens
            ],
            totais=TotaisSimplesResposta(
                cbs=resultado.total_cbs,
                ibs=resultado.total_ibs,
                imposto_seletivo=resultado.total_imposto_seletivo,
                tributos=resultado.total_tributos,
            ),
            regime_apuracao=resultado.regime_apuracao,
            avisos=list(resultado.avisos),
        )


class AtividadeResposta(BaseModel):
    codigo: str
    descricao: str
    anexo: str
    disponivel: bool
    tipos_de_documento: list[int]


def criar_roteador_simples(
    caso_de_uso: CasoDeUsoCalcularSimples, consulta_atividades: ConsultaAtividades
) -> APIRouter:
    roteador = APIRouter()

    @roteador.post("/api/calculos/simples-nacional")
    def calcular(pedido: PedidoSimples) -> RespostaSimples:
        return RespostaSimples.do_dominio(caso_de_uso.executar(pedido.para_dominio()))

    @roteador.get("/api/atividades-simples")
    def atividades(data: date | None = None) -> list[AtividadeResposta]:
        encontradas = consulta_atividades.executar(data or date.today())
        return [
            AtividadeResposta(
                codigo=a.codigo,
                descricao=a.descricao,
                anexo=a.anexo,
                disponivel=a.disponivel,
                tipos_de_documento=list(a.tipos_de_documento),
            )
            for a in encontradas
        ]

    return roteador
