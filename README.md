# Nome do app (provisório)

Aplicativo para motociclistas de entrega registrarem seus **expedientes de trabalho**: o app acompanha o trajeto por GPS, recebe os ganhos lançados durante o dia e calcula, em tempo real e no histórico, **quanto foi ganho, quanto foi gasto com combustível e qual o lucro** — por expediente, por dia ou por período.

Este repositório contém a **API**. O app Android (Kotlin) fica no repositório irmão **[`pi-iv-app`](../pi-iv-app)** (`univesp/pi-iv-app`), que consome esta API; o planejamento dele está em `pi-iv-app/docs/app-plan.md`.

📄 Especificação da API: [`docs/api-spec.md`](docs/api-spec.md)

## Stack

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.12 |
| Ambiente / dependências | [uv](https://docs.astral.sh/uv/) |
| Framework web | FastAPI |
| ORM / migrations | SQLAlchemy 2.0 (sync) + Alembic |
| Validação / config | Pydantic v2 + pydantic-settings |
| Banco de dados | PostgreSQL 16 |
| Autenticação | JWT (PyJWT) + hash de senha argon2 (pwdlib) |
| Testes | pytest, pytest-cov, testcontainers (Postgres real) |
| Lint / formatação | ruff |

## Estrutura

```
api/
  app/
    main.py
    core/            # config, db, segurança (JWT), erros, dependências, OpenAPI
    models/          # modelos SQLAlchemy
    schemas/         # schemas Pydantic (entrada/saída)
    repositories/    # acesso a dados
    services/        # regras de negócio; calculations.py = cálculos puros (§4 do spec)
    routers/         # endpoints FastAPI (registrados em routers/__init__.py)
  alembic/           # migrations
  tests/
    unit/            # sem banco e sem rede
    integration/     # PostgreSQL real via testcontainers
    conftest.py
    factories.py
  pyproject.toml
  uv.lock
  .python-version
.github/workflows/api.yml
docker-compose.yml
docs/
  api-spec.md
```

## Endpoints

Prefixo `/api/v1`. Documentação interativa em **`/docs`** (Swagger) e **`/redoc`** quando a API está rodando. Detalhes, regras e erros em [`docs/api-spec.md`](docs/api-spec.md#5-endpoints).

| Grupo | Rotas |
|---|---|
| Saúde | `GET /health` |
| Autenticação | `POST /auth/register`, `POST /auth/login` |
| Usuário | `GET /users/me`, `PATCH /users/me` |
| Combustíveis | `GET /fuels`, `GET /fuel-prices/current`, `PUT /fuel-prices` |
| Veículos | `POST /vehicles`, `GET /vehicles`, `GET/PATCH/DELETE /vehicles/{id}` |
| Expedientes | `POST /shifts`, `GET /shifts`, `GET /shifts/current`, `GET /shifts/{id}`, `POST /shifts/{id}/finish` |
| Ganhos | `POST/GET /shifts/{id}/earnings`, `PATCH/DELETE /shifts/{id}/earnings/{earning_id}` |
| GPS | `POST/GET /shifts/{id}/track-points` |
| Análise | `GET /analytics/daily`, `GET /analytics/summary` |

## Setup

O ambiente é gerenciado **100% pelo uv** — versão do Python (`.python-version`), virtualenv (`.venv`), dependências (`pyproject.toml` + `uv.lock`) e execução de comandos (`uv run`).

Pré-requisitos: [uv](https://docs.astral.sh/uv/getting-started/installation/) e Docker.

```bash
# instalar uv (se necessário)
curl -LsSf https://astral.sh/uv/install.sh | sh

# na raiz do repositório
docker compose up -d db              # PostgreSQL de desenvolvimento em localhost:5433

cd api
cp .env.example .env
uv sync                              # instala Python 3.12 (se preciso) e as dependências em .venv
uv run alembic upgrade head          # cria as tabelas e o seed de combustíveis
uv run fastapi dev app/main.py       # API em http://localhost:8000 (docs em /docs)
```

O Postgres do projeto usa a porta **5433** no host para não conflitar com outro Postgres local. Para mudar, defina `DB_PORT` ao subir o compose (`DB_PORT=5434 docker compose up -d db`) e ajuste `DATABASE_URL` no `api/.env`.

Health check: `curl localhost:8000/api/v1/health` → `{"status":"ok","database":"ok"}` (ou **503** se o banco estiver fora).

### Autenticação

As rotas protegidas usam JWT (`Authorization: Bearer <token>`). Defina `JWT_SECRET` no `api/.env`; em produção ele é obrigatório e precisa ter pelo menos 32 caracteres (gere com `openssl rand -hex 32`).

```bash
curl -X POST localhost:8000/api/v1/auth/register -H 'Content-Type: application/json' \
  -d '{"name":"John Doe","email":"john@example.com","password":"senha-segura-123","password_confirm":"senha-segura-123"}'

TOKEN=$(curl -s -X POST localhost:8000/api/v1/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"john@example.com","password":"senha-segura-123"}' | jq -r .access_token)

curl localhost:8000/api/v1/users/me -H "Authorization: Bearer $TOKEN"
```

No Swagger (`/docs`), use o botão **Authorize** e cole o token.

Migrations (Alembic, dentro de `api/`):

```bash
uv run alembic upgrade head                              # aplica todas
uv run alembic downgrade -1                              # desfaz a última
uv run alembic revision --autogenerate -m "descricao"    # gera nova a partir dos modelos
uv run alembic check                                     # falha se modelos e migrations divergirem
```

Adicionando dependências:

```bash
uv add <pacote>          # dependência da aplicação
uv add --dev <pacote>    # dependência de desenvolvimento (pytest, ruff, ...)
```

## Testes

```bash
uv run pytest                        # unitários + integração
uv run pytest -m unit                # apenas unitários (não precisa de Docker)
uv run pytest -m integration         # apenas integração
```

Os testes de integração sobem um **PostgreSQL real** em container (testcontainers), aplicam as migrations uma vez por sessão e isolam cada teste numa transação desfeita ao final — **o Docker precisa estar rodando**. A cobertura é medida automaticamente em toda execução.

Meta de cobertura: **≥ 90%** (o `pytest` falha abaixo disso). Cobertura atual: **100%** de linhas e branches.

Além dos testes de comportamento, `tests/unit/test_openapi.py` garante que toda rota tem descrição no Swagger e que toda rota protegida exige o token e documenta o 401.

## Qualidade

```bash
uv run ruff check .
uv run ruff format .
```

## CI

O workflow [`.github/workflows/api.yml`](.github/workflows/api.yml) roda a cada push na `main` e em pull requests que alterem `api/`:

- **Lint:** `ruff check` e `ruff format --check`.
- **Testes:** `uv sync --locked` (falha se o `uv.lock` estiver desatualizado), testes unitários e depois a suíte completa com PostgreSQL real (o runner do GitHub já tem Docker); o relatório `coverage.xml` fica como artefato da execução.

Para rodar o mesmo localmente, dentro de `api/`:

```bash
uv sync --locked && uv run ruff check . && uv run ruff format --check . && uv run pytest
```

## Roadmap

Todas as etapas concluídas:

1. Scaffold (uv, pyproject, ruff, docker-compose, config, `/health` + teste)
2. Modelos + Alembic + seed de combustíveis + infra de testes de integração
3. Autenticação e usuário
4. Combustíveis e preços
5. Veículos
6. Expedientes (iniciar / atual / encerrar) + módulo de cálculos
7. Ganhos
8. Pontos de GPS
9. Histórico e análise de desempenho
10. Revisão de cobertura, documentação OpenAPI e CI (GitHub Actions)

Detalhes de cada etapa em [`docs/api-spec.md`](docs/api-spec.md#7-roadmap-de-execução).
