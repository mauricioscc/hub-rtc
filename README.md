# Hub RTC

Ferramenta interna que reúne, num só lugar, as três ferramentas oficiais da Receita
Federal para a Reforma Tributária do Consumo (CBS, IBS e Imposto Seletivo, LC 214/2025):

| Motor | Versão | Porta | Repositório |
| --- | --- | --- | --- |
| Calculadora Regime Regular | 1.7.2 | 8081 | [calculadora-rtc-regime-regular](https://github.com/ReceitaFederal/calculadora-rtc-regime-regular) |
| Calculadora Simples Nacional | 1.0.2 | 8082 | [calculadora-rtc-simples-nacional](https://github.com/ReceitaFederal/calculadora-rtc-simples-nacional) |
| Gerador de DANFSe | 1.0.0 | 8083 | [calculadora-rtc-gerador-danfse](https://github.com/ReceitaFederal/calculadora-rtc-gerador-danfse) |

> Os resultados são simulações feitas com os motores oficiais. Não substituem a
> emissão nem a autorização de documentos fiscais.

## Estado atual: Fase 0 (Fundação)

Os três motores sobem com um comando, compartilhando o banco oficial da Receita.
O Hub em Python ainda é só o esqueleto das camadas; o cálculo chega na Fase 1.

## Subir os motores

Requisito: Docker com Compose. Java, Maven e Go **não** são necessários.

```bash
cp .env.example .env
docker compose up -d --build --wait
```

O primeiro build leva alguns minutos (baixa dependências e gera o banco).
Swagger de cada motor:

- Regime Regular: <http://localhost:8081/api/swagger-ui.html>
- Simples Nacional: <http://localhost:8082/api/swagger-ui.html>
- Gerador de DANFSe: <http://localhost:8083/api/swagger-ui/index.html>

Para atualizar um motor, troque a versão no `.env` e rode
`docker compose up -d --build` (ver [ADR003](docs/adr/ADR003-versoes-fixadas-e-banco-gerado-em-conteiner.md)).

## Desenvolvimento

```bash
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"   # Linux: .venv/bin/pip

pytest              # testes de unidade (rápidos, sem Docker)
pytest -m fumaca    # testa os motores no ar (Docker local)
ruff check . && ruff format --check .
mypy src tests
lint-imports        # garante que as camadas não se misturam
```

Para testar o servidor Docker da empresa em vez do local:
`HUB_RTC_HOST=<endereco-do-servidor> pytest -m fumaca`.

## Arquitetura

```
src/hub_rtc/
  dominio/        entidades e regras, sem I/O
  portas/         interfaces (Protocol) que os casos de uso exigem
  casos_de_uso/   um caso de uso por arquivo
  adaptadores/    clientes HTTP dos três motores
  entrada/        rotas FastAPI e tela web
  composicao.py   único ponto que liga portas a adaptadores
```

Dependências só apontam para dentro (camadas de baixo não conhecem as de cima).
Decisões registradas em [docs/adr](docs/adr).
