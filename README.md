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

## O que funciona hoje

**Cálculo do Regime Regular** (CBS, IBS estadual e municipal, Imposto Seletivo) pelo motor
oficial, por API e por tela web (`index.html`):

- Listas de seleção de CST e classificação tributária, vindas do motor para a data informada.
- Resultado por item e em total, com a alíquota efetiva (já com a redução) e a memória de
  cálculo do motor.
- Exemplos prontos: tributação integral, medicamento (redução de 60%), bares e restaurantes
  (40%), isenção, imunidade, obras e bens imóveis (50%), oficina automotiva e vários itens.
- Fatos geradores a partir de 01/01/2027: a tela pede as alíquotas nominais (CBS, IBS estadual e
  municipal) e avisa que o cálculo é uma simulação com os valores informados.
- Imposto Seletivo por item (ad valorem e ad rem), a partir de 2027: com ele, o motor calcula a
  base de CBS e IBS (base do IS + imposto) e a tela deixa de pedir essa base.
- NBS por item (serviços) e tipo de documento (NF-e, NFC-e, CT-e) opcionais. Com tipo de documento,
  o motor confere se NCM ou NBS são permitidos para a classificação (ex.: NF-e com a classificação
  000001 não aceita NBS) e a tela mostra a mensagem dele.
- Erros do motor traduzidos: 422 para recusa (ex.: CST inexistente), 503 para motor fora do ar.

**Cálculo do Simples Nacional** (CBS e IBS) pelo motor oficial, por API e por tela web
(`simples.html`, com navegação entre as duas telas):

- NF-e, NFC-e e CT-e, com CRT 1 (Simples) ou 2 (excesso de sublimite, sem IBS).
- Alíquotas efetivas do período informadas por anexo (I a V, com o par sem redistribuição do
  ISS nos anexos III a V), fator "r" e impedimento pelo sublimite.
- Atividade do Simples Nacional escolhida numa lista vinda do motor, filtrada pelo tipo de documento.
- Item que o motor não consegue calcular (atividade inexistente, alíquota do anexo ausente,
  classificação incompatível) aparece com a mensagem dele, sem derrubar os demais itens.
- Mostra o regime de apuração, os avisos e a memória de cálculo. O cálculo vale a partir de 2027.

### API do Hub

| Rota | O que faz |
| --- | --- |
| `POST /api/calculos/regime-regular` | Calcula os tributos de uma operação |
| `GET /api/situacoes-tributarias?data=AAAA-MM-DD` | Lista CSTs e classificações vigentes na data |
| `POST /api/calculos/simples-nacional` | Calcula CBS e IBS de uma operação do Simples Nacional |
| `GET /api/atividades-simples?data=AAAA-MM-DD` | Lista as atividades do Simples Nacional vigentes na data |
| `GET /api/saude` | Confere se o Hub está no ar |

A documentação interativa fica em `/docs` do Hub. Valores monetários e alíquotas saem
como texto, para não perder casas decimais.

### Roteiro

| Fase | Conteúdo | Situação |
| --- | --- | --- |
| 0 | Motores oficiais no Docker | Pronta |
| 1 | Cálculo do Regime Regular (API e tela) | Pronta |
| 2 | Publicação: repositório público, CI, tela no Pages, Hub via Tailscale Funnel | Pronta |
| 3 | Completar o Regime Regular: alíquotas nominais (2027+), Imposto Seletivo, NBS, tipo de documento, exportação | Em andamento (só falta a exportação) |
| 4 | Simples Nacional | Em andamento (NF-e, NFC-e e CT-e prontos; falta NFS-e) |
| 5 | Gerador de DANFSe | Planejada |
| 6 | Produção: servidor da empresa, HTTPS, acesso controlado, monitoramento | Planejada |

### Limitações conhecidas

- O tipo de documento da tela lista só NF-e, NFC-e e CT-e (NFS-e e outros ficam para depois). O CST e a
  classificação do Imposto Seletivo são digitados (padrão 000 / 000001), sem lista de seleção.
- Só foram testados tributação integral, reduções, isenção e imunidade. Crédito presumido,
  monofasia, diferimento e compra governamental não foram exercitados.
- O Hub público não tem login nem limite de uso.
- Simples Nacional: a NFS-e (tipo 91, com os campos de ISS e de regime municipal), o MEI e a
  tela de compra governamental ainda não existem. As alíquotas efetivas são digitadas pelo
  usuário: o Hub não as calcula a partir da receita acumulada.
- O motor do Gerador de DANFSe sobe e responde, mas o Hub ainda não o usa.

## Subir o Hub e os motores

Requisito: Docker com Compose. Java, Maven e Go **não** são necessários.

```bash
cp .env.example .env
docker compose up -d --build --wait
```

O primeiro build leva alguns minutos (baixa dependências e gera o banco).
Com tudo no ar, a tela e a API do Hub ficam em <http://localhost:8000>
(docs da API em `/docs`). Swagger de cada motor:

- Regime Regular: <http://localhost:8081/api/swagger-ui.html>
- Simples Nacional: <http://localhost:8082/api/swagger-ui.html>
- Gerador de DANFSe: <http://localhost:8083/api/swagger-ui/index.html>

Para atualizar um motor, troque a versão no `.env` e rode
`docker compose up -d --build` (ver [ADR003](docs/adr/ADR003-versoes-fixadas-e-banco-gerado-em-conteiner.md)).

## Tela de testes no GitHub Pages

O Pages só serve arquivos estáticos: ele hospeda a **tela**, não a API nem os motores.
Para o funcionário testar:

1. No servidor Docker da empresa, no `.env`, defina
   `HUB_RTC_ORIGENS_PERMITIDAS=https://<usuario>.github.io` e rode `docker compose up -d --build`.
   O Hub precisa estar acessível a quem vai testar (endereço HTTPS público ou VPN).
2. No GitHub: *Settings → Pages → Source: GitHub Actions*. O workflow
   [pages.yml](.github/workflows/pages.yml) publica a tela a cada mudança em `src/hub_rtc/entrada/web/`.
3. O funcionário abre `https://<usuario>.github.io/<repositorio>/`, informa o endereço do
   Hub uma vez (fica lembrado no navegador) ou usa `?api=https://endereco-do-hub`.

Endereço atual dos testes: tela em <https://mauricioscc.github.io/hub-rtc/>, Hub em
`https://office-mscx.tailbf5033.ts.net`, publicado pelo Tailscale Funnel a partir do PC
do desenvolvedor (`tailscale funnel --bg 8000`; para desligar: `tailscale funnel --https=443 off`).
O Hub só responde enquanto esse PC e o Docker estiverem ligados.
Atenção: em computadores que fazem parte da rede Tailscale do desenvolvedor, o nome do Hub
resolve para um IP da rede privada e o navegador bloqueia a chamada vinda do Pages
(`LocalNetworkAccessPermissionDenied`). Nesses computadores use <http://localhost:8000>.
Quem está fora dessa rede (o caso do funcionário) não é afetado.

Sem Pages, basta abrir o endereço do próprio Hub: ele serve a mesma tela.

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
  adaptadores/    clientes HTTP dos motores (Regime Regular e Simples Nacional)
  entrada/        rotas FastAPI e tela web
  composicao.py   único ponto que liga portas a adaptadores
```

Dependências só apontam para dentro (camadas de baixo não conhecem as de cima).
Decisões registradas em [docs/adr](docs/adr).

## Licença

[MIT](LICENSE). Os motores da Receita Federal usados pelo Hub são projetos separados,
compilados das tags oficiais sem alteração (ver [ADR001](docs/adr/ADR001-nao-fazer-fork-dos-motores.md)),
e seguem as licenças dos seus próprios repositórios.
