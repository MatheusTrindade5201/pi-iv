import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.auth import Name


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: str
    created_at: datetime


class UserUpdate(BaseModel):
    name: Name
