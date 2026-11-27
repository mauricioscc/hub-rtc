"""Operação de consumo a ser calculada. Valida só o formato; a regra tributária é do motor."""

import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from hub_rtc.dominio.erros import OperacaoInvalida

TAMANHO_CST = 3
TAMANHO_CLASSIFICACAO = 6
TAMANHO_UF = 2
TAMANHO_NBS = 9
ALIQUOTA_MAXIMA = Decimal(100)


def _exigir_digitos(valor: str, tamanho: int, nome: str) -> None:
    if not re.fullmatch(rf"\d{{{tamanho}}}", valor):
        raise OperacaoInvalida(f"{nome} deve ter {tamanho} dígitos, recebido '{valor}'")


@dataclass(frozen=True)
class AliquotasSeletivo:
    """Alíquotas nominais do Imposto Seletivo: ad valorem em %, ad rem por unidade."""

    ad_valorem: Decimal
    ad_rem: Decimal

    def __post_init__(self) -> None:
        if not 0 <= self.ad_valorem <= ALIQUOTA_MAXIMA:
            raise OperacaoInvalida(f"alíquota ad valorem deve estar entre 0 e {ALIQUOTA_MAXIMA}%")
        if self.ad_rem < 0:
            raise OperacaoInvalida("alíquota ad rem não pode ser negativa")


@dataclass(frozen=True)
class AliquotasNominais:
    """Alíquotas em %, informadas pelo usuário (o motor as exige a partir de 01/01/2027)."""

    cbs: Decimal
    ibs_estadual: Decimal
    ibs_municipal: Decimal
    imposto_seletivo: AliquotasSeletivo | None = None

    def __post_init__(self) -> None:
        for nome, valor in (
            ("CBS", self.cbs),
            ("IBS estadual", self.ibs_estadual),
            ("IBS municipal", self.ibs_municipal),
        ):
            if not 0 <= valor <= ALIQUOTA_MAXIMA:
                raise OperacaoInvalida(
                    f"alíquota nominal de {nome} deve estar entre 0 e {ALIQUOTA_MAXIMA}%"
                )


@dataclass(frozen=True)
class ImpostoSeletivoItem:
    """Dados do Imposto Seletivo do item. A base de CBS/IBS passa a ser derivada dela."""

    cst: str
    classificacao_tributaria: str
    base_calculo: Decimal
    quantidade: Decimal | None = None
    unidade: str | None = None

    def __post_init__(self) -> None:
        _exigir_digitos(self.cst, TAMANHO_CST, "CST do Imposto Seletivo")
        _exigir_digitos(
            self.classificacao_tributaria,
            TAMANHO_CLASSIFICACAO,
            "classificação do Imposto Seletivo",
        )
        if self.base_calculo < 0:
            raise OperacaoInvalida("base de cálculo do Imposto Seletivo não pode ser negativa")
        if self.quantidade is not None and self.quantidade < 0:
            raise OperacaoInvalida("quantidade não pode ser negativa")


@dataclass(frozen=True)
class ItemOperacao:
    numero: int
    cst: str
    classificacao_tributaria: str
    base_calculo: Decimal | None
    ncm: str | None = None
    imposto_seletivo: ImpostoSeletivoItem | None = None
    nbs: str | None = None

    def __post_init__(self) -> None:
        if self.numero < 1:
            raise OperacaoInvalida(f"número do item deve ser positivo, recebido {self.numero}")
        _exigir_digitos(self.cst, TAMANHO_CST, "CST")
        _exigir_digitos(
            self.classificacao_tributaria, TAMANHO_CLASSIFICACAO, "classificação tributária"
        )
        if self.nbs is not None:
            _exigir_digitos(self.nbs, TAMANHO_NBS, "NBS")
        if self.base_calculo is None and self.imposto_seletivo is None:
            raise OperacaoInvalida("base de cálculo é obrigatória sem Imposto Seletivo")
        if self.base_calculo is not None and self.base_calculo < 0:
            raise OperacaoInvalida("base de cálculo não pode ser negativa")


@dataclass(frozen=True)
class Operacao:
    fato_gerador: datetime
    municipio: int
    uf: str
    itens: tuple[ItemOperacao, ...]
    tipo_documento: int | None = None
    aliquotas_nominais: AliquotasNominais | None = None

    def __post_init__(self) -> None:
        if not self.itens:
            raise OperacaoInvalida("a operação precisa de ao menos um item")
        if len(self.uf) != TAMANHO_UF or not self.uf.isalpha():
            raise OperacaoInvalida(f"UF deve ter duas letras, recebido '{self.uf}'")
        numeros = [item.numero for item in self.itens]
        if len(set(numeros)) != len(numeros):
            raise OperacaoInvalida("número de item repetido na operação")
