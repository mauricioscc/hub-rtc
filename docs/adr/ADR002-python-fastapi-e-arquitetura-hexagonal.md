# ADR002 - Python, FastAPI e arquitetura hexagonal

## Data

> 26/11/2026

## Status

> Aceito

## Contexto

O Hub precisa orquestrar três motores, padronizar erros e oferecer API e tela web.
A equipe é um desenvolvedor, que já usa Python (CertiControl), apoiado pelo Claude.

## Decisão

- Linguagem: Python 3.12+ com FastAPI.
- Arquitetura hexagonal (portas e adaptadores), em cinco camadas:
  `dominio` → `portas` → `casos_de_uso` → `entrada` / `adaptadores` → `composicao`.
  As dependências só apontam para dentro; o `import-linter` barra o contrário no CI.
- Estilo: guia [clean-code-python](https://github.com/zedr/clean-code-python),
  verificado por `ruff` (complexidade máxima 6, até 3 argumentos), `mypy --strict`
  e revisão de código.
- Desenvolvimento orientado a testes (TDD): teste vermelho, código verde, refatorar.

## Consequências

Positivas:

- O domínio é testado sem rede nem Docker, em segundos.
- Trocar ou acrescentar um motor é escrever um adaptador novo.

Negativas:

- Mais arquivos que um script único; o ganho aparece quando a Receita muda algo.
