from app.models import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserUpdate


class UserService:
    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

    def update(self, user: User, data: UserUpdate) -> User:
        user.name = data.name
        return self.repository.save(user)
