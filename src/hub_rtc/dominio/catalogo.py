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


@dataclass(frozen=True)
class AtividadeSimples:
    """Atividade do Simples Nacional (define o anexo e, com ele, as alíquotas efetivas)."""

    codigo: str
    descricao: str
    anexo: str
    disponivel: bool
    tipos_de_documento: tuple[int, ...]
