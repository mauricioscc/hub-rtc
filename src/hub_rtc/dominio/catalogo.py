"""Códigos de situação e classificação tributária que o motor aceita numa data."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ClassificacaoTributaria:
    codigo: str
    descricao: str


@dataclass(frozen=True)
class SituacaoTributaria:
    codigo: str
    descricao: str
    classificacoes: tuple[ClassificacaoTributaria, ...]
