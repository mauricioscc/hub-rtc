"""API HTTP do Hub (FastAPI). Traduz JSON para o domínio e erros do domínio para HTTP."""

from collections.abc import Sequence
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Protocol

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from hub_rtc.dominio.catalogo import SituacaoTributaria
from hub_rtc.dominio.erros import ErroDoHub, MotorIndisponivel
from hub_rtc.dominio.operacao import (
    AliquotasNominais,
    AliquotasSeletivo,
    ImpostoSeletivoItem,
    ItemOperacao,
    Operacao,
)
from hub_rtc.dominio.resultado import ResultadoCalculo

DIRETORIO_WEB = Path(__file__).parent / "web"
STATUS_ENTIDADE_INVALIDA = 422
STATUS_INDISPONIVEL = 503


class CasoDeUsoCalcular(Protocol):
    def executar(self, operacao: Operacao) -> ResultadoCalculo: ...


class ConsultaSituacoes(Protocol):
    def executar(self, data: date) -> tuple[SituacaoTributaria, ...]: ...


class ImpostoSeletivoPedido(BaseModel):
    cst: str
    classificacao_tributaria: str
    base_calculo: Decimal
    quantidade: Decimal | None = None
    unidade: str | None = None


class ItemPedido(BaseModel):
    numero: int
    cst: str
    classificacao_tributaria: str
    base_calculo: Decimal | None = None
    ncm: str | None = None
    nbs: str | None = None
    imposto_seletivo: ImpostoSeletivoPedido | None = None

    def para_dominio(self) -> ItemOperacao:
        seletivo = self.imposto_seletivo
        return ItemOperacao(
            numero=self.numero,
            cst=self.cst,
            classificacao_tributaria=self.classificacao_tributaria,
            base_calculo=self.base_calculo,
            ncm=self.ncm,
            nbs=self.nbs,
            imposto_seletivo=ImpostoSeletivoItem(**seletivo.model_dump()) if seletivo else None,
        )


class AliquotasSeletivoPedido(BaseModel):
    ad_valorem: Decimal
    ad_rem: Decimal


class AliquotasNominaisPedido(BaseModel):
    cbs: Decimal
    ibs_estadual: Decimal
    ibs_municipal: Decimal
    imposto_seletivo: AliquotasSeletivoPedido | None = None

    def para_dominio(self) -> AliquotasNominais:
        seletivo = self.imposto_seletivo
        return AliquotasNominais(
            cbs=self.cbs,
            ibs_estadual=self.ibs_estadual,
            ibs_municipal=self.ibs_municipal,
            imposto_seletivo=AliquotasSeletivo(**seletivo.model_dump()) if seletivo else None,
        )


class PedidoCalculo(BaseModel):
    fato_gerador: datetime
    municipio: int
    uf: str
    tipo_documento: int | None = None
    aliquotas_nominais: AliquotasNominaisPedido | None = None
    itens: list[ItemPedido]

    def para_dominio(self) -> Operacao:
        aliquotas = self.aliquotas_nominais
        return Operacao(
            fato_gerador=self.fato_gerador,
            municipio=self.municipio,
            uf=self.uf,
            tipo_documento=self.tipo_documento,
            aliquotas_nominais=aliquotas.para_dominio() if aliquotas else None,
            itens=tuple(item.para_dominio() for item in self.itens),
        )


class MemoriaResposta(BaseModel):
    tributos: str
    texto: str


class ItemResposta(BaseModel):
    numero: int
    base_calculo: Decimal
    cbs: Decimal
    ibs: Decimal
    ibs_uf: Decimal
    ibs_municipal: Decimal
    imposto_seletivo: Decimal
    aliquota_cbs: Decimal
    aliquota_ibs_uf: Decimal
    aliquota_ibs_municipal: Decimal
    memorias: list[MemoriaResposta]


class ClassificacaoResposta(BaseModel):
    codigo: str
    descricao: str


class SituacaoResposta(BaseModel):
    codigo: str
    descricao: str
    classificacoes: list[ClassificacaoResposta]

    @classmethod
    def do_dominio(cls, situacao: SituacaoTributaria) -> "SituacaoResposta":
        return cls(
            codigo=situacao.codigo,
            descricao=situacao.descricao,
            classificacoes=[
                ClassificacaoResposta(codigo=c.codigo, descricao=c.descricao)
                for c in situacao.classificacoes
            ],
        )


class TotaisResposta(BaseModel):
    cbs: Decimal
    ibs: Decimal
    imposto_seletivo: Decimal


class RespostaCalculo(BaseModel):
    itens: list[ItemResposta]
    totais: TotaisResposta
    simulado: bool

    @classmethod
    def do_dominio(cls, resultado: ResultadoCalculo) -> "RespostaCalculo":
        return cls(
            itens=[
                ItemResposta(
                    numero=item.numero,
                    base_calculo=item.base_calculo_ibs_cbs,
                    cbs=item.cbs,
                    ibs=item.ibs,
                    ibs_uf=item.ibs_uf,
                    ibs_municipal=item.ibs_municipal,
                    imposto_seletivo=item.imposto_seletivo,
                    aliquota_cbs=item.aliquota_cbs,
                    aliquota_ibs_uf=item.aliquota_ibs_uf,
                    aliquota_ibs_municipal=item.aliquota_ibs_municipal,
                    memorias=[
                        MemoriaResposta(tributos=m.tributos, texto=m.texto)
                        for m in item.memorias_de_calculo
                    ],
                )
                for item in resultado.itens
            ],
            totais=TotaisResposta(
                cbs=resultado.total_cbs,
                ibs=resultado.total_ibs,
                imposto_seletivo=resultado.total_imposto_seletivo,
            ),
            simulado=resultado.simulado,
        )


def _responder_erro_do_hub(_: Request, erro: Exception) -> JSONResponse:
    status = (
        STATUS_INDISPONIVEL if isinstance(erro, MotorIndisponivel) else STATUS_ENTIDADE_INVALIDA
    )
    return JSONResponse(status_code=status, content={"erro": str(erro)})


def criar_roteador_regime_regular(
    caso_de_uso: CasoDeUsoCalcular, consulta_situacoes: ConsultaSituacoes
) -> APIRouter:
    roteador = APIRouter()

    @roteador.post("/api/calculos/regime-regular")
    def calcular(pedido: PedidoCalculo) -> RespostaCalculo:
        resultado = caso_de_uso.executar(pedido.para_dominio())
        return RespostaCalculo.do_dominio(resultado)

    @roteador.get("/api/situacoes-tributarias")
    def situacoes_tributarias(data: date | None = None) -> list[SituacaoResposta]:
        situacoes = consulta_situacoes.executar(data or date.today())
        return [SituacaoResposta.do_dominio(s) for s in situacoes]

    return roteador


def criar_app(roteadores: Sequence[APIRouter], origens_permitidas: tuple[str, ...] = ()) -> FastAPI:
    app = FastAPI(title="Hub RTC", version="0.1.0")
    if origens_permitidas:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(origens_permitidas),
            allow_methods=["GET", "POST"],
            allow_headers=["Content-Type"],
        )
    app.add_exception_handler(ErroDoHub, _responder_erro_do_hub)

    @app.get("/api/saude")
    def saude() -> dict[str, str]:
        return {"status": "ok"}

    for roteador in roteadores:
        app.include_router(roteador)

    # Por último: as rotas /api têm prioridade sobre os arquivos da tela.
    app.mount("/", StaticFiles(directory=DIRETORIO_WEB, html=True), name="web")
    return app
