"""Erros que o Hub sabe explicar ao usuário, sem detalhes de HTTP."""


class ErroDoHub(Exception):
    """Base de todos os erros esperados do Hub."""


class OperacaoInvalida(ErroDoHub):
    """Os dados informados não formam uma operação válida."""


class MotorRejeitouOperacao(ErroDoHub):
    """O motor oficial recusou a operação (regra tributária ou dado inconsistente)."""


class MotorIndisponivel(ErroDoHub):
    """Não foi possível obter resposta do motor oficial."""
