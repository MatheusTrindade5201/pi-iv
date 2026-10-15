from pydantic import BaseModel

DESCRIPTION = """
API do app de registro de expedientes para motociclistas.

O motociclista cadastra a moto e o preço dos combustíveis, inicia um expediente,
lança os ganhos e envia os pontos de GPS. A API calcula distância, tempo parado com
motor ligado, gasto de combustível e lucro (parcial e final), e agrega o histórico
por dia e por período.

**Autenticação:** `POST /auth/login` devolve um token JWT; envie-o em
`Authorization: Bearer <token>` (botão **Authorize**). Só `register`, `login` e
`health` são públicas.

**Valores:** dinheiro e medidas são strings decimais (`"187.40"`); datas em ISO 8601
com fuso.
""".strip()

TAGS = [
    {"name": "health", "description": "Disponibilidade da API e do banco."},
    {"name": "auth", "description": "Cadastro e login (JWT)."},
    {"name": "users", "description": "Perfil do usuário logado."},
    {"name": "fuels", "description": "Combustíveis disponíveis (Gasolina, Etanol, Flex)."},
    {"name": "fuel-prices", "description": "Preço por litro de cada combustível, com histórico."},
    {"name": "vehicles", "description": "Motos do usuário."},
    {
        "name": "shifts",
        "description": "Expedientes: iniciar, acompanhar o lucro parcial, encerrar e listar.",
    },
    {"name": "earnings", "description": "Ganhos lançados durante o expediente."},
    {
        "name": "track-points",
        "description": "Pontos de GPS enviados em lote, com deduplicação para reenvio offline.",
    },
    {"name": "analytics", "description": "Histórico por dia e análise de desempenho por período."},
]

ERROR_DESCRIPTIONS = {
    401: "Token ausente, inválido ou expirado",
    404: "Recurso inexistente ou de outro usuário",
    409: "Conflito com o estado atual",
    422: "Regra de negócio violada ou corpo inválido",
}


class ErrorResponse(BaseModel):
    detail: str


def errors(*codes: int) -> dict[int | str, dict]:
    return {
        code: {"model": ErrorResponse, "description": ERROR_DESCRIPTIONS[code]} for code in codes
    }
