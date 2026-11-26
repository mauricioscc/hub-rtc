# ADR003 - Versões fixadas e banco oficial gerado em contêiner

## Data

> 26/11/2026

## Status

> Aceito

## Contexto

- As duas calculadoras exigem o banco SQLite `calculadora-pro.db`, gerado pelos
  scripts Flyway do repositório do Regime Regular. Sem ele, não iniciam.
- Regime Regular e Gerador de DANFSe usam a mesma porta padrão (8080).
- Os repositórios Java não versionam o `maven-wrapper.jar`, então `./mvnw` não roda
  num clone limpo.
- O servidor Docker da empresa não tem Java 25 nem Go instalados, e não precisa ter.

## Decisão

- Cada motor é compilado da sua tag oficial, definida no `.env`
  (`VERSAO_REGIME_REGULAR`, `VERSAO_SIMPLES_NACIONAL`, `VERSAO_GERADOR_DANFSE`).
- O serviço `banco` gera o banco uma vez, copia para o volume `banco-oficial` e
  encerra; as calculadoras o montam somente leitura.
- Portas publicadas: 8081 (Regime Regular), 8082 (Simples), 8083 (DANFSe).
- Builds Java usam a imagem oficial `maven:3.9-eclipse-temurin-25` no lugar do wrapper.
- Cada contêiner tem limite de memória (1 GB, 768 MB e 128 MB).

## Consequências

Positivas:

- `docker compose up -d --build` sobe tudo em qualquer máquina com Docker.
- A versão de cada motor em uso fica explícita e auditável.

Negativas:

- O primeiro build baixa dependências Maven e Go e leva alguns minutos.
- Ao trocar a versão do Regime Regular, o banco precisa ser regerado
  (`docker compose build banco` e recriar o volume).
