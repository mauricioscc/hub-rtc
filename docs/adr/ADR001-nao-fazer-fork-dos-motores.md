# ADR001 - Não fazer fork dos motores da Receita Federal

## Data

> 26/11/2026

## Status

> Aceito

## Contexto

A Receita Federal publica três motores oficiais da Reforma Tributária do Consumo:
Calculadora Regime Regular (Java), Calculadora Simples Nacional (Java) e Gerador de
DANFSe (Go). Eles mudam com frequência: só o Regime Regular tinha 73 migrações de
banco até 30/10/2026. Copiar e adaptar esse código nos obrigaria a acompanhar cada
mudança fiscal à mão.

## Decisão

Os motores são usados exatamente como a Receita publica: compilados da tag oficial
do GitHub, dentro de contêineres, sem alterar nenhuma linha. O Hub RTC só conversa
com eles por HTTP. Toda regra fiscal continua sendo da Receita.

## Consequências

Positivas:

- Atualizar para uma nova release da Receita é trocar a versão no `.env`.
- O resultado do cálculo é o mesmo do motor oficial.

Negativas:

- Dependemos dos contratos HTTP da Receita; mudanças neles quebram o Hub
  (mitigado por testes de contrato a partir da Fase 1).
- Defeitos dos motores só podem ser contornados no adaptador ou reportados à Receita.
