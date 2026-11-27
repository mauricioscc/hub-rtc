"""Tributos calculados pelo motor, já no vocabulário do Hub."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class TributosDoItem:
    numero: int
    base_calculo_ibs_cbs: Decimal
    cbs: Decimal
    ibs_uf: Decimal
    ibs_municipal: Decimal
    imposto_seletivo: Decimal

    @property
    def ibs(self) -> Decimal:
        return self.ibs_uf + self.ibs_municipal


@dataclass(frozen=True)
class ResultadoCalculo:
    itens: tuple[TributosDoItem, ...]

    @property
    def total_cbs(self) -> Decimal:
        return sum((item.cbs for item in self.itens), Decimal(0))

    @property
    def total_ibs(self) -> Decimal:
        return sum((item.ibs for item in self.itens), Decimal(0))

    @property
    def total_imposto_seletivo(self) -> Decimal:
        return sum((item.imposto_seletivo for item in self.itens), Decimal(0))
