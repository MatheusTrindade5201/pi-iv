# Especificação da API

Documento de referência da API do app de registro de expedientes para motociclistas. Serve de base para planejar e executar cada etapa do [roadmap](#7-roadmap-de-execução).

- [1. Visão geral](#1-visão-geral)
- [2. Modelo de dados](#2-modelo-de-dados)
- [3. Regras de negócio](#3-regras-de-negócio)
- [4. Cálculos](#4-cálculos)
- [5. Endpoints](#5-endpoints)
- [6. Estratégia de testes](#6-estratégia-de-testes)
- [7. Roadmap de execução](#7-roadmap-de-execução)
- [8. Pontos em aberto](#8-pontos-em-aberto)

---

## 1. Visão geral

O motociclista cadastra sua moto e o preço dos combustíveis que costuma pagar. Ao começar a trabalhar, **inicia um expediente**: o app passa a enviar pontos de GPS e o motociclista **lança os ganhos** (corridas/entregas) ao longo do dia. A API calcula a distância percorrida, o tempo parado, o gasto de combustível e o lucro, tanto parcial (expediente em andamento) quanto final. O histórico mostra o lucro por dia e permite análise por período.

### Telas → funcionalidades da API

| Tela | O que a API precisa oferecer |
|---|---|
| **Login** | Autenticar por e-mail e senha e devolver token JWT |
| **Cadastro** | Criar usuário (nome, e-mail, senha, confirmação de senha) |
| **Home / Expediente** | Expediente em andamento com duração, status do GPS (último ponto, lacunas) e lucro parcial: ganhos, combustível, km, tempo, valor/hora, valor/km |
| **Lançar ganho** | Adicionar ganho ao expediente; "Sobrescrever ganho atual" edita o último ganho lançado |
| **Encerrar expediente** | Resumo final (com aviso de GPS inativo) e encerramento com métricas persistidas |
| **Histórico** | Lista de dias com o lucro do dia; iniciar novo expediente |
| **Perfil** | Editar nome; cadastrar/atualizar moto (modelo, combustível, consumo médio, cilindrada, ano); ver/editar preço da gasolina e do etanol |

---

## 2. Modelo de dados

Baseado no diagrama do projeto (dbdiagram.io). Itens marcados com **➕** são adições ao diagrama original.

Convenções:
- Chaves primárias `uuid` (gerado pela aplicação, `uuid4`).
- Valores monetários e numéricos em `numeric` (Python: `Decimal`), nunca `float`.
- Timestamps em `timestamptz`, sempre gravados em UTC.
- `NN` = NOT NULL.

### users

| Coluna | Tipo | Restrições |
|---|---|---|
| id | uuid | PK |
| name | varchar(120) | NN |
| email | varchar(255) | NN, único (armazenado em minúsculas) |
| password_hash | varchar(255) | NN |
| created_at | timestamptz | NN, default now() |

### fuel

Tabela de domínio, populada por seed na migration inicial com IDs fixos (constantes em `app/models/fuel.py`):

| Constante | id | name |
|---|---|---|
| `GASOLINE_ID` | `00000000-0000-4000-8000-000000000001` | Gasolina |
| `ETHANOL_ID` | `00000000-0000-4000-8000-000000000002` | Etanol |
| `FLEX_ID` | `00000000-0000-4000-8000-000000000003` | Flex |

| Coluna | Tipo | Restrições |
|---|---|---|
| id | uuid | PK |
| name | varchar(50) | NN, único |

### fuel_prices

Histórico de preços por usuário. Cada atualização insere uma nova linha; o preço vigente é o de maior `valid_from <= agora`. Só existe preço para Gasolina e Etanol (Flex não tem preço próprio).

| Coluna | Tipo | Restrições |
|---|---|---|
| id | uuid | PK |
| user_id | uuid | NN, FK → users.id |
| fuel_id | uuid | NN, FK → fuel.id |
| price_per_liter | numeric(6,3) | NN, > 0 |
| valid_from | timestamptz | NN |

### vehicles

| Coluna | Tipo | Restrições |
|---|---|---|
| id | uuid | PK |
| user_id | uuid | NN, FK → users.id |
| fuel_id | uuid | NN, FK → fuel.id (Gasolina, Etanol ou Flex) |
| model | varchar(120) | NN |
| declared_kml | numeric(5,2) | NN, > 0 — consumo médio declarado (km/l) |
| displacement_cc | int | ➕ opcional — cilindrada |
| year | int | ➕ opcional — ano |
| created_at | timestamptz | NN, default now() |

### shifts (expedientes)

| Coluna | Tipo | Restrições |
|---|---|---|
| id | uuid | PK |
| user_id | uuid | NN, FK → users.id |
| vehicle_id | uuid | NN, FK → vehicles.id |
| fuel_id | uuid | ➕ NN, FK → fuel.id — combustível efetivamente usado (Gasolina ou Etanol; necessário para Flex) |
| started_at | timestamptz | NN |
| ended_at | timestamptz | preenchido ao encerrar |
| status | shift_status | NN |
| price_per_liter_used | numeric(6,3) | NN — snapshot do preço ao iniciar |
| kml_used | numeric(5,2) | NN — snapshot do `declared_kml` ao iniciar |
| distance_km | numeric(8,3) | calculado ao encerrar |
| idle_minutes | int | ➕ calculado ao encerrar — tempo parado (motor ligado) |
| fuel_cost | numeric(10,2) | calculado ao encerrar |
| earnings_total | numeric(10,2) | calculado ao encerrar |
| profit | numeric(10,2) | calculado ao encerrar |
| duration_minutes | int | calculado ao encerrar |
| profit_per_hour | numeric(10,2) | calculado ao encerrar |
| profit_per_km | numeric(10,2) | calculado ao encerrar |
| created_at | timestamptz | NN, default now() |

Enum `shift_status`: `in_progress`, `finished`.

### earnings (ganhos)

| Coluna | Tipo | Restrições |
|---|---|---|
| id | uuid | PK |
| shift_id | uuid | NN, FK → shifts.id (ON DELETE CASCADE) |
| amount | numeric(10,2) | NN, > 0 |
| platform | varchar(50) | opcional (ex.: iFood, Uber, 99) |
| earned_at | timestamptz | NN |

### track_points (pontos de GPS)

| Coluna | Tipo | Restrições |
|---|---|---|
| id | uuid | PK |
| shift_id | uuid | NN, FK → shifts.id (ON DELETE CASCADE) |
| recorded_at | timestamptz | NN |
| latitude | numeric(9,6) | NN, entre -90 e 90 |
| longitude | numeric(9,6) | NN, entre -180 e 180 |
| accuracy_m | numeric(7,2) | opcional |
| speed_ms | numeric(6,2) | opcional |

### Índices e constraints

- `users(email)` único; `fuel(name)` único.
- `fuel_prices(user_id, fuel_id, valid_from DESC)`.
- `shifts(user_id, started_at DESC)`.
- Índice único **parcial** `shifts(user_id) WHERE status = 'in_progress'` — garante no máximo um expediente em andamento por usuário.
- `earnings(shift_id, earned_at)`.
- `track_points(shift_id, recorded_at)` **único** — permite reenvio de lotes sem duplicar pontos.

---

## 3. Regras de negócio

### Acesso
- Todos os recursos pertencem a um usuário. Acesso a recurso de outro usuário retorna **404** (não revela existência).
- Rotas protegidas exigem `Authorization: Bearer <token>`; token ausente, inválido ou expirado → **401**.

### Usuário
- E-mail normalizado (trim + minúsculas) e único → duplicado **409**.
- Senha com no mínimo 8 caracteres; `password` e `password_confirm` devem ser iguais → **422**.
- Login com credenciais inválidas → **401** com mensagem genérica.

### Combustível
- Atualizar preços insere novas linhas em `fuel_prices` com `valid_from = agora` (o histórico é preservado; expedientes antigos não mudam porque guardam snapshot).
- Não é permitido cadastrar preço para "Flex" → **422**.

### Veículo
- `fuel_id` deve existir (Gasolina, Etanol ou Flex); `declared_kml > 0` com até 2 casas e < 1000; `year` entre 1950 e ano atual + 1; `displacement_cc` entre 1 e 3000.
- Alterar `declared_kml` não muda expedientes já iniciados (eles guardam snapshot em `kml_used`).
- Excluir veículo com expedientes associados → **409**.

### Expediente
- **Iniciar** (`POST /shifts`):
  - veículo deve pertencer ao usuário;
  - se o veículo é **Flex**, o corpo deve informar `fuel_id` (Gasolina ou Etanol) → senão **422**; se não é Flex, `fuel_id` é o do veículo (enviar outro → **422**);
  - deve existir preço vigente do combustível usado → senão **409** (`"Cadastre o preço do combustível antes de iniciar"`);
  - já existe expediente `in_progress` → **409**;
  - grava snapshot: `price_per_liter_used` (preço vigente) e `kml_used` (`declared_kml`).
- **Ganhos** e **pontos de GPS** só podem ser adicionados/alterados em expediente `in_progress` → senão **409**.
- **"Sobrescrever ganho atual"**: o app edita o último ganho lançado via `PATCH /shifts/{id}/earnings/{earning_id}`.
- **Encerrar**: grava `ended_at = agora`, calcula e persiste todas as métricas ([seção 4](#4-cálculos)) e muda o status para `finished`. Expediente encerrado é **imutável** (edições → **409**).
- Pontos de GPS com `recorded_at` fora do intervalo `[started_at, agora + 1 min]` são descartados e contados em `rejected` — **o lote não falha**, para que um único ponto ruim não trave o buffer offline do app. Ganhos fora desse intervalo → **422**.

---

## 4. Cálculos

Todos os cálculos ficam em funções **puras** (`app/services/calculations.py`), sem acesso a banco — são o principal alvo dos testes unitários. O mesmo código calcula o **resumo parcial** (expediente em andamento, usando `agora` como fim) e as **métricas finais** (ao encerrar).

### 4.1 Referência

O cálculo de combustível a partir de GPS segue a abordagem de:

> Kan, Z.; Tang, L.; Kwan, M.-P.; Zhang, X. **Estimating Vehicle Fuel Consumption and Emissions Using GPS Big Data.** *Int. J. Environ. Res. Public Health* 2018, 15, 566. doi:[10.3390/ijerph15040566](https://doi.org/10.3390/ijerph15040566)

O artigo divide a trajetória em **segmentos entre pontos consecutivos** (space-time path segments, STPS) e classifica cada segmento como **atividade móvel (MA)** ou **atividade estacionária (SA)**, estimando o consumo de cada tipo separadamente. Isso evita subestimar o custo quando o veículo fica parado com o motor ligado (semáforos, espera em restaurante, trânsito).

### 4.2 Pré-processamento dos pontos

1. Ordenar por `recorded_at`.
2. Descartar pontos com `accuracy_m > GPS_MAX_ACCURACY_M` (padrão **50 m**).
3. Descartar pontos que gerem salto com velocidade implícita > `GPS_MAX_SPEED_KMH` (padrão **150 km/h**) em relação ao último ponto válido.

### 4.3 Segmentos e classificação (eq. 1–6 do artigo)

Para cada par de pontos válidos consecutivos `s_i = <c_i, c_{i+1}>`:

- `dist_i` = distância Haversine entre os pontos (raio da Terra 6 371 km);
- `Δt_i` = `recorded_at_{i+1} − recorded_at_i` (segundos).

Classificação, com limiar `δ = GPS_STATIONARY_THRESHOLD_M` (padrão **15 m**, ≈ erro posicional do GPS, como no artigo):

| Condição | Tipo |
|---|---|
| `dist_i ≥ δ` | **MA** — atividade móvel |
| `dist_i < δ` | **SA** — atividade estacionária |

**Decisão do projeto: parado = sempre motor ligado.** O artigo distingue SA com motor ligado e desligado (inferindo desligado quando não há pontos durante a parada). Aqui **toda SA conta como marcha lenta com motor ligado**, inclusive lacunas sem pontos em que a moto não se deslocou.

### 4.4 Distância e tempo parado

```
distance_km  = Σ dist_i   (segmentos MA)
idle_seconds = Σ Δt_i     (segmentos SA)
idle_minutes = round(idle_seconds / 60)
```

- O intervalo entre `started_at` e o primeiro ponto **não** entra em `idle_seconds` (não há posição conhecida); ele aparece apenas como lacuna de GPS (§4.7).
- Pontos com o mesmo `recorded_at` do último ponto válido são descartados.

### 4.5 Combustível

**Em movimento** — o artigo usa a equação COPERT para carros de passeio (eq. 8). Como aqui o veículo é uma moto e o usuário informa o consumo médio, usamos o consumo declarado:

```
liters_moving = distance_km / kml_used
```

**Parado (motor ligado)** — eq. 9 do artigo, `FC_SA = r · T`, consumo proporcional ao tempo parado:

```
liters_idle = idle_seconds × IDLE_FUEL_ML_PER_S / 1000
```

O artigo usa `r = 0,361 mL/s` (≈ 1,3 L/h), medido para um carro 3.0 L — valor que superestima muito o consumo de uma moto. Por isso `r` é um **parâmetro configurável** (`IDLE_FUEL_ML_PER_S`), com padrão **0,04 mL/s (≈ 0,15 L/h)**, ordem de grandeza típica da marcha lenta de motos de 125–160 cc.

**Custo total:**

```
fuel_cost = (liters_moving + liters_idle) × price_per_liter_used
```

### 4.6 Ganhos, lucro e indicadores

```
earnings_total   = Σ earnings.amount
profit           = earnings_total − fuel_cost
duration_minutes = (ended_at ou agora) − started_at, em minutos inteiros (truncado)
profit_per_hour  = profit / (duration_minutes / 60)    → null se duration_minutes = 0
profit_per_km    = profit / distance_km                 → null se distance_km = 0
```

- Valores monetários arredondados para 2 casas com `ROUND_HALF_UP` **apenas no final** (cálculos intermediários em `Decimal` com precisão total).
- Conferência com o protótipo: lucro R$ 187,40 em 4 h → **R$ 46,85/h**; em 78,2 km → **R$ 2,39/km**.

### 4.7 Status do GPS

Para os avisos "GPS ativo – último ponto há 4s" e "GPS ficou inativo por 6 min":

- `last_point_at` — `recorded_at` do último ponto recebido;
- `gps_gaps` — lista de intervalos `{start, end, minutes}` entre pontos consecutivos (ou entre `started_at` e o primeiro ponto) maiores que `GPS_GAP_THRESHOLD_S` (padrão **120 s**).

### 4.8 Agregação por dia e período

- O dia de um expediente é a **data local** de `started_at` no fuso informado (`tz`, padrão `America/Sao_Paulo`).
- Agregações somam `earnings_total`, `fuel_cost`, `profit`, `distance_km`, `duration_minutes` e `idle_minutes` dos expedientes `finished`; `profit_per_hour` e `profit_per_km` do período são recalculados a partir dos totais (não média das médias).

### 4.9 Parâmetros (settings / variáveis de ambiente)

| Variável | Padrão | Uso |
|---|---|---|
| `GPS_MAX_ACCURACY_M` | 50 | descarte de pontos imprecisos |
| `GPS_MAX_SPEED_KMH` | 150 | descarte de saltos |
| `GPS_STATIONARY_THRESHOLD_M` | 15 | limiar δ MA/SA |
| `GPS_GAP_THRESHOLD_S` | 120 | detecção de GPS inativo |
| `IDLE_FUEL_ML_PER_S` | 0.04 | consumo em marcha lenta |
| `DEFAULT_TZ` | America/Sao_Paulo | agregação por dia |
| `JWT_SECRET`, `JWT_EXPIRES_MINUTES` | — / 1440 | autenticação |
| `JWT_LEEWAY_SECONDS` | 30 | tolerância a diferença de relógio ao validar `iat`/`exp` |
| `DATABASE_URL` | — | conexão PostgreSQL |

---

## 5. Endpoints

- Prefixo: `/api/v1`. Corpo e respostas em JSON.
- Autenticação: `Authorization: Bearer <token>` em todas as rotas, exceto `register`, `login` e `health`.
- Valores monetários serializados como **string decimal** (`"187.40"`) para não perder precisão; datas em ISO 8601 UTC.

### Formato de erro

```json
{ "detail": "Já existe um expediente em andamento" }
```

| Código | Quando |
|---|---|
| 400 | Requisição malformada |
| 401 | Token ausente/inválido/expirado; credenciais inválidas |
| 404 | Recurso inexistente ou de outro usuário |
| 409 | Conflito de estado (e-mail duplicado, expediente já em andamento, expediente encerrado, preço inexistente, veículo com expedientes) |
| 422 | Erro de validação |

### 5.1 Saúde

| Método | Rota | Descrição |
|---|---|---|
| GET | `/health` | Executa `SELECT 1` no banco: **200** `{ "status": "ok", "database": "ok" }` ou **503** `{ "status": "error", "database": "unavailable" }` |

### 5.2 Autenticação e usuário

| Método | Rota | Descrição |
|---|---|---|
| POST | `/auth/register` | Cria usuário → **201** |
| POST | `/auth/login` | Autentica → **200** com token |
| GET | `/users/me` | Dados do usuário logado |
| PATCH | `/users/me` | Atualiza nome |

`POST /auth/register`
```json
{ "name": "John Doe", "email": "john@gmail.com", "password": "********", "password_confirm": "********" }
```
→ `201 { "id": "…", "name": "John Doe", "email": "john@gmail.com", "created_at": "…" }`

`POST /auth/login`
```json
{ "email": "john@gmail.com", "password": "********" }
```
→ `200 { "access_token": "…", "token_type": "bearer" }`

Token JWT HS256 com `sub` (id do usuário), `iat` e `exp` (padrão 24 h, `JWT_EXPIRES_MINUTES`).

`PATCH /users/me`
```json
{ "name": "John Atualizado" }
```
→ `200` com o mesmo formato de `UserResponse`.

Erros:

| Situação | Código | `detail` |
|---|---|---|
| E-mail já cadastrado (comparação sem diferenciar maiúsculas) | 409 | `E-mail já cadastrado` |
| Senhas diferentes, senha < 8 caracteres, e-mail inválido, nome vazio | 422 | erros de validação |
| E-mail inexistente ou senha errada (mesma mensagem nos dois casos) | 401 | `E-mail ou senha inválidos` |
| Token ausente, inválido, expirado ou de usuário inexistente | 401 | `Não autenticado` |

Respostas 401 incluem o header `WWW-Authenticate: Bearer`.

### 5.3 Combustíveis e preços

| Método | Rota | Descrição |
|---|---|---|
| GET | `/fuels` | Lista combustíveis (Gasolina, Etanol, Flex) |
| GET | `/fuel-prices/current` | Preço vigente de cada combustível do usuário |
| PUT | `/fuel-prices` | Atualiza um ou mais preços (insere nova vigência) |

`PUT /fuel-prices`
```json
{ "prices": [ { "fuel_id": "…", "price_per_liter": "6.20" }, { "fuel_id": "…", "price_per_liter": "3.75" } ] }
```
→ `200 [ { "fuel_id": "…", "fuel_name": "Gasolina", "price_per_liter": "6.200", "valid_from": "…" }, … ]`

- Todos os itens do mesmo `PUT` recebem o mesmo `valid_from` (agora). Preços anteriores ficam no histórico.
- A resposta traz **todos** os preços vigentes do usuário, não só os enviados (ex.: atualizar só a Gasolina devolve também o Etanol vigente).
- `price_per_liter`: maior que 0, até 3 casas decimais e menor que 1000.

`GET /fuel-prices/current` → mesmo formato da resposta do `PUT`. Usuário sem preços cadastrados → `[]`; combustível sem preço não aparece na lista.

`GET /fuels` → `[ { "id": "…", "name": "Gasolina" }, { "id": "…", "name": "Etanol" }, { "id": "…", "name": "Flex" } ]`

Erros:

| Situação | Código | `detail` |
|---|---|---|
| Preço para Flex | 422 | `Flex não tem preço próprio; informe Gasolina ou Etanol` |
| `fuel_id` inexistente | 422 | `Combustível não encontrado` |
| Lista vazia, `fuel_id` repetido, preço ≤ 0 ou fora do formato | 422 | erros de validação |
| Sem token | 401 | `Não autenticado` |

### 5.4 Veículos

| Método | Rota | Descrição |
|---|---|---|
| POST | `/vehicles` | Cadastra moto → **201** |
| GET | `/vehicles` | Lista motos do usuário |
| GET | `/vehicles/{id}` | Detalhe |
| PATCH | `/vehicles/{id}` | Atualiza ("Atualizar" no Perfil) |
| DELETE | `/vehicles/{id}` | Remove → **204** (ou **409** se houver expedientes) |

`POST /vehicles`
```json
{ "model": "Honda CG 160", "fuel_id": "…", "declared_kml": "32", "displacement_cc": 160, "year": 2022 }
```
(`displacement_cc` e `year` opcionais)

→ `201`
```json
{
  "id": "…",
  "model": "Honda CG 160",
  "fuel_id": "…",
  "fuel_name": "Gasolina",
  "declared_kml": "32.00",
  "displacement_cc": 160,
  "year": 2022,
  "created_at": "…"
}
```

`GET /vehicles` → lista nesse formato, em ordem de cadastro.

`PATCH /vehicles/{id}` — atualização parcial: só os campos enviados mudam. `null` em `displacement_cc` ou `year` limpa o campo; `null` em `model`, `fuel_id` ou `declared_kml` → **422**.
```json
{ "declared_kml": "30.5", "year": null }
```

Erros:

| Situação | Código | `detail` |
|---|---|---|
| Veículo inexistente ou de outro usuário | 404 | `Veículo não encontrado` |
| `fuel_id` inexistente | 422 | `Combustível não encontrado` |
| Campos fora das regras (§3) | 422 | erros de validação |
| Excluir veículo com expedientes | 409 | `Veículo possui expedientes registrados` |
| Sem token | 401 | `Não autenticado` |

### 5.5 Expedientes

| Método | Rota | Descrição |
|---|---|---|
| POST | `/shifts` | Inicia expediente → **201** |
| GET | `/shifts/current` | Expediente em andamento com resumo parcial (**404** se não houver) |
| GET | `/shifts/{id}` | Detalhe (parcial se em andamento, final se encerrado) |
| POST | `/shifts/{id}/finish` | Encerra e devolve o resumo final |
| GET | `/shifts?from=&to=&page=&size=` | Lista paginada, mais recentes primeiro |

`POST /shifts`
```json
{ "vehicle_id": "…", "fuel_id": "…" }
```
(`fuel_id` obrigatório só para moto Flex)

Resposta de `GET /shifts/current` (e de `finish`):
```json
{
  "id": "…",
  "status": "in_progress",
  "vehicle_id": "…",
  "fuel_id": "…",
  "started_at": "2026-09-28T11:00:00Z",
  "ended_at": null,
  "price_per_liter_used": "6.200",
  "kml_used": "32.00",
  "summary": {
    "earnings_total": "245.00",
    "fuel_cost": "57.60",
    "profit": "187.40",
    "distance_km": "78.200",
    "duration_minutes": 240,
    "idle_minutes": 35,
    "profit_per_hour": "46.85",
    "profit_per_km": "2.40"
  },
  "gps": {
    "last_point_at": "2026-09-28T14:59:56Z",
    "gaps": [ { "start": "…", "end": "…", "minutes": 6 } ]
  }
}
```

- Em andamento, `summary` é calculado até o momento da requisição. Encerrado, `summary` traz as métricas gravadas no `finish` (não mudam depois).
- `gps` é calculado a partir de todos os pontos recebidos, inclusive os descartados pelos filtros.
- `profit_per_km` usa `ROUND_HALF_UP`: 187,40 / 78,2 = 2,396 → **2,40** (o protótipo mostra 2,39 porque trunca).

`GET /shifts` — parâmetros:

| Parâmetro | Padrão | Regra |
|---|---|---|
| `from`, `to` | — | datas locais `YYYY-MM-DD`, inclusivas, filtram por `started_at`; `from <= to` |
| `tz` | `America/Sao_Paulo` | fuso IANA válido |
| `page` | 1 | ≥ 1 |
| `size` | 20 | 1–100 |

```json
{
  "items": [ { "id": "…", "status": "finished", "vehicle_id": "…", "fuel_id": "…", "started_at": "…", "ended_at": "…", "price_per_liter_used": "6.200", "kml_used": "32.00", "summary": { "…": "…" } } ],
  "total": 42,
  "page": 1,
  "size": 20
}
```
Itens não trazem `gps`; `summary` é `null` para expediente em andamento.

Erros:

| Situação | Código | `detail` |
|---|---|---|
| Veículo inexistente ou de outro usuário | 404 | `Veículo não encontrado` |
| Moto Flex sem `fuel_id`, ou com `fuel_id` diferente de Gasolina/Etanol | 422 | `Informe o combustível abastecido (Gasolina ou Etanol) para moto Flex` |
| Moto não-Flex com `fuel_id` diferente do cadastrado | 422 | `Combustível diferente do cadastrado no veículo` |
| Já existe expediente em andamento | 409 | `Já existe um expediente em andamento` |
| Sem preço vigente do combustível | 409 | `Cadastre o preço do combustível antes de iniciar` |
| `GET /shifts/current` sem expediente em andamento | 404 | `Nenhum expediente em andamento` |
| Expediente inexistente ou de outro usuário | 404 | `Expediente não encontrado` |
| Encerrar expediente já encerrado | 409 | `Expediente já encerrado` |
| Parâmetros de listagem inválidos | 422 | erros de validação |
| Sem token | 401 | `Não autenticado` |

### 5.6 Ganhos

| Método | Rota | Descrição |
|---|---|---|
| POST | `/shifts/{id}/earnings` | Lança ganho → **201** |
| GET | `/shifts/{id}/earnings` | Lista ganhos do expediente |
| PATCH | `/shifts/{id}/earnings/{earning_id}` | Edita ganho ("Sobrescrever ganho atual") |
| DELETE | `/shifts/{id}/earnings/{earning_id}` | Remove ganho → **204** |

`POST /shifts/{id}/earnings`
```json
{ "amount": "20.00", "platform": "iFood", "earned_at": "2026-09-28T13:10:00Z" }
```
(`earned_at` opcional — padrão: agora)

→ `201 { "id": "…", "shift_id": "…", "amount": "20.00", "platform": "iFood", "earned_at": "…" }`

- `amount`: maior que 0, até 2 casas decimais, no máximo 100.000.
- `platform`: opcional, até 50 caracteres.
- `earned_at`: precisa ter fuso (ex.: `Z` ou `-03:00`) e estar entre o início do expediente e agora (+1 min de tolerância de relógio).
- `GET` lista em ordem de `earned_at`, inclusive de expedientes encerrados.

**"Sobrescrever ganho atual"**: o app guarda o `id` do último ganho lançado e envia `PATCH /shifts/{id}/earnings/{earning_id}` com o novo valor. A edição é parcial: `null` em `platform` limpa o campo; `null` em `amount` ou `earned_at` → **422**.
```json
{ "amount": "12.00" }
```

Expediente encerrado é somente leitura: lançar, editar ou remover ganhos → **409**, e as métricas gravadas no `finish` não mudam.

Erros:

| Situação | Código | `detail` |
|---|---|---|
| Expediente inexistente ou de outro usuário | 404 | `Expediente não encontrado` |
| Ganho inexistente ou de outro expediente | 404 | `Ganho não encontrado` |
| Expediente encerrado (POST/PATCH/DELETE) | 409 | `Expediente já encerrado` |
| `earned_at` fora do expediente | 422 | `Horário do ganho fora do expediente` |
| Valor inválido, `earned_at` sem fuso | 422 | erros de validação |
| Sem token | 401 | `Não autenticado` |

### 5.7 Pontos de GPS

| Método | Rota | Descrição |
|---|---|---|
| POST | `/shifts/{id}/track-points` | Envia lote de pontos → **202** com `{ "accepted": n, "duplicated": m, "rejected": k }` |
| GET | `/shifts/{id}/track-points` | Lista pontos (para desenhar trajeto) |

`POST /shifts/{id}/track-points`
```json
{
  "points": [
    { "recorded_at": "2026-09-28T13:00:00Z", "latitude": -23.550520, "longitude": -46.633308, "accuracy_m": 8.5, "speed_ms": 11.2 }
  ]
}
```
- Lote de 1 a 500 pontos. Pontos repetidos (mesmo `recorded_at`, já salvos ou repetidos no próprio lote) são ignorados e contados em `duplicated`, permitindo que o app reenvie lotes após ficar offline.
- Pontos fora do intervalo do expediente são contados em `rejected` (ver §3).
- `recorded_at` precisa ter fuso. `latitude`/`longitude` são arredondadas para 6 casas (≈ 11 cm); `accuracy_m` e `speed_ms` (opcionais, ≥ 0) para 2 casas.
- A deduplicação é feita no banco (`INSERT … ON CONFLICT DO NOTHING` sobre `UNIQUE (shift_id, recorded_at)`), então é segura mesmo com envios simultâneos.

→ `202`
```json
{ "accepted": 5, "duplicated": 0, "rejected": 1 }
```

`GET /shifts/{id}/track-points` → pontos em ordem de `recorded_at`, inclusive de expedientes encerrados:
```json
[ { "recorded_at": "…", "latitude": "-23.550520", "longitude": "-46.633308", "accuracy_m": "8.40", "speed_ms": "9.12" } ]
```

Erros:

| Situação | Código | `detail` |
|---|---|---|
| Expediente inexistente ou de outro usuário | 404 | `Expediente não encontrado` |
| Expediente encerrado (POST) | 409 | `Expediente já encerrado` |
| Lote vazio ou > 500, coordenadas fora do intervalo, `recorded_at` sem fuso | 422 | erros de validação |
| Sem token | 401 | `Não autenticado` |

### 5.8 Histórico e análise

| Método | Rota | Descrição |
|---|---|---|
| GET | `/analytics/daily?from=&to=&tz=` | Totais por dia (tela Histórico: "Lucro do dia") |
| GET | `/analytics/summary?from=&to=&tz=` | Totais e indicadores do período |

Parâmetros (iguais nas duas rotas):

| Parâmetro | Padrão | Regra |
|---|---|---|
| `to` | hoje no fuso `tz` | data local `YYYY-MM-DD`, inclusiva |
| `from` | `to` − 29 dias (30 dias no total) | data local, inclusiva, `from <= to` |
| `tz` | `America/Sao_Paulo` | fuso IANA válido |

- Período máximo: 366 dias.
- Só entram expedientes **encerrados**; o dia é a data local de `started_at` (§4.8).
- A agregação é feita no banco (`GROUP BY date(timezone(tz, started_at))`) a partir das métricas gravadas no `finish`.

`GET /analytics/daily` — só dias com expediente, do **mais recente para o mais antigo** (ordem da tela Histórico). O app formata "Ontem" / "18/09/2026" a partir de `date`.
```json
[
  {
    "date": "2026-09-27",
    "shifts_count": 1,
    "earnings_total": "245.00",
    "fuel_cost": "57.60",
    "profit": "187.40",
    "distance_km": "78.200",
    "duration_minutes": 240,
    "idle_minutes": 35
  }
]
```

`GET /analytics/summary`
```json
{
  "from": "2026-09-01",
  "to": "2026-09-30",
  "days_worked": 2,
  "shifts_count": 2,
  "earnings_total": "490.00",
  "fuel_cost": "115.20",
  "profit": "374.80",
  "distance_km": "156.400",
  "duration_minutes": 480,
  "idle_minutes": 60,
  "profit_per_hour": "46.85",
  "profit_per_km": "2.40",
  "avg_profit_per_day": "187.40"
}
```

- `from`/`to` na resposta trazem o período efetivamente usado (útil quando foram omitidos).
- `days_worked` conta dias locais distintos; dois expedientes no mesmo dia contam 1.
- `profit_per_hour = profit / (duration_minutes / 60)`, `profit_per_km = profit / distance_km` e `avg_profit_per_day = profit / days_worked` são calculados a partir dos **totais** (não média das médias), com `ROUND_HALF_UP`; `null` quando o divisor é 0.
- Período sem expedientes → `daily = []` e `summary` com totais zerados e taxas `null`.

Erros:

| Situação | Código | `detail` |
|---|---|---|
| `from > to`, período > 366 dias, `tz` inválido | 422 | erros de validação |
| Sem token | 401 | `Não autenticado` |

---

## 6. Estratégia de testes

Ferramentas: **pytest**, **pytest-cov**, **testcontainers** (PostgreSQL real), `fastapi.testclient.TestClient`. Tudo executado com `uv run pytest`. Meta: **cobertura ≥ 90%** (`--cov-fail-under=90`).

### 6.1 Unitários (`tests/unit`)

Rápidos, sem banco e sem rede.

- **Cálculos** (`calculations.py`):
  - Haversine com distâncias conhecidas;
  - filtros de GPS: precisão ruim, salto acima de 150 km/h, ordenação;
  - classificação MA/SA exatamente no limiar δ (14,9 m / 15 m);
  - custo em marcha lenta; lacuna sem pontos **parada** (conta como SA) vs. **em movimento** (conta distância);
  - custo de combustível, lucro, lucro negativo;
  - divisões por zero (`duration = 0`, `distance = 0` → null);
  - arredondamento `ROUND_HALF_UP`;
  - detecção de lacunas de GPS;
  - agrupamento por dia com fuso (expediente iniciado 23h30 local cai no dia local, não no UTC).
- **Segurança**: hash/verify de senha; JWT válido, expirado, assinatura inválida.
- **Schemas Pydantic**: senhas diferentes, e-mail inválido, valores ≤ 0, lat/long fora do intervalo.
- **Services** com repositórios fake: regras de iniciar expediente (Flex, sem preço, já em andamento), expediente encerrado imutável.

### 6.2 Integração (`tests/integration`)

- Um container PostgreSQL por sessão de testes (testcontainers), migrations Alembic aplicadas no início.
- Isolamento por teste (transação com rollback ou `TRUNCATE`).
- Fixtures/factories em `conftest.py`: usuário autenticado, cliente com token, veículo, preços, expediente.
- Para **cada endpoint**: caminho feliz, sem token / token inválido (401), recurso de outro usuário (404), validação (422), conflitos (409).
- **Fluxo completo**: cadastro → login → preços → moto → iniciar → pontos → ganhos → sobrescrever ganho → resumo parcial → encerrar → histórico diário → resumo do período.
- Constraints do banco: índice parcial de 1 expediente em andamento, unicidade de `track_points(shift_id, recorded_at)`.

---

## 7. Roadmap de execução

Cada etapa é planejada e executada separadamente, com testes, e **commitada pelo usuário** ao final.

| # | Etapa | Entregáveis |
|---|---|---|
| 1 | Scaffold | `uv init`, `pyproject.toml`, `.python-version`, ruff, `docker-compose.yml`, settings, `GET /health` + teste |
| 2 | Banco | Modelos SQLAlchemy, Alembic, seed de `fuel`, infra de testes de integração (testcontainers) |
| 3 | Auth e usuário | register, login, JWT, `/users/me` |
| 4 | Combustíveis e preços | `/fuels`, `/fuel-prices` |
| 5 | Veículos | CRUD de `/vehicles` |
| 6 | Expedientes | módulo de cálculos, iniciar / atual / detalhe / encerrar / listar |
| 7 | Ganhos | CRUD de ganhos do expediente |
| 8 | Pontos de GPS | envio em lote, idempotência, status do GPS |
| 9 | Histórico e análise | `/analytics/daily`, `/analytics/summary` |
| 10 | Fechamento | revisão de cobertura, documentação OpenAPI, CI (GitHub Actions) |

---

## 8. Pontos em aberto

- **Nome do app** (hoje "Nome do app" nos protótipos).
- **Refresh token** — fora do MVP; token de acesso com expiração de 24 h.
- **Valor de `IDLE_FUEL_ML_PER_S`** — padrão 0,04 mL/s; pode ser calibrado com dados reais ou variar por cilindrada.
- **Tolerâncias do GPS** (precisão, velocidade máxima, δ, lacuna) — configuráveis; ajustar após testes de campo.
- **Múltiplas motos** — a API suporta várias, mas a tela de Perfil mostra uma ("Minha moto").
