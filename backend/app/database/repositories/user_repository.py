
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.database.models.user import UserModel


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: str):
        statement = select(UserModel).where(
            UserModel.id == user_id
        )
        return self.db.scalar(statement)

    def get_by_username(self, username: str):
        statement = select(UserModel).where(
            func.lower(UserModel.username) == username.strip().lower()
        )
        return self.db.scalar(statement)

    def get_by_email(self, email: str):
        statement = select(UserModel).where(
            func.lower(UserModel.email) == email.strip().lower()
        )
        return self.db.scalar(statement)

    def get_by_identifier(self, identifier: str):
        identifier = identifier.strip().lower()

        statement = select(UserModel).where(
            (func.lower(UserModel.username) == identifier)
            | (func.lower(UserModel.email) == identifier)
        )
        return self.db.scalar(statement)

    def create(
        self,
        user_id: str,
        username: str,
        email: str,
        password_hash: str,
        created_at: datetime | str | None = None,
        updated_at: datetime | str | None = None,
    ):
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(
                created_at.replace("Z", "+00:00")
            )

        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(
                updated_at.replace("Z", "+00:00")
            )

        user = UserModel(
            id=user_id,
            username=username.strip(),
            email=email.strip().lower(),
            password_hash=password_hash,
            created_at=created_at or datetime.now().astimezone(),
            updated_at=updated_at or datetime.now().astimezone(),
        )

        try:
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            return user
        except Exception:
            self.db.rollback()
            raise
