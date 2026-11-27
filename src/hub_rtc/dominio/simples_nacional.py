"""Operação do Simples Nacional. Valida só o formato; a regra tributária é do motor."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from hub_rtc.dominio.erros import OperacaoInvalida
from hub_rtc.dominio.operacao import exigir_digitos

ANEXOS = ("I", "II", "III", "IV", "V")
CRT_ACEITOS = (1, 2)
ALIQUOTA_MAXIMA = Decimal(100)
TAMANHO_ATIVIDADE = 2
TAMANHO_CLASSIFICACAO = 6
TAMANHO_NBS = 9


@dataclass(frozen=True)
class ParAliquotas:
    """Alíquotas efetivas em %. O IBS é nulo quando o sublimite impede recolhê-lo."""

    cbs: Decimal | None
    ibs: Decimal | None

    def __post_init__(self) -> None:
        for valor in (self.cbs, self.ibs):
            if valor is not None and not 0 <= valor <= ALIQUOTA_MAXIMA:
                raise OperacaoInvalida(
                    f"alíquota efetiva deve estar entre 0 e {ALIQUOTA_MAXIMA}%, recebido {valor}"
                )


@dataclass(frozen=True)
class AnexoAliquotas:
    par: ParAliquotas
    # Usado nos anexos III a V quando o ISS não entra no cálculo do Simples.
    sem_redistribuicao_iss: ParAliquotas | None = None


@dataclass(frozen=True)
class AliquotasEfetivas:
    """Linha de alíquotas efetivas do contribuinte no período, por anexo."""

    anexos: Mapping[str, AnexoAliquotas]
    fator_r: bool | None = None
    impedimento_sublimite: bool = False

    def __post_init__(self) -> None:
        for anexo in self.anexos:
            if anexo not in ANEXOS:
                raise OperacaoInvalida(f"anexo '{anexo}' desconhecido; use {', '.join(ANEXOS)}")


@dataclass(frozen=True)
class ItemSimples:
    numero: int
    atividade: str
    classificacao_tributaria: str
    base_calculo: Decimal
    valor_imposto_seletivo: Decimal = Decimal(0)
    ncm: str | None = None
    nbs: str | None = None

    def __post_init__(self) -> None:
        if self.numero < 1:
            raise OperacaoInvalida(f"número do item deve ser positivo, recebido {self.numero}")
        exigir_digitos(self.atividade, TAMANHO_ATIVIDADE, "atividade")
        exigir_digitos(
            self.classificacao_tributaria, TAMANHO_CLASSIFICACAO, "classificação tributária"
        )
        if self.nbs is not None:
            exigir_digitos(self.nbs, TAMANHO_NBS, "NBS")
        if self.base_calculo < 0 or self.valor_imposto_seletivo < 0:
            raise OperacaoInvalida("base de cálculo e Imposto Seletivo não podem ser negativos")


@dataclass(frozen=True)
class OperacaoSimples:
    data: date
    tipo_documento: int
    crt: int
    aliquotas_efetivas: AliquotasEfetivas
    itens: tuple[ItemSimples, ...]

    def __post_init__(self) -> None:
        if self.crt not in CRT_ACEITOS:
            raise OperacaoInvalida(f"CRT deve ser 1 ou 2, recebido {self.crt}")
        if not self.itens:
            raise OperacaoInvalida("a operação precisa de ao menos um item")
        numeros = [item.numero for item in self.itens]
        if len(set(numeros)) != len(numeros):
            raise OperacaoInvalida("número de item repetido na operação")
