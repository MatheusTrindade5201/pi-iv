from typing import Annotated, Literal, Self

from pydantic import AfterValidator, BaseModel, EmailStr, Field, StringConstraints, model_validator

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
NormalizedEmail = Annotated[EmailStr, AfterValidator(lambda email: email.lower())]
Password = Annotated[str, Field(min_length=8, max_length=128)]


class RegisterRequest(BaseModel):
    name: Name
    email: NormalizedEmail
    password: Password
    password_confirm: str

    @model_validator(mode="after")
    def passwords_match(self) -> Self:
        if self.password != self.password_confirm:
            raise ValueError("As senhas não conferem")
        return self


class LoginRequest(BaseModel):
    email: NormalizedEmail
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
