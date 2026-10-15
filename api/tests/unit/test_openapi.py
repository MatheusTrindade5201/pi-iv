import pytest

from app.core.config import Settings
from app.main import create_app

pytestmark = pytest.mark.unit

PUBLIC_OPERATIONS = {
    ("post", "/api/v1/auth/register"),
    ("post", "/api/v1/auth/login"),
    ("get", "/api/v1/health"),
}
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


@pytest.fixture(scope="module")
def spec() -> dict:
    return create_app(Settings(_env_file=None, environment="test")).openapi()


def operations(spec: dict) -> list[tuple[str, str, dict]]:
    return [
        (method, path, operation)
        for path, item in spec["paths"].items()
        for method, operation in item.items()
        if method in HTTP_METHODS
    ]


def test_api_metadata(spec: dict) -> None:
    assert spec["info"]["version"] == "1.0.0"
    assert "Authorization: Bearer" in spec["info"]["description"]


def test_every_operation_has_summary_and_described_tag(spec: dict) -> None:
    described_tags = {tag["name"] for tag in spec["tags"] if tag.get("description")}

    for method, path, operation in operations(spec):
        assert operation.get("summary"), f"{method.upper()} {path} sem summary"
        assert set(operation["tags"]) <= described_tags, f"{method.upper()} {path} sem tag"


def test_protected_operations_require_bearer_and_document_401(spec: dict) -> None:
    protected = [op for op in operations(spec) if (op[0], op[1]) not in PUBLIC_OPERATIONS]

    assert len(protected) == len(operations(spec)) - len(PUBLIC_OPERATIONS)
    for method, path, operation in protected:
        assert operation.get("security") == [{"HTTPBearer": []}], f"{method.upper()} {path}"
        error_schema = operation["responses"]["401"]["content"]["application/json"]["schema"]
        assert error_schema == {"$ref": "#/components/schemas/ErrorResponse"}


def test_public_operations_do_not_require_token(spec: dict) -> None:
    for method, path in PUBLIC_OPERATIONS:
        assert "security" not in spec["paths"][path][method]
