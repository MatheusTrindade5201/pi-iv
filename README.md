# Nome do app (provisório)

Aplicativo para motociclistas de entrega registrarem seus **expedientes de trabalho**: o app acompanha o trajeto por GPS, recebe os ganhos lançados durante o dia e calcula, em tempo real e no histórico, **quanto foi ganho, quanto foi gasto com combustível e qual o lucro** — por expediente, por dia ou por período.

O projeto é composto por um app Android (Kotlin) e uma API. **Neste momento o escopo é apenas a API.**

📄 Especificação completa: [`docs/api-spec.md`](docs/api-spec.md)

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

## Estrutura prevista

```
api/
  app/
    main.py
    core/            # config, security, db
    models/          # modelos SQLAlchemy
    schemas/         # schemas Pydantic
    repositories/    # acesso a dados
    services/        # regras de negócio e cálculos
    routers/         # endpoints FastAPI
  alembic/
  tests/
    unit/
    integration/
    conftest.py
  pyproject.toml
  uv.lock
  .python-version
docker-compose.yml
docs/
  api-spec.md
```

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

Meta de cobertura: **≥ 90%**.

## Qualidade

```bash
uv run ruff check .
uv run ruff format .
```

## Roadmap

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
