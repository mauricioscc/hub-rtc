"""Operação de consumo a ser calculada. Valida só o formato; a regra tributária é do motor."""

import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from hub_rtc.dominio.erros import OperacaoInvalida

TAMANHO_CST = 3
TAMANHO_CLASSIFICACAO = 6
TAMANHO_UF = 2


def _exigir_digitos(valor: str, tamanho: int, nome: str) -> None:
    if not re.fullmatch(rf"\d{{{tamanho}}}", valor):
        raise OperacaoInvalida(f"{nome} deve ter {tamanho} dígitos, recebido '{valor}'")


@dataclass(frozen=True)
class ItemOperacao:
    numero: int
    cst: str
    classificacao_tributaria: str
    base_calculo: Decimal
    ncm: str | None = None

    def __post_init__(self) -> None:
        if self.numero < 1:
            raise OperacaoInvalida(f"número do item deve ser positivo, recebido {self.numero}")
        _exigir_digitos(self.cst, TAMANHO_CST, "CST")
        _exigir_digitos(
            self.classificacao_tributaria, TAMANHO_CLASSIFICACAO, "classificação tributária"
        )
        if self.base_calculo < 0:
            raise OperacaoInvalida("base de cálculo não pode ser negativa")


@dataclass(frozen=True)
class Operacao:
    fato_gerador: datetime
    municipio: int
    uf: str
    itens: tuple[ItemOperacao, ...]
    tipo_documento: int | None = None

    def __post_init__(self) -> None:
        if not self.itens:
            raise OperacaoInvalida("a operação precisa de ao menos um item")
        if len(self.uf) != TAMANHO_UF or not self.uf.isalpha():
            raise OperacaoInvalida(f"UF deve ter duas letras, recebido '{self.uf}'")
        numeros = [item.numero for item in self.itens]
        if len(set(numeros)) != len(numeros):
            raise OperacaoInvalida("número de item repetido na operação")
